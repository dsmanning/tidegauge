#ifndef TIDEGAUGE_TIDE_MATH_H
#define TIDEGAUGE_TIDE_MATH_H

#include <cmath>
#include <cstddef>
#include <cstdint>

namespace tidegauge {

inline bool compute_tide_height_m(
    float geometry_reference_m,
    float measured_distance_m,
    float datum_offset_m,
    float *out_tide_height_m
) {
    if (out_tide_height_m == nullptr || measured_distance_m < 0.0f) {
        return false;
    }

    *out_tide_height_m = geometry_reference_m - measured_distance_m - datum_offset_m;
    return true;
}

inline bool apply_distance_calibration_m(
    float measured_distance_m,
    float distance_scale,
    float distance_offset_m,
    float *out_corrected_distance_m
) {
    if (out_corrected_distance_m == nullptr || measured_distance_m < 0.0f || distance_scale <= 0.0f) {
        return false;
    }

    const float corrected_m = (measured_distance_m * distance_scale) + distance_offset_m;
    if (corrected_m < 0.0f) {
        return false;
    }

    *out_corrected_distance_m = corrected_m;
    return true;
}

inline bool distance_from_pulse_us(
    unsigned long pulse_us,
    float speed_of_sound_m_per_us,
    float *out_distance_m
) {
    if (out_distance_m == nullptr || pulse_us == 0UL || speed_of_sound_m_per_us <= 0.0f) {
        return false;
    }

    *out_distance_m = (static_cast<float>(pulse_us) * speed_of_sound_m_per_us) / 2.0f;
    return true;
}

inline bool median_distance_m(const float *samples_m, std::size_t count, float *out_median_m) {
    if (samples_m == nullptr || out_median_m == nullptr || count == 0 || count > 16) {
        return false;
    }

    float sorted[16];
    for (std::size_t i = 0; i < count; ++i) {
        if (samples_m[i] < 0.0f) {
            return false;
        }
        sorted[i] = samples_m[i];
    }

    for (std::size_t i = 1; i < count; ++i) {
        const float v = sorted[i];
        std::size_t j = i;
        while (j > 0 && sorted[j - 1] > v) {
            sorted[j] = sorted[j - 1];
            --j;
        }
        sorted[j] = v;
    }

    *out_median_m = sorted[count / 2];
    return true;
}

inline bool encode_tide_height_payload(float tide_height_m, std::uint8_t out_payload[2]) {
    if (out_payload == nullptr) {
        return false;
    }

    const long tide_height_mm = lroundf(tide_height_m * 1000.0f);
    if (tide_height_mm < -32768L || tide_height_mm > 32767L) {
        return false;
    }

    const std::int16_t signed_mm = static_cast<std::int16_t>(tide_height_mm);
    out_payload[0] = static_cast<std::uint8_t>((signed_mm >> 8) & 0xFF);
    out_payload[1] = static_cast<std::uint8_t>(signed_mm & 0xFF);
    return true;
}

inline bool encode_distance_battery_payload(
    float measured_distance_m,
    float battery_voltage_v,
    std::uint8_t out_payload[4]
) {
    if (out_payload == nullptr || measured_distance_m < 0.0f || battery_voltage_v < 0.0f) {
        return false;
    }

    const long distance_mm = lroundf(measured_distance_m * 1000.0f);
    if (distance_mm < 0L || distance_mm > 65535L) {
        return false;
    }

    const long battery_mv = lroundf(battery_voltage_v * 1000.0f);
    if (battery_mv < 0L || battery_mv > 65535L) {
        return false;
    }

    out_payload[0] = static_cast<std::uint8_t>((distance_mm >> 8) & 0xFF);
    out_payload[1] = static_cast<std::uint8_t>(distance_mm & 0xFF);
    out_payload[2] = static_cast<std::uint8_t>((battery_mv >> 8) & 0xFF);
    out_payload[3] = static_cast<std::uint8_t>(battery_mv & 0xFF);
    return true;
}

inline bool encode_tide_distance_battery_payload(
    float tide_height_m,
    float measured_distance_m,
    float battery_voltage_v,
    std::uint8_t out_payload[6]
) {
    if (out_payload == nullptr) {
        return false;
    }

    std::uint8_t tide_payload[2] = {0, 0};
    if (!encode_tide_height_payload(tide_height_m, tide_payload)) {
        return false;
    }

    std::uint8_t distance_battery_payload[4] = {0, 0, 0, 0};
    if (!encode_distance_battery_payload(measured_distance_m, battery_voltage_v, distance_battery_payload)) {
        return false;
    }

    out_payload[0] = tide_payload[0];
    out_payload[1] = tide_payload[1];
    out_payload[2] = distance_battery_payload[0];
    out_payload[3] = distance_battery_payload[1];
    out_payload[4] = distance_battery_payload[2];
    out_payload[5] = distance_battery_payload[3];
    return true;
}

}  // namespace tidegauge

#endif
