#include <Arduino.h>
#include <SPI.h>
#include <pico/time.h>
#include <hardware/watchdog.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <lmic.h>
#include <hal/hal.h>
#if __has_include("config.h")
#include "config.h"
#else
#include "config.example.h"
#endif
#include "runtime_config.h"
#include "src/app/node_runtime.h"
#include "src/adapters/arduino_sensor.h"
#include "src/adapters/lmic_radio.h"
#include "src/adapters/nonce_storage.h"

static_assert(tg_config::US915_SUBBAND >= 1 && tg_config::US915_SUBBAND <= 8, "Subband must be 1..8");
static_assert(tg_config::ULTRASONIC_SAMPLE_COUNT >= 3 && tg_config::ULTRASONIC_SAMPLE_COUNT <= 100, "Sample count must be 3..100");
static_assert(tg_config::ULTRASONIC_TIMEOUT_US > 0 && tg_config::ULTRASONIC_TIMEOUT_US <= 45000, "Echo deadline must be <=45ms");
static_assert(tg_config::ULTRASONIC_POWER_SETTLE_MS <= 5000 && tg_config::ULTRASONIC_INTERSAMPLE_DELAY_MS <= 100, "Sensor cycle must fit 30s deadline");
static_assert(tg_config::DS18B20_RESOLUTION_BITS >= 9 && tg_config::DS18B20_RESOLUTION_BITS <= 12, "DS18B20 resolution must be 9..12");
static_assert(tg_config::IDLE_LOOP_SLEEP_MS <= 10, "LMIC must be serviced frequently");
static_assert(tg_config::RAPID_DIAGNOSTIC_INTERVAL_S > 0, "Sampling interval must be positive");
static_assert(TIDEGAUGE_MIN_DISTANCE_M > 0 && TIDEGAUGE_MAX_DISTANCE_M > TIDEGAUGE_MIN_DISTANCE_M, "Invalid sensor range");

static uint8_t APPEUI[8], DEVEUI[8], APPKEY[16];
static const int HCSR04_TRIG_PIN = D6;
static const int HCSR04_ECHO_PIN = D5;
static const int HCSR04_POWER_ENABLE_PIN = tg_config::ULTRASONIC_POWER_ENABLE_PIN;
static const int BATTERY_ADC_PIN = 26;
static const float BATTERY_DIVIDER_RATIO = 1.545f;
static OneWire g_one_wire(tg_config::DS18B20_DATA_PIN);
static DallasTemperature g_temperature_sensors(&g_one_wire);
static tidegauge::SubbandFallback g_subband_fallback(tg_config::US915_SUBBAND);
static osjob_t sendjob;

void os_getArtEui(u1_t* buf) {memcpy(buf,APPEUI,8);}
void os_getDevEui(u1_t* buf) {memcpy(buf,DEVEUI,8);}
void os_getDevKey(u1_t* buf) {memcpy(buf,APPKEY,16);}
const lmic_pinmap lmic_pins = {
    .nss=PIN_RFM_CS, .rxtx=LMIC_UNUSED_PIN, .rst=PIN_RFM_RST,
    .dio={PIN_RFM_DIO0,PIN_RFM_DIO1,PIN_RFM_DIO2},
};

class ArduinoClock : public tidegauge::ClockPort {
    uint32_t now_ms() override {return millis();}
};
class HardwareWatchdog : public tidegauge::WatchdogPort {
public:
    void feed() override {watchdog_update();}
    void reboot(uint8_t reason) override {
        watchdog_hw->scratch[2]=reason;
        watchdog_reboot(0,0,0);
        while(true) {} // Do not feed after requesting recovery.
    }
};
static ArduinoClock g_clock;
static HardwareWatchdog g_watchdog;
static tidegauge::LittleFsNonceStorage g_storage;
static tidegauge::JoinNonce g_nonce(g_storage);
static tidegauge::LmicRadio g_radio(g_clock,g_nonce,g_subband_fallback,
    tg_config::LORA_ADR_ENABLED,tg_config::LORA_UPLINK_TX_POWER_DBM);
static tidegauge::ArduinoSensor g_sensor_hardware(g_temperature_sensors,
    HCSR04_TRIG_PIN,HCSR04_ECHO_PIN,HCSR04_POWER_ENABLE_PIN,BATTERY_ADC_PIN,
    BATTERY_DIVIDER_RATIO,tg_config::ULTRASONIC_TIMEOUT_US,tg_config::DS18B20_RESOLUTION_BITS);

static tidegauge::SensorSettings sensor_settings() {
    tidegauge::SensorSettings s;
    s.samples=tg_config::ULTRASONIC_SAMPLE_COUNT;
    s.minimum_valid=s.samples/4>3 ? s.samples/4 : 3;
    s.settle_ms=HCSR04_POWER_ENABLE_PIN>=0 ? tg_config::ULTRASONIC_POWER_SETTLE_MS : 0;
    s.gap_ms=tg_config::ULTRASONIC_INTERSAMPLE_DELAY_MS;
    s.speed=tg_config::SPEED_OF_SOUND_M_PER_US;
    s.scale=tg_config::DISTANCE_SCALE; s.offset=tg_config::DISTANCE_OFFSET_M;
    s.reference=tg_config::GEOMETRY_REFERENCE_M; s.datum=tg_config::DATUM_OFFSET_M;
    s.min_distance=TIDEGAUGE_MIN_DISTANCE_M; s.max_distance=TIDEGAUGE_MAX_DISTANCE_M;
    return s;
}
static tidegauge::SensorCycle g_sensor(g_sensor_hardware,sensor_settings());
static tidegauge::NodeRuntime g_node(g_clock,g_sensor,g_radio,g_watchdog,
    tg_config::RAPID_DIAGNOSTIC_MODE ? tg_config::RAPID_DIAGNOSTIC_INTERVAL_S*1000 : 60000,
    tg_config::RAPID_DIAGNOSTIC_MODE);

static bool hex_to_bytes(const char* hex,uint8_t* out,size_t count) {
    if(strlen(hex)!=count*2) return false;
    for(size_t i=0;i<count;++i) {
        uint8_t value=0;
        for(unsigned j=0;j<2;++j) {
            const char c=hex[i*2+j];
            const int digit=c>='0' && c<='9' ? c-'0' :
                c>='a' && c<='f' ? c-'a'+10 : c>='A' && c<='F' ? c-'A'+10 : -1;
            if(digit<0) return false;
            value=static_cast<uint8_t>((value<<4)|digit);
        }
        out[i]=value;
    }
    return true;
}
static void reverse_bytes(uint8_t* bytes,size_t size) {
    for(size_t i=0;i<size/2;++i) {uint8_t b=bytes[i]; bytes[i]=bytes[size-1-i]; bytes[size-1-i]=b;}
}

// Never autoformat a damaged filesystem: losing the nonce journal permits reuse.
// Formatting is allowed only on a completely erased, allocated FS region.
extern uint8_t _FS_start, _FS_end;
static bool mount_nonce_storage() {
    const uintptr_t start=reinterpret_cast<uintptr_t>(&_FS_start);
    const uintptr_t end=reinterpret_cast<uintptr_t>(&_FS_end);
    if(end<=start || end-start<65536) return false;
    LittleFS.setConfig(LittleFSConfig(false));
    if(LittleFS.begin()) return true;
    for(uintptr_t address=start;address<end;++address) {
        if(*reinterpret_cast<const uint8_t*>(address)!=0xff) return false;
    }
    return LittleFS.format() && LittleFS.begin();
}

static void do_send(osjob_t*) {
    g_node.tick();
    static uint32_t logged=0;
    if(logged!=g_node.measurements) {
        logged=g_node.measurements;
        // Logging is best-effort and only after a completed measurement.
        if(Serial && Serial.availableForWrite()>=48) {
            Serial.print("MEASURE: height="); Serial.print(g_node.latest.height,3);
            Serial.print(" temperature_c="); Serial.println(g_node.latest.temperature,2);
        }
    }
}
void onEvent(ev_t event) {
    g_radio.on_event(event);
    if(Serial && Serial.availableForWrite()>=32) {
        Serial.print("LMIC event="); Serial.println(static_cast<unsigned>(event));
    }
}

void setup() {
    const bool watchdog_boot=watchdog_caused_reboot();
    const uint32_t magic=0x54474432;
    if(watchdog_boot && watchdog_hw->scratch[0]==magic) {
        g_node.watchdog_boots=static_cast<uint16_t>(watchdog_hw->scratch[1]+1);
        g_node.reset_reason=watchdog_hw->scratch[2] ? watchdog_hw->scratch[2] : 3;
    } else {
        g_node.watchdog_boots=watchdog_boot ? 1 : 0;
        g_node.reset_reason=watchdog_boot ? 3 : 0;
    }
    watchdog_hw->scratch[0]=magic;
    watchdog_hw->scratch[1]=g_node.watchdog_boots;
    watchdog_hw->scratch[2]=0;
    watchdog_enable(TIDEGAUGE_WATCHDOG_TIMEOUT_MS, true);
    Serial.begin(115200);
    while (!Serial && millis()<3000) {}
    if(watchdog_boot) Serial.println("WATCHDOG: reboot detected");
    Serial.println("Tide gauge firmware 2 starting");

    pinMode(HCSR04_TRIG_PIN,OUTPUT); pinMode(HCSR04_ECHO_PIN,INPUT);
    if(HCSR04_POWER_ENABLE_PIN>=0) pinMode(HCSR04_POWER_ENABLE_PIN, OUTPUT);
    g_sensor.reset(); digitalWrite(HCSR04_TRIG_PIN,LOW); analogReadResolution(12);
    watchdog_update();
    const bool credentials_ok=hex_to_bytes(tg_config::APP_EUI_HEX,APPEUI,sizeof(APPEUI)) &&
        hex_to_bytes(tg_config::DEV_EUI_HEX,DEVEUI,sizeof(DEVEUI)) &&
        hex_to_bytes(tg_config::APP_KEY_HEX,APPKEY,sizeof(APPKEY));
    if(!credentials_ok) {
        Serial.println("Invalid credentials: radio disabled; sampling continues");
    }
    reverse_bytes(APPEUI,sizeof(APPEUI)); reverse_bytes(DEVEUI,sizeof(DEVEUI));
    if (tg_config::RAPID_DIAGNOSTIC_MODE) {
        Serial.println("DIAG: skipping LoRa join");
        do_send(&sendjob);
        return;
    }
    g_storage.set_ready(credentials_ok && mount_nonce_storage());
    watchdog_update();
    os_init();
    watchdog_update();
    g_radio.begin();
}

void loop() {
    if(!tg_config::RAPID_DIAGNOSTIC_MODE) {
        g_radio.service();
        os_runloop_once();
    }
    do_send(&sendjob);
    static bool storage_error_logged=false;
    if(g_radio.storage_failed() && !storage_error_logged && Serial) {
        Serial.println("NONCE: storage unavailable/corrupt/exhausted; radio disabled");
        storage_error_logged=true;
    }
    sleep_ms(tg_config::IDLE_LOOP_SLEEP_MS);
}
