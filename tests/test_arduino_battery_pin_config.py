from __future__ import annotations

from pathlib import Path


def test_battery_adc_pin_is_a26_gpio26() -> None:
    sketch_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "ttn_otaa_lmic.ino"
    content = sketch_path.read_text(encoding="utf-8")
    assert "static const int BATTERY_ADC_PIN = 26;" in content
