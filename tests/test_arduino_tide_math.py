from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def _compile_and_run(program_source: str) -> str:
    repo_root = Path(__file__).resolve().parents[1]
    include_dir = repo_root / "arduino" / "ttn_otaa_lmic"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        source_path = tmp_path / "main.cpp"
        binary_path = tmp_path / "main"
        source_path.write_text(program_source, encoding="utf-8")

        subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-I",
                str(include_dir),
                str(source_path),
                "-o",
                str(binary_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        result = subprocess.run(
            [str(binary_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()


def test_compute_tide_height_and_payload_encoding() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float tide_height_m = 0.0f;
            if (!tidegauge::compute_tide_height_m(2.5f, 0.75f, 0.2f, &tide_height_m)) {
                return 1;
            }

            std::uint8_t payload[2] = {0, 0};
            if (!tidegauge::encode_tide_height_payload(tide_height_m, payload)) {
                return 2;
            }

            std::cout << std::fixed << std::setprecision(3) << tide_height_m << " "
                      << static_cast<unsigned>(payload[0]) << " "
                      << static_cast<unsigned>(payload[1]);
            return 0;
        }
        """
    )

    assert output == "1.550 6 14"


def test_compute_tide_height_rejects_negative_distance() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float tide_height_m = 0.0f;
            std::cout << (tidegauge::compute_tide_height_m(2.5f, -0.01f, 0.2f, &tide_height_m) ? "ok" : "invalid");
            return 0;
        }
        """
    )

    assert output == "invalid"


def test_encode_tide_height_rejects_out_of_range_payload() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            std::uint8_t payload[2] = {0, 0};
            std::cout << (tidegauge::encode_tide_height_payload(50.0f, payload) ? "ok" : "invalid");
            return 0;
        }
        """
    )

    assert output == "invalid"
