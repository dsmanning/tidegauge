#ifndef TIDEGAUGE_TIDE_MATH_H
#define TIDEGAUGE_TIDE_MATH_H

#include <cmath>
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

}  // namespace tidegauge

#endif
