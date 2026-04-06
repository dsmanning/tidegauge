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
            std::uint8_t payload[10] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
            if (!tidegauge::encode_tide_distance_battery_payload(0.283f, 0.742f, 3.95f, 0.018f, 21.25f, payload)) {
                return 1;
            }
            std::cout
                << static_cast<unsigned>(payload[0]) << " "
                << static_cast<unsigned>(payload[1]) << " "
                << static_cast<unsigned>(payload[2]) << " "
                << static_cast<unsigned>(payload[3]) << " "
                << static_cast<unsigned>(payload[4]) << " "
                << static_cast<unsigned>(payload[5]) << " "
                << static_cast<unsigned>(payload[6]) << " "
                << static_cast<unsigned>(payload[7]) << " "
                << static_cast<unsigned>(payload[8]) << " "
                << static_cast<unsigned>(payload[9]);
            return 0;
        }
        """
    )

    assert output == "1 27 2 230 15 110 0 18 8 77"


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


def test_median_distance_supports_one_hundred_samples() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float samples[100];
            for (int i = 0; i < 100; ++i) {
                samples[i] = 2.195f + ((i % 5) * 0.0001f);
            }
            float result_m = 0.0f;
            if (!tidegauge::median_distance_m(samples, 100, &result_m)) {
                return 1;
            }
            std::cout << std::fixed << std::setprecision(4) << result_m;
            return 0;
        }
        """
    )

    assert output == "2.1952"


def test_furthest_cluster_distance_stats_prefers_long_cluster() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float samples[12] = {
                0.6733f, 0.6774f, 0.6903f,
                1.0822f, 1.0865f,
                2.2187f, 2.2190f, 2.2192f, 2.2192f, 2.2194f, 2.2194f, 2.2196f
            };
            float median_m = 0.0f;
            float stddev_m = 0.0f;
            if (!tidegauge::furthest_cluster_distance_stats_m(samples, 12, 0.15f, 3, &median_m, &stddev_m)) {
                return 1;
            }
            std::cout << std::fixed << std::setprecision(4) << median_m << " " << stddev_m;
            return 0;
        }
        """
    )

    assert output == "2.2192 0.0003"


def test_furthest_cluster_distance_stats_rejects_tiny_far_outlier_cluster() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float samples[7] = {0.6733f, 0.6735f, 0.6774f, 0.6903f, 0.6903f, 2.2192f, 2.2194f};
            float median_m = 0.0f;
            float stddev_m = 0.0f;
            if (!tidegauge::furthest_cluster_distance_stats_m(samples, 7, 0.15f, 3, &median_m, &stddev_m)) {
                return 1;
            }
            std::cout << median_m;
            return 0;
        }
        """
    )

    assert output == "0.6774"


def test_distance_stddev_m_computes_population_standard_deviation() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float samples[4] = {1.20f, 1.20f, 1.20f, 1.40f};
            float stddev_m = 0.0f;
            if (!tidegauge::distance_stddev_m(samples, 4, &stddev_m)) {
                return 1;
            }
            std::cout << std::fixed << std::setprecision(4) << stddev_m;
            return 0;
        }
        """
    )

    assert output == "0.0866"


def test_distance_stddev_m_rejects_invalid_inputs() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float valid_samples[2] = {1.0f, 1.1f};
            float invalid_samples[2] = {1.0f, -0.1f};
            float stddev_m = 0.0f;
            std::cout
                << (tidegauge::distance_stddev_m(valid_samples, 0, &stddev_m) ? "ok" : "invalid")
                << " "
                << (tidegauge::distance_stddev_m(invalid_samples, 2, &stddev_m) ? "ok" : "invalid");
            return 0;
        }
        """
    )

    assert output == "invalid invalid"


def test_distance_stddev_m_supports_one_hundred_samples() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float samples[100];
            for (int i = 0; i < 100; ++i) {
                samples[i] = 2.195f + ((i % 5) * 0.0001f);
            }
            float stddev_m = 0.0f;
            if (!tidegauge::distance_stddev_m(samples, 100, &stddev_m)) {
                return 1;
            }
            std::cout << std::fixed << std::setprecision(4) << stddev_m;
            return 0;
        }
        """
    )

    assert output == "0.0001"


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

def test_battery_voltage_from_adc_raw_uses_configured_divider_ratio() -> None:
    output = _compile_and_run(
        """
        #include <iomanip>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            float battery_v = 0.0f;
            const float divider_ratio = 31.95f / 21.95f;
            if (!tidegauge::battery_voltage_from_adc_raw(3296, 3.3f, 4095, divider_ratio, &battery_v)) {
                return 1;
            }
            std::cout << std::fixed << std::setprecision(3) << battery_v;
            return 0;
        }
        """
    )

    assert output == "3.866"


def test_encode_temperature_payload_encodes_signed_centidegrees() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            std::uint8_t payload[2] = {0, 0};
            if (!tidegauge::encode_temperature_payload(21.25f, payload)) {
                return 1;
            }
            std::cout
                << static_cast<unsigned>(payload[0]) << " "
                << static_cast<unsigned>(payload[1]);
            return 0;
        }
        """
    )

    assert output == "8 77"


def test_encode_temperature_payload_supports_negative_temperatures() -> None:
    output = _compile_and_run(
        """
        #include <iostream>
        #include "tide_math.h"

        int main() {
            std::uint8_t payload[2] = {0, 0};
            if (!tidegauge::encode_temperature_payload(-3.50f, payload)) {
                return 1;
            }
            std::cout
                << static_cast<unsigned>(payload[0]) << " "
                << static_cast<unsigned>(payload[1]);
            return 0;
        }
        """
    )

    assert output == "254 162"


def test_encode_payload_uses_invalid_sentinels_for_nan_measurements() -> None:
    output = _compile_and_run(
        """
        #include <cmath>
        #include <iostream>
        #include "tide_math.h"

        int main() {
            std::uint8_t payload[10] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
            if (!tidegauge::encode_tide_distance_battery_payload(
                    NAN,
                    NAN,
                    3.95f,
                    NAN,
                    NAN,
                    payload)) {
                return 1;
            }
            std::cout
                << static_cast<unsigned>(payload[0]) << " "
                << static_cast<unsigned>(payload[1]) << " "
                << static_cast<unsigned>(payload[2]) << " "
                << static_cast<unsigned>(payload[3]) << " "
                << static_cast<unsigned>(payload[4]) << " "
                << static_cast<unsigned>(payload[5]) << " "
                << static_cast<unsigned>(payload[6]) << " "
                << static_cast<unsigned>(payload[7]) << " "
                << static_cast<unsigned>(payload[8]) << " "
                << static_cast<unsigned>(payload[9]);
            return 0;
        }
        """
    )

    assert output == "128 0 255 255 15 110 255 255 128 0"
