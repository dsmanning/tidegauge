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

static uint8_t APPEUI[8];
static uint8_t DEVEUI[8];
static uint8_t APPKEY[16];

static osjob_t sendjob;
static const unsigned TX_INTERVAL_S = 300;
static const unsigned RETRY_INTERVAL_S = 5;

// HC-SR04 wiring (Adafruit Feather labels):
// TRIG -> D6, ECHO -> D5
static const int HCSR04_TRIG_PIN = D6;
static const int HCSR04_ECHO_PIN = D5;
static const unsigned long HCSR04_TIMEOUT_US = 30000UL;

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

static void do_send(osjob_t *j) {
    (void)j;

    if (LMIC.opmode & OP_TXRXPEND) {
        Serial.println("LMIC: TX/RX pending");
        os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(RETRY_INTERVAL_S), do_send);
    } else {
        digitalWrite(HCSR04_TRIG_PIN, LOW);
        delayMicroseconds(2);
        digitalWrite(HCSR04_TRIG_PIN, HIGH);
        delayMicroseconds(10);
        digitalWrite(HCSR04_TRIG_PIN, LOW);

        const unsigned long pulse_us = pulseIn(HCSR04_ECHO_PIN, HIGH, HCSR04_TIMEOUT_US);
        if (pulse_us == 0UL) {
            Serial.println("SENSOR: timeout waiting for echo pulse");
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(TX_INTERVAL_S), do_send);
            return;
        }

        const float measured_distance_m = (static_cast<float>(pulse_us) * 0.000343f) / 2.0f;
        float tide_height_m = 0.0f;
        if (!tidegauge::compute_tide_height_m(
                tg_config::GEOMETRY_REFERENCE_M, measured_distance_m, tg_config::DATUM_OFFSET_M, &tide_height_m)) {
            Serial.println("SENSOR: invalid tide height input");
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(TX_INTERVAL_S), do_send);
            return;
        }

        uint8_t payload[2] = {0, 0};
        if (!tidegauge::encode_tide_height_payload(tide_height_m, payload)) {
            Serial.println("PAYLOAD: tide height out of int16 range");
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(TX_INTERVAL_S), do_send);
            return;
        }

        LMIC_setTxData2(1, payload, sizeof(payload), 0);
        Serial.print("LMIC: queued uplink distance_m=");
        Serial.print(measured_distance_m, 3);
        Serial.print(" tide_height_m=");
        Serial.print(tide_height_m, 3);
        Serial.print(" payload=");
        Serial.print(payload[0], HEX);
        Serial.print(" ");
        Serial.println(payload[1], HEX);
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
            LMIC_setLinkCheckMode(0);
            do_send(&sendjob);
            break;
        case EV_JOIN_FAILED:
            Serial.println("EV_JOIN_FAILED");
            break;
        case EV_TXCOMPLETE:
            Serial.println("EV_TXCOMPLETE");
            if (LMIC.dataLen) {
                Serial.print("LMIC: downlink bytes=");
                Serial.println(LMIC.dataLen);
            }
            os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(TX_INTERVAL_S), do_send);
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

    os_init();
    LMIC_reset();

    LMIC_selectSubBand(tg_config::US915_SUBBAND);
    LMIC_setClockError(MAX_CLOCK_ERROR * 1 / 100);

    LMIC_startJoining();
}

void loop() {
    os_runloop_once();
}
