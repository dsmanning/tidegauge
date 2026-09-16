from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


def _decode_with_node(payload_bytes: list[int]) -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    decoder_path = repo_root / "ttn" / "uplink_decoder.js"

    script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({json.dumps(str(decoder_path))}, "utf8");
const context = {{}};
vm.createContext(context);
vm.runInContext(source, context);
const result = context.decodeUplink({{ bytes: {json.dumps(payload_bytes)} }});
process.stdout.write(JSON.stringify(result));
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "decode.js"
        script_path.write_text(script, encoding="utf-8")
        result = subprocess.run(
            ["node", str(script_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    return json.loads(result.stdout)


def test_decoder_handles_valid_ten_byte_payload() -> None:
    decoded = _decode_with_node([0x01, 0x1B, 0x02, 0xE6, 0x0F, 0x6E, 0x00, 0x12, 0x08, 0x4D])

    assert decoded == {
        "data": {
            "tide_height_mm": 283,
            "tide_height_m": 0.283,
            "raw_distance_mm": 742,
            "raw_distance_m": 0.742,
            "battery_mv": 3950,
            "battery_v": 3.95,
            "distance_stddev_mm": 18,
            "distance_stddev_m": 0.018,
            "temperature_centi_c": 2125,
            "temperature_c": 21.25,
        }
    }


def test_decoder_maps_invalid_sentinels_to_null() -> None:
    decoded = _decode_with_node([0x80, 0x00, 0xFF, 0xFF, 0x0F, 0x6E, 0xFF, 0xFF, 0x80, 0x00])

    assert decoded == {
        "data": {
            "tide_height_mm": None,
            "tide_height_m": None,
            "raw_distance_mm": None,
            "raw_distance_m": None,
            "battery_mv": 3950,
            "battery_v": 3.95,
            "distance_stddev_mm": None,
            "distance_stddev_m": None,
            "temperature_centi_c": None,
            "temperature_c": None,
        }
    }


def test_decoder_accepts_diagnostics_and_preserves_measurements() -> None:
    decoded = _decode_with_node([0x01, 0x1B, 0x02, 0xE6, 0xff, 0xff, 0, 18, 8, 77,
                                1, 12, 3, 2, 0, 1, 0, 0, 0, 2, 60, 4, 0, 5, 0, 33])['data']
    assert decoded['tide_height_m'] == .283
    assert decoded['battery_v'] is None
    assert decoded['diagnostic_version'] == 1
    assert decoded['firmware_revision'] == 2
    assert decoded['uptime_s'] == 65536
    assert decoded['reset_reason'] == 3
    assert decoded['recovery_count'] == 2
    assert decoded['valid_samples'] == 60
    assert decoded['timeout_samples'] == 4
    assert decoded['watchdog_boots'] == 5
    assert decoded['measurement_sequence'] == 33
    assert decoded['fault_flags'] == 12


def test_decoder_accepts_compact_session_marker_payload() -> None:
    decoded = _decode_with_node([
        0x01, 0x1B, 0x02, 0xE6, 0x0F, 0x6E, 0x00, 0x12, 0x08, 0x4D, 0x95,
    ])
    assert decoded["data"]["sample_sequence"] == 0x15
    assert decoded["data"]["session_start"] is True


def test_decoder_accepts_legacy_twelve_byte_sequence_payload() -> None:
    decoded = _decode_with_node([
        0x01, 0x1B, 0x02, 0xE6, 0x0F, 0x6E, 0x00, 0x12, 0x08, 0x4D, 0x12, 0x34,
    ])
    assert decoded["data"]["sample_sequence"] == 0x1234


def test_decoder_rejects_unknown_diagnostic_schema_and_wrong_lengths() -> None:
    assert 'errors' in _decode_with_node([0] * 9)
    assert 'errors' in _decode_with_node([0] * 13)
    assert 'errors' in _decode_with_node([0] * 26)
