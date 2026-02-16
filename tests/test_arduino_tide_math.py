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


def test_encode_tide_distance_and_battery_payload() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            std::uint8_t payload[6] = {0, 0, 0, 0, 0, 0};
            if (!tidegauge::encode_tide_distance_battery_payload(0.283f, 0.742f, 3.95f, payload)) {
                return 1;
            }
            std::cout
                << static_cast<unsigned>(payload[0]) << " "
                << static_cast<unsigned>(payload[1]) << " "
                << static_cast<unsigned>(payload[2]) << " "
                << static_cast<unsigned>(payload[3]) << " "
                << static_cast<unsigned>(payload[4]) << " "
                << static_cast<unsigned>(payload[5]);
            return 0;
        }
        """
    )

    assert output == "1 27 2 230 15 110"


def test_apply_distance_calibration_scale_and_offset() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float corrected_m = 0.0f;
            if (!tidegauge::apply_distance_calibration_m(1.250f, 0.990f, -0.015f, &corrected_m)) {
                return 1;
            }
            std::cout << std::fixed << std::setprecision(4) << corrected_m;
            return 0;
        }
        """
    )

    assert output == "1.2225"


def test_apply_distance_calibration_rejects_negative_result() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float corrected_m = 0.0f;
            std::cout << (tidegauge::apply_distance_calibration_m(0.020f, 1.000f, -0.050f, &corrected_m) ? "ok" : "invalid");
            return 0;
        }
        """
    )

    assert output == "invalid"


def test_median_distance_filters_outlier() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float samples[5] = {1.002f, 0.998f, 3.500f, 1.001f, 0.999f};
            float result_m = 0.0f;
            if (!tidegauge::median_distance_m(samples, 5, &result_m)) {
                return 1;
            }
            std::cout << std::fixed << std::setprecision(3) << result_m;
            return 0;
        }
        """
    )

    assert output == "1.001"


def test_median_distance_requires_non_negative_samples() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float samples[3] = {1.0f, -0.1f, 1.1f};
            float result_m = 0.0f;
            std::cout << (tidegauge::median_distance_m(samples, 3, &result_m) ? "ok" : "invalid");
            return 0;
        }
        """
    )

    assert output == "invalid"


def test_median_distance_supports_ten_samples() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float samples[10] = {1.50f, 1.49f, 1.51f, 1.50f, 1.52f, 1.50f, 1.48f, 1.50f, 1.90f, 1.50f};
            float result_m = 0.0f;
            if (!tidegauge::median_distance_m(samples, 10, &result_m)) {
                return 1;
            }
            std::cout << std::fixed << std::setprecision(3) << result_m;
            return 0;
        }
        """
    )

    assert output == "1.500"


def test_distance_from_pulse_us_uses_configurable_speed_of_sound() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float distance_m = 0.0f;
            if (!tidegauge::distance_from_pulse_us(5831UL, 0.000343f, &distance_m)) {
                return 1;
            }
            std::cout << std::fixed << std::setprecision(3) << distance_m;
            return 0;
        }
        """
    )

    assert output == "1.000"


def test_distance_from_pulse_us_rejects_invalid_inputs() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float distance_m = 0.0f;
            std::cout
                << (tidegauge::distance_from_pulse_us(0UL, 0.000343f, &distance_m) ? "ok" : "invalid")
                << " "
                << (tidegauge::distance_from_pulse_us(1000UL, 0.0f, &distance_m) ? "ok" : "invalid");
            return 0;
        }
        """
    )

    assert output == "invalid invalid"
