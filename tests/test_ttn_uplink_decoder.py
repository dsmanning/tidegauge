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
