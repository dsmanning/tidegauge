from pathlib import Path


def test_arduino_config_template_exists() -> None:
    template_path = Path("arduino/ttn_otaa_lmic/config.example.h")
    assert template_path.exists()
    content = template_path.read_text(encoding="utf-8")

    assert "DEV_EUI_HEX" in content
    assert "APP_EUI_HEX" in content
    assert "APP_KEY_HEX" in content
    assert "US915_SUBBAND" in content
    assert "RAPID_DIAGNOSTIC_MODE" in content
    assert "RAPID_DIAGNOSTIC_INTERVAL_S" in content
    assert "ULTRASONIC_SAMPLE_COUNT" in content
    assert "ULTRASONIC_TIMEOUT_US" in content
    assert "SPEED_OF_SOUND_M_PER_US" in content
    assert "GEOMETRY_REFERENCE_M" in content
    assert "DATUM_OFFSET_M" in content


def test_sketch_uses_external_config_header() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert '"config.h"' in content
    assert '"config.example.h"' in content
    assert "SubbandFallback g_subband_fallback(tg_config::US915_SUBBAND)" in content
    assert "LMIC_selectSubBand(initial_subband)" in content
    assert "tg_config::ULTRASONIC_SAMPLE_COUNT" in content
    assert "tg_config::ULTRASONIC_TIMEOUT_US" in content
    assert "distance_from_pulse_us" in content
    assert "if (tg_config::RAPID_DIAGNOSTIC_MODE)" in content
    assert 'Serial.print("DIAG: sample[' in content


def test_sketch_does_not_include_temporary_join_diagnostics() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "CFG: subband=" not in content
    assert "CFG: eui_checksum=0x" not in content
    assert "eui_checksum(" not in content
