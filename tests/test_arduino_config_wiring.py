from pathlib import Path


def test_arduino_config_template_exists() -> None:
    template_path = Path("arduino/ttn_otaa_lmic/config.example.h")
    assert template_path.exists()
    content = template_path.read_text(encoding="utf-8")

    assert "DEV_EUI_HEX" in content
    assert "APP_EUI_HEX" in content
    assert "APP_KEY_HEX" in content
    assert "US915_SUBBAND" in content
    assert "GEOMETRY_REFERENCE_M" in content
    assert "DATUM_OFFSET_M" in content


def test_sketch_uses_external_config_header() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert '"config.h"' in content
    assert '"config.example.h"' in content
    assert "LMIC_selectSubBand(tg_config::US915_SUBBAND)" in content


def test_sketch_does_not_include_temporary_join_diagnostics() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "CFG: subband=" not in content
    assert "CFG: eui_checksum=0x" not in content
    assert "eui_checksum(" not in content
