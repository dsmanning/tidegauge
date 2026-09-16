from __future__ import annotations

from pathlib import Path


def test_rapid_diagnostic_mode_skips_lora_join_in_setup() -> None:
    sketch_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "ttn_otaa_lmic.ino"
    content = sketch_path.read_text(encoding="utf-8")
    assert 'Serial.println("DIAG: skipping LoRa join");' in content
    assert "do_send(&sendjob);" in content
