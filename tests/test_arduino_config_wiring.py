from pathlib import Path


def test_arduino_config_template_exists() -> None:
    template_path = Path("arduino/ttn_otaa_lmic/config.example.h")
    assert template_path.exists()
    content = template_path.read_text(encoding="utf-8")

    assert "DEV_EUI_HEX" in content
    assert "APP_EUI_HEX" in content
    assert "APP_KEY_HEX" in content
    assert "US915_SUBBAND" in content
    assert "LORA_ADR_ENABLED" in content
    assert "LORA_UPLINK_TX_POWER_DBM" in content
    assert "RAPID_DIAGNOSTIC_MODE" in content
    assert "RAPID_DIAGNOSTIC_INTERVAL_S" in content
    assert "ULTRASONIC_SAMPLE_COUNT" in content
    assert "ULTRASONIC_POWER_ENABLE_PIN" in content
    assert "ULTRASONIC_POWER_SETTLE_MS" in content
    assert "ULTRASONIC_TIMEOUT_US" in content
    assert "IDLE_LOOP_SLEEP_MS" in content
    assert "DS18B20_DATA_PIN" in content
    assert "DS18B20_RESOLUTION_BITS" in content
    assert "SPEED_OF_SOUND_M_PER_US" in content
    assert "GEOMETRY_REFERENCE_M" in content
    assert "DATUM_OFFSET_M" in content
    assert "inline constexpr bool RAPID_DIAGNOSTIC_MODE = false;" in content
    assert "inline constexpr std::size_t ULTRASONIC_SAMPLE_COUNT = 64;" in content


def test_sketch_uses_external_config_header() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert '"config.h"' in content
    assert '"config.example.h"' in content
    assert "<OneWire.h>" in content
    assert "<DallasTemperature.h>" in content
    assert "SubbandFallback g_subband_fallback(tg_config::US915_SUBBAND)" in content
    assert "LMIC_setAdrMode" in content
    assert "LMIC_setDrTxpow" in content
    assert "LMIC_selectSubBand(initial_subband)" in content
    assert "DallasTemperature" in content
    assert "OneWire" in content
    assert "tg_config::DS18B20_DATA_PIN" in content
    assert "tg_config::DS18B20_RESOLUTION_BITS" in content
    assert "sensors.setResolution" in content
    assert "sensors.requestTemperatures();" in content
    assert "sensors.getTempCByIndex(0)" in content
    assert "tg_config::ULTRASONIC_SAMPLE_COUNT" in content
    assert "tg_config::ULTRASONIC_TIMEOUT_US" in content
    assert "tg_config::ULTRASONIC_POWER_ENABLE_PIN" in content
    assert "tg_config::ULTRASONIC_POWER_SETTLE_MS" in content
    assert "tg_config::IDLE_LOOP_SLEEP_MS" in content
    assert "distance_from_pulse_us" in content
    assert "if (tg_config::RAPID_DIAGNOSTIC_MODE)" in content
    assert 'Serial.print("DIAG: sample[' in content


def test_sketch_reports_ultrasonic_diagnostic_summary_fields() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert 'Serial.print("DIAG: samples_valid=");' in content
    assert 'Serial.print(" samples_timeout=");' in content
    assert 'Serial.print(" pulse_min_us=");' in content
    assert 'Serial.print(" pulse_max_us=");' in content
    assert 'Serial.print(" echo_high_stuck=");' in content
    assert 'Serial.print(" temperature_c=");' in content


def test_sketch_reports_ds18b20_bus_diagnostics() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert 'Serial.print("DS18B20: device_count=");' in content
    assert 'Serial.print(" DS18B20: address=");' in content
    assert "g_temperature_sensors.getDeviceCount()" in content
    assert "g_temperature_sensors.getAddress(" in content


def test_sketch_uses_jsn_compatible_trigger_pulse_width() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "delayMicroseconds(20);" in content


def test_sketch_power_gates_sensor_when_configured_and_sleeps_in_idle_loop() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "power_on_ultrasonic_sensor();" in content
    assert "power_off_ultrasonic_sensor();" in content
    assert "pinMode(HCSR04_POWER_ENABLE_PIN, OUTPUT);" in content
    assert "sleep_ms(tg_config::IDLE_LOOP_SLEEP_MS);" in content


def test_sketch_does_not_include_temporary_join_diagnostics() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "CFG: subband=" not in content
    assert "CFG: eui_checksum=0x" not in content
    assert "eui_checksum(" not in content


def test_sketch_does_not_include_experimental_watchdog_sleep_path() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "watchdog_enable_caused_reboot()" not in content
    assert "enter_watchdog_deep_sleep(" not in content
    assert "restore_lmic_session_from_retained_state()" not in content
    assert "LMIC_setSession" not in content
    assert "LMIC_getSessionKeys" not in content
