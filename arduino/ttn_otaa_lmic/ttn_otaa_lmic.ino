#include <Arduino.h>
#include <SPI.h>
#include <lmic.h>
#include <hal/hal.h>
#if defined(__has_include)
#  if __has_include("config.h")
#    include "config.h"
#  else
#    include "config.example.h"
#  endif
#else
#  include "config.h"
#endif
#include "tide_math.h"
#include "subband_fallback.h"

static uint8_t APPEUI[8];
static uint8_t DEVEUI[8];
static uint8_t APPKEY[16];

static osjob_t sendjob;
static const unsigned TX_INTERVAL_S = 60;
static const unsigned RETRY_INTERVAL_S = 5;
static const std::uint8_t JOIN_TXCOMPLETE_BEFORE_SUBBAND_ROTATE = 3;
static tidegauge::SubbandFallback g_subband_fallback(tg_config::US915_SUBBAND);

// HC-SR04 wiring (Adafruit Feather labels):
// TRIG -> D6, ECHO -> D5
static const int HCSR04_TRIG_PIN = D6;
static const int HCSR04_ECHO_PIN = D5;
static const unsigned long HCSR04_TIMEOUT_US = tg_config::ULTRASONIC_TIMEOUT_US;
static const std::size_t HCSR04_SAMPLE_COUNT = tg_config::ULTRASONIC_SAMPLE_COUNT;
static const unsigned long HCSR04_INTERSAMPLE_DELAY_MS = tg_config::ULTRASONIC_INTERSAMPLE_DELAY_MS;
static const int BATTERY_ADC_PIN = 29;
static const float BATTERY_DIVIDER_RATIO = 2.0f;

void os_getArtEui(u1_t *buf) { memcpy(buf, APPEUI, 8); }
void os_getDevEui(u1_t *buf) { memcpy(buf, DEVEUI, 8); }
void os_getDevKey(u1_t *buf) { memcpy(buf, APPKEY, 16); }

const lmic_pinmap lmic_pins = {
    .nss = PIN_RFM_CS,
    .rxtx = LMIC_UNUSED_PIN,
    .rst = PIN_RFM_RST,
    .dio = {PIN_RFM_DIO0, PIN_RFM_DIO1, PIN_RFM_DIO2},
};

static bool hex_to_bytes(const char *hex, uint8_t *out, size_t out_len) {
    size_t n = strlen(hex);
    if (n != out_len * 2) {
        return false;
    }

    for (size_t i = 0; i < out_len; ++i) {
        char hi = hex[i * 2];
        char lo = hex[i * 2 + 1];
        uint8_t hv = (hi >= '0' && hi <= '9') ? (uint8_t)(hi - '0') :
                     (hi >= 'A' && hi <= 'F') ? (uint8_t)(hi - 'A' + 10) :
                     (hi >= 'a' && hi <= 'f') ? (uint8_t)(hi - 'a' + 10) : 0xFF;
        uint8_t lv = (lo >= '0' && lo <= '9') ? (uint8_t)(lo - '0') :
                     (lo >= 'A' && lo <= 'F') ? (uint8_t)(lo - 'A' + 10) :
                     (lo >= 'a' && lo <= 'f') ? (uint8_t)(lo - 'a' + 10) : 0xFF;
        if (hv == 0xFF || lv == 0xFF) {
            return false;
        }
        out[i] = (uint8_t)((hv << 4) | lv);
    }

    return true;
}

// LMIC expects little-endian for EUI fields.
static void reverse_bytes(uint8_t *buf, size_t len) {
    for (size_t i = 0; i < len / 2; ++i) {
        uint8_t t = buf[i];
        buf[i] = buf[len - 1 - i];
        buf[len - 1 - i] = t;
    }
}

static float read_battery_voltage_v() {
    const int raw = analogRead(BATTERY_ADC_PIN);
    const float adc_v = (static_cast<float>(raw) * 3.3f) / 4095.0f;
    return adc_v * BATTERY_DIVIDER_RATIO;
}

static void restart_join_on_next_subband() {
    g_subband_fallback.rotate_to_next();
    const std::uint8_t subband = g_subband_fallback.current_subband();
    Serial.print("LMIC: switching to US915 subband ");
    Serial.println(subband);
    LMIC_reset();
    LMIC_selectSubBand(subband);
    LMIC_setClockError(MAX_CLOCK_ERROR * 1 / 100);
    LMIC_startJoining();
}

static unsigned current_send_interval_s() {
    if (tg_config::RAPID_DIAGNOSTIC_MODE) {
        return static_cast<unsigned>(tg_config::RAPID_DIAGNOSTIC_INTERVAL_S);
    }
    return TX_INTERVAL_S;
}

static void do_send(osjob_t *j) {
    (void)j;

    if (LMIC.opmode & OP_TXRXPEND) {
        Serial.println("LMIC: TX/RX pending");
        os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(RETRY_INTERVAL_S), do_send);
    } else {
        float measured_samples_m[HCSR04_SAMPLE_COUNT] = {0, 0, 0, 0, 0};
        std::size_t valid_sample_count = 0;
        for (std::size_t i = 0; i < HCSR04_SAMPLE_COUNT; ++i) {
            digitalWrite(HCSR04_TRIG_PIN, LOW);
            delayMicroseconds(2);
            digitalWrite(HCSR04_TRIG_PIN, HIGH);
            delayMicroseconds(10);
            digitalWrite(HCSR04_TRIG_PIN, LOW);

            const unsigned long pulse_us = pulseIn(HCSR04_ECHO_PIN, HIGH, HCSR04_TIMEOUT_US);
            if (pulse_us > 0UL) {
                float sample_m = 0.0f;
                if (tidegauge::distance_from_pulse_us(pulse_us, tg_config::SPEED_OF_SOUND_M_PER_US, &sample_m)) {
                    measured_samples_m[valid_sample_count++] = sample_m;
                }
            }
            if (tg_config::RAPID_DIAGNOSTIC_MODE) {
                Serial.print("DIAG: sample[");
                Serial.print(static_cast<unsigned>(i));
                Serial.print("] pulse_us=");
                Serial.print(pulse_us);
                if (pulse_us > 0UL) {
                    Serial.print(" distance_m=");
                    float sample_m = 0.0f;
                    if (tidegauge::distance_from_pulse_us(pulse_us, tg_config::SPEED_OF_SOUND_M_PER_US, &sample_m)) {
                        Serial.println(sample_m, 4);
                    } else {
                        Serial.println(" invalid");
                    }
                } else {
                    Serial.println(" timeout");
                }
            }
            if (i + 1 < HCSR04_SAMPLE_COUNT) {
                delay(HCSR04_INTERSAMPLE_DELAY_MS);
            }
        }

        if (valid_sample_count == 0) {
            Serial.println("SENSOR: timeout waiting for echo pulse");
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(current_send_interval_s()), do_send);
            return;
        }

        float measured_distance_m = 0.0f;
        if (!tidegauge::median_distance_m(measured_samples_m, valid_sample_count, &measured_distance_m)) {
            Serial.println("SENSOR: invalid median distance sample set");
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(current_send_interval_s()), do_send);
            return;
        }
        float corrected_distance_m = 0.0f;
        if (!tidegauge::apply_distance_calibration_m(
                measured_distance_m,
                tg_config::DISTANCE_SCALE,
                tg_config::DISTANCE_OFFSET_M,
                &corrected_distance_m)) {
            Serial.println("SENSOR: invalid distance calibration");
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(current_send_interval_s()), do_send);
            return;
        }
        const float battery_voltage_v = read_battery_voltage_v();
        float tide_height_m = 0.0f;
        if (!tidegauge::compute_tide_height_m(
                tg_config::GEOMETRY_REFERENCE_M, corrected_distance_m, tg_config::DATUM_OFFSET_M, &tide_height_m)) {
            Serial.println("SENSOR: invalid tide height input");
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(current_send_interval_s()), do_send);
            return;
        }

        uint8_t payload[6] = {0, 0, 0, 0, 0, 0};
        if (!tidegauge::encode_tide_distance_battery_payload(
                tide_height_m, corrected_distance_m, battery_voltage_v, payload)) {
            Serial.println("PAYLOAD: tide/distance/battery out of encodable range");
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(current_send_interval_s()), do_send);
            return;
        }

        if (tg_config::RAPID_DIAGNOSTIC_MODE) {
            Serial.print("DIAG: median_distance_m=");
            Serial.print(measured_distance_m, 4);
            Serial.print(" corrected_distance_m=");
            Serial.print(corrected_distance_m, 4);
            Serial.print(" tide_height_m=");
            Serial.print(tide_height_m, 4);
            Serial.print(" battery_v=");
            Serial.println(battery_voltage_v, 4);
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(current_send_interval_s()), do_send);
            return;
        }

        LMIC_setTxData2(1, payload, sizeof(payload), 0);
        Serial.print("LMIC: queued uplink raw_distance_m=");
        Serial.print(measured_distance_m, 3);
        Serial.print(" corrected_distance_m=");
        Serial.print(corrected_distance_m, 3);
        Serial.print(" tide_height_m=");
        Serial.print(tide_height_m, 3);
        Serial.print(" battery_v=");
        Serial.print(battery_voltage_v, 3);
        Serial.print(" payload=");
        Serial.print(payload[0], HEX);
        Serial.print(" ");
        Serial.print(payload[1], HEX);
        Serial.print(" ");
        Serial.print(payload[2], HEX);
        Serial.print(" ");
        Serial.print(payload[3], HEX);
        Serial.print(" ");
        Serial.print(payload[4], HEX);
        Serial.print(" ");
        Serial.println(payload[5], HEX);
    }
}

void onEvent(ev_t ev) {
    Serial.print(os_getTime());
    Serial.print(": ");

    switch (ev) {
        case EV_JOINING:
            Serial.println("EV_JOINING");
            break;
        case EV_JOINED:
            Serial.println("EV_JOINED");
            g_subband_fallback.note_joined();
            LMIC_setLinkCheckMode(0);
            do_send(&sendjob);
            break;
        case EV_JOIN_FAILED:
            Serial.println("EV_JOIN_FAILED");
            restart_join_on_next_subband();
            break;
        case EV_TXCOMPLETE:
            Serial.println("EV_TXCOMPLETE");
            if (LMIC.dataLen) {
                Serial.print("LMIC: downlink bytes=");
                Serial.println(LMIC.dataLen);
            }
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(current_send_interval_s()), do_send);
            break;
        case EV_JOIN_TXCOMPLETE:
            Serial.println("EV_JOIN_TXCOMPLETE");
            if (g_subband_fallback.note_join_txcomplete(JOIN_TXCOMPLETE_BEFORE_SUBBAND_ROTATE)) {
                restart_join_on_next_subband();
            }
            break;
        default:
            Serial.print("EV_");
            Serial.println((unsigned)ev);
            break;
    }
}

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000) {
    }

    Serial.println("LMIC OTAA test starting");
    Serial.print("CFG: rapid_diag=");
    Serial.println(tg_config::RAPID_DIAGNOSTIC_MODE ? 1 : 0);

    if (!hex_to_bytes(tg_config::APP_EUI_HEX, APPEUI, sizeof(APPEUI)) ||
        !hex_to_bytes(tg_config::DEV_EUI_HEX, DEVEUI, sizeof(DEVEUI)) ||
        !hex_to_bytes(tg_config::APP_KEY_HEX, APPKEY, sizeof(APPKEY))) {
        Serial.println("LMIC: invalid OTAA hex credentials");
        while (true) {
            delay(1000);
        }
    }

    reverse_bytes(APPEUI, sizeof(APPEUI));
    reverse_bytes(DEVEUI, sizeof(DEVEUI));

    pinMode(HCSR04_TRIG_PIN, OUTPUT);
    pinMode(HCSR04_ECHO_PIN, INPUT);
    digitalWrite(HCSR04_TRIG_PIN, LOW);
    analogReadResolution(12);

    os_init();
    LMIC_reset();

    const std::uint8_t initial_subband = g_subband_fallback.current_subband();
    Serial.print("LMIC: initial US915 subband ");
    Serial.println(initial_subband);
    LMIC_selectSubBand(initial_subband);
    LMIC_setClockError(MAX_CLOCK_ERROR * 1 / 100);

    LMIC_startJoining();
}

void loop() {
    os_runloop_once();
}
