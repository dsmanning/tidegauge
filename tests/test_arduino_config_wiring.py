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
    assert "TIDEGAUGE_WATCHDOG_TIMEOUT_MS" in content
    assert "DS18B20_DATA_PIN" in content
    assert "DS18B20_RESOLUTION_BITS" in content
    assert "SPEED_OF_SOUND_M_PER_US" in content
    assert "GEOMETRY_REFERENCE_M" in content
    assert "DATUM_OFFSET_M" in content
    assert "inline constexpr bool RAPID_DIAGNOSTIC_MODE = false;" in content
    assert "inline constexpr std::size_t ULTRASONIC_SAMPLE_COUNT = 64;" in content


def test_sketch_wires_the_tested_adapters_and_runtime() -> None:
    content = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino").read_text()
    assert '#include "config.h"' in content
    assert '#include "config.example.h"' in content
    assert 'tidegauge::ArduinoSensor g_sensor_hardware' in content
    assert 'tidegauge::LmicRadio g_radio' in content
    assert 'tidegauge::NodeRuntime g_node' in content
    assert 'tg_config::LORA_ADR_ENABLED,tg_config::LORA_UPLINK_TX_POWER_DBM' in content
    assert 'tg_config::ULTRASONIC_TIMEOUT_US,tg_config::DS18B20_RESOLUTION_BITS' in content
    assert 'watchdog_enable(TIDEGAUGE_WATCHDOG_TIMEOUT_MS, true);' in content
    assert 'Serial.println("WATCHDOG: reboot detected");' in content
    assert 'g_radio.on_event(event);' in content
    assert 'sleep_ms(tg_config::IDLE_LOOP_SLEEP_MS);' in content

# Behavioral coverage lives in test_arduino_resilience.py and the executable
# radio/sensor/storage contract tests, rather than asserting source substrings.
