#include <Arduino.h>
#include <SPI.h>
#include <pico/time.h>
#include <OneWire.h>
#include <DallasTemperature.h>
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
static const int HCSR04_POWER_ENABLE_PIN = tg_config::ULTRASONIC_POWER_ENABLE_PIN;
static const unsigned long HCSR04_INTERSAMPLE_DELAY_MS = tg_config::ULTRASONIC_INTERSAMPLE_DELAY_MS;
static constexpr float HCSR04_CLUSTER_GAP_THRESHOLD_M = 0.15f;
static constexpr std::size_t HCSR04_MIN_CLUSTER_COUNT = 3;
static const int BATTERY_ADC_PIN = 26;
static const float BATTERY_DIVIDER_RATIO = 1.545f;
static const int DS18B20_DATA_PIN = tg_config::DS18B20_DATA_PIN;

static OneWire g_one_wire(DS18B20_DATA_PIN);
static DallasTemperature g_temperature_sensors(&g_one_wire);

static void print_ds18b20_address(const DeviceAddress address) {
    for (std::uint8_t i = 0; i < 8; ++i) {
        if (address[i] < 0x10) {
            Serial.print("0");
        }
        Serial.print(address[i], HEX);
    }
}

static void log_ds18b20_bus_state() {
    Serial.print("DS18B20: device_count=");
    Serial.print(g_temperature_sensors.getDeviceCount());

    DeviceAddress address = {0, 0, 0, 0, 0, 0, 0, 0};
    if (g_temperature_sensors.getAddress(address, 0)) {
        Serial.print(" DS18B20: address=");
        print_ds18b20_address(address);
    } else {
        Serial.print(" DS18B20: address=none");
    }
    Serial.println();
}

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
    float battery_v = 0.0f;
    if (!tidegauge::battery_voltage_from_adc_raw(raw, 3.3f, 4095, BATTERY_DIVIDER_RATIO, &battery_v)) {
        return 0.0f;
    }
    return battery_v;
}

static void configure_low_power_lora_uplink() {
    LMIC_setAdrMode(tg_config::LORA_ADR_ENABLED ? 1 : 0);
    LMIC_setDrTxpow(LMIC.datarate, tg_config::LORA_UPLINK_TX_POWER_DBM);
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

static void power_on_ultrasonic_sensor() {
    if (HCSR04_POWER_ENABLE_PIN >= 0) {
        digitalWrite(HCSR04_POWER_ENABLE_PIN, HIGH);
        delay(tg_config::ULTRASONIC_POWER_SETTLE_MS);
    }
}

static void power_off_ultrasonic_sensor() {
    if (HCSR04_POWER_ENABLE_PIN >= 0) {
        digitalWrite(HCSR04_POWER_ENABLE_PIN, LOW);
    }
}

static void do_send(osjob_t *j) {
    (void)j;

    if (LMIC.opmode & OP_TXRXPEND) {
        Serial.println("LMIC: TX/RX pending");
        os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(RETRY_INTERVAL_S), do_send);
    } else {
        power_on_ultrasonic_sensor();
        float measured_samples_m[HCSR04_SAMPLE_COUNT] = {};
        std::size_t valid_sample_count = 0;
        std::size_t timeout_sample_count = 0;
        std::size_t echo_high_stuck_count = 0;
        unsigned long min_valid_pulse_us = 0UL;
        unsigned long max_valid_pulse_us = 0UL;
        for (std::size_t i = 0; i < HCSR04_SAMPLE_COUNT; ++i) {
            if (digitalRead(HCSR04_ECHO_PIN) == HIGH) {
                ++echo_high_stuck_count;
            }
            digitalWrite(HCSR04_TRIG_PIN, LOW);
            delayMicroseconds(2);
            digitalWrite(HCSR04_TRIG_PIN, HIGH);
            delayMicroseconds(20);
            digitalWrite(HCSR04_TRIG_PIN, LOW);

            const unsigned long pulse_us = pulseIn(HCSR04_ECHO_PIN, HIGH, HCSR04_TIMEOUT_US);
            if (pulse_us > 0UL) {
                if (min_valid_pulse_us == 0UL || pulse_us < min_valid_pulse_us) {
                    min_valid_pulse_us = pulse_us;
                }
                if (pulse_us > max_valid_pulse_us) {
                    max_valid_pulse_us = pulse_us;
                }
                float sample_m = 0.0f;
                if (tidegauge::distance_from_pulse_us(pulse_us, tg_config::SPEED_OF_SOUND_M_PER_US, &sample_m)) {
                    measured_samples_m[valid_sample_count++] = sample_m;
                }
            } else {
                ++timeout_sample_count;
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
        if (tg_config::RAPID_DIAGNOSTIC_MODE) {
            Serial.print("DIAG: samples_valid=");
            Serial.print(static_cast<unsigned>(valid_sample_count));
            Serial.print(" samples_timeout=");
            Serial.print(static_cast<unsigned>(timeout_sample_count));
            Serial.print(" pulse_min_us=");
            Serial.print(min_valid_pulse_us);
            Serial.print(" pulse_max_us=");
            Serial.print(max_valid_pulse_us);
            Serial.print(" echo_high_stuck=");
            Serial.println(echo_high_stuck_count > 0 ? 1 : 0);
        }

        float measured_distance_m = NAN;
        float measured_distance_stddev_m = NAN;
        float corrected_distance_m = NAN;
        float corrected_distance_stddev_m = NAN;
        float tide_height_m = NAN;

        if (valid_sample_count == 0) {
            Serial.println("SENSOR: timeout waiting for echo pulse");
        } else if (!tidegauge::furthest_cluster_distance_stats_m(
                       measured_samples_m,
                       valid_sample_count,
                       HCSR04_CLUSTER_GAP_THRESHOLD_M,
                       HCSR04_MIN_CLUSTER_COUNT,
                       &measured_distance_m,
                       &measured_distance_stddev_m)) {
            Serial.println("SENSOR: invalid furthest distance cluster sample set");
        } else if (!tidegauge::apply_distance_calibration_m(
                       measured_distance_m,
                       tg_config::DISTANCE_SCALE,
                       tg_config::DISTANCE_OFFSET_M,
                       &corrected_distance_m)) {
            Serial.println("SENSOR: invalid distance calibration");
        } else {
            corrected_distance_stddev_m = measured_distance_stddev_m * tg_config::DISTANCE_SCALE;
            if (!tidegauge::compute_tide_height_m(
                    tg_config::GEOMETRY_REFERENCE_M, corrected_distance_m, tg_config::DATUM_OFFSET_M, &tide_height_m)) {
                Serial.println("SENSOR: invalid tide height input");
                corrected_distance_m = NAN;
                corrected_distance_stddev_m = NAN;
                tide_height_m = NAN;
            }
        }
        const float battery_voltage_v = read_battery_voltage_v();
        log_ds18b20_bus_state();
        g_temperature_sensors.requestTemperatures();
        float temperature_c = g_temperature_sensors.getTempCByIndex(0);
        if (temperature_c == DEVICE_DISCONNECTED_C) {
            Serial.println("SENSOR: DS18B20 disconnected");
            temperature_c = NAN;
        }

        uint8_t payload[10] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
        if (!tidegauge::encode_tide_distance_battery_payload(
                tide_height_m,
                corrected_distance_m,
                battery_voltage_v,
                corrected_distance_stddev_m,
                temperature_c,
                payload)) {
            power_off_ultrasonic_sensor();
            Serial.println("PAYLOAD: tide/distance/battery/stddev/temperature out of encodable range");
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(current_send_interval_s()), do_send);
            return;
        }

        if (tg_config::RAPID_DIAGNOSTIC_MODE) {
            power_off_ultrasonic_sensor();
            Serial.print("DIAG: median_distance_m=");
            Serial.print(measured_distance_m, 4);
            Serial.print(" corrected_distance_m=");
            Serial.print(corrected_distance_m, 4);
            Serial.print(" corrected_stddev_m=");
            Serial.print(corrected_distance_stddev_m, 4);
            Serial.print(" temperature_c=");
            Serial.print(temperature_c, 2);
            Serial.print(" tide_height_m=");
            Serial.print(tide_height_m, 4);
            Serial.print(" battery_v=");
            Serial.println(battery_voltage_v, 4);
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(current_send_interval_s()), do_send);
            return;
        }

        power_off_ultrasonic_sensor();
        configure_low_power_lora_uplink();
        LMIC_setTxData2(1, payload, sizeof(payload), 0);
        Serial.print("LMIC: queued uplink raw_distance_m=");
        Serial.print(measured_distance_m, 3);
        Serial.print(" corrected_distance_m=");
        Serial.print(corrected_distance_m, 3);
        Serial.print(" corrected_stddev_m=");
        Serial.print(corrected_distance_stddev_m, 3);
        Serial.print(" temperature_c=");
        Serial.print(temperature_c, 2);
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
        Serial.print(payload[5], HEX);
        Serial.print(" ");
        Serial.print(payload[6], HEX);
        Serial.print(" ");
        Serial.print(payload[7], HEX);
        Serial.print(" ");
        Serial.print(payload[8], HEX);
        Serial.print(" ");
        Serial.println(payload[9], HEX);
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
            configure_low_power_lora_uplink();
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
    if (HCSR04_POWER_ENABLE_PIN >= 0) {
        pinMode(HCSR04_POWER_ENABLE_PIN, OUTPUT);
        power_off_ultrasonic_sensor();
    }
    digitalWrite(HCSR04_TRIG_PIN, LOW);
    analogReadResolution(12);
    g_temperature_sensors.begin();
    g_temperature_sensors.setResolution(tg_config::DS18B20_RESOLUTION_BITS);
    log_ds18b20_bus_state();

    os_init();
    LMIC_reset();

    if (tg_config::RAPID_DIAGNOSTIC_MODE) {
        Serial.println("DIAG: skipping LoRa join");
        do_send(&sendjob);
        return;
    }

    const std::uint8_t initial_subband = g_subband_fallback.current_subband();
    Serial.print("LMIC: initial US915 subband ");
    Serial.println(initial_subband);
    LMIC_selectSubBand(initial_subband);
    LMIC_setClockError(MAX_CLOCK_ERROR * 1 / 100);

    LMIC_startJoining();
}

void loop() {
    os_runloop_once();
    sleep_ms(tg_config::IDLE_LOOP_SLEEP_MS);
}
