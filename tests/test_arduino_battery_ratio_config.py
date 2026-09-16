from __future__ import annotations

from pathlib import Path


def test_battery_divider_ratio_matches_100k_over_22k_wiring() -> None:
    sketch_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "ttn_otaa_lmic.ino"
    content = sketch_path.read_text(encoding="utf-8")
    assert "static const float BATTERY_DIVIDER_RATIO = 1.545f;" in content
