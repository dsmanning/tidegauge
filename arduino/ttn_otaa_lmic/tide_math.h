#ifndef TIDEGAUGE_TIDE_MATH_H
#define TIDEGAUGE_TIDE_MATH_H

#include <cmath>
#include <cstddef>
#include <cstdint>

namespace tidegauge {

inline constexpr std::uint16_t INVALID_UNSIGNED_16 = 0xFFFFu;
inline constexpr std::int16_t INVALID_SIGNED_16 = static_cast<std::int16_t>(0x8000);

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

inline bool battery_voltage_from_adc_raw(
    int raw_adc,
    float adc_reference_v,
    int adc_max_raw,
    float battery_divider_ratio,
    float *out_battery_v
) {
    if (out_battery_v == nullptr || raw_adc < 0 || adc_max_raw <= 0 ||
        adc_reference_v <= 0.0f || battery_divider_ratio <= 0.0f) {
        return false;
    }
    if (raw_adc > adc_max_raw) {
        return false;
    }

    const float adc_v = (static_cast<float>(raw_adc) * adc_reference_v) / static_cast<float>(adc_max_raw);
    *out_battery_v = adc_v * battery_divider_ratio;
    return true;
}

inline bool median_distance_m(const float *samples_m, std::size_t count, float *out_median_m) {
    if (samples_m == nullptr || out_median_m == nullptr || count == 0 || count > 100) {
        return false;
    }

    float sorted[100];
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

inline bool furthest_cluster_distance_stats_m(
    const float *samples_m,
    std::size_t count,
    float cluster_gap_threshold_m,
    std::size_t min_cluster_count,
    float *out_median_m,
    float *out_stddev_m
) {
    if (samples_m == nullptr || out_median_m == nullptr || out_stddev_m == nullptr ||
        count == 0 || count > 100 || cluster_gap_threshold_m <= 0.0f || min_cluster_count == 0) {
        return false;
    }

    float sorted[100];
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

    std::size_t selected_start = count;
    std::size_t selected_end = count;
    std::size_t cluster_end = count;
    while (cluster_end > 0) {
        std::size_t cluster_start = cluster_end - 1;
        while (cluster_start > 0 &&
               (sorted[cluster_start] - sorted[cluster_start - 1]) <= cluster_gap_threshold_m) {
            --cluster_start;
        }

        const std::size_t cluster_size = cluster_end - cluster_start;
        if (cluster_size >= min_cluster_count) {
            selected_start = cluster_start;
            selected_end = cluster_end;
            break;
        }
        cluster_end = cluster_start;
    }

    if (selected_start == count) {
        selected_start = 0;
        selected_end = count;
    }

    const std::size_t selected_count = selected_end - selected_start;
    if (selected_count == 0) {
        return false;
    }

    *out_median_m = sorted[selected_start + (selected_count / 2)];

    float sum_m = 0.0f;
    for (std::size_t i = selected_start; i < selected_end; ++i) {
        sum_m += sorted[i];
    }

    const float mean_m = sum_m / static_cast<float>(selected_count);
    float variance_m2 = 0.0f;
    for (std::size_t i = selected_start; i < selected_end; ++i) {
        const float delta_m = sorted[i] - mean_m;
        variance_m2 += delta_m * delta_m;
    }

    *out_stddev_m = sqrtf(variance_m2 / static_cast<float>(selected_count));
    return true;
}

inline bool distance_stddev_m(const float *samples_m, std::size_t count, float *out_stddev_m) {
    if (samples_m == nullptr || out_stddev_m == nullptr || count == 0 || count > 100) {
        return false;
    }

    float sum_m = 0.0f;
    for (std::size_t i = 0; i < count; ++i) {
        if (samples_m[i] < 0.0f) {
            return false;
        }
        sum_m += samples_m[i];
    }

    const float mean_m = sum_m / static_cast<float>(count);
    float variance_m2 = 0.0f;
    for (std::size_t i = 0; i < count; ++i) {
        const float delta_m = samples_m[i] - mean_m;
        variance_m2 += delta_m * delta_m;
    }

    *out_stddev_m = sqrtf(variance_m2 / static_cast<float>(count));
    return true;
}

inline bool encode_tide_height_payload(float tide_height_m, std::uint8_t out_payload[2]) {
    if (out_payload == nullptr) {
        return false;
    }

    if (std::isnan(tide_height_m)) {
        out_payload[0] = 0x80;
        out_payload[1] = 0x00;
        return true;
    }

    const long tide_height_mm = lroundf(tide_height_m * 1000.0f);
    if (tide_height_mm < -32767L || tide_height_mm > 32767L) {
        return false;
    }

    const std::int16_t signed_mm = static_cast<std::int16_t>(tide_height_mm);
    out_payload[0] = static_cast<std::uint8_t>((signed_mm >> 8) & 0xFF);
    out_payload[1] = static_cast<std::uint8_t>(signed_mm & 0xFF);
    return true;
}

inline bool encode_temperature_payload(float temperature_c, std::uint8_t out_payload[2]) {
    if (out_payload == nullptr) {
        return false;
    }

    if (std::isnan(temperature_c)) {
        out_payload[0] = 0x80;
        out_payload[1] = 0x00;
        return true;
    }

    const long temperature_centi_c = lroundf(temperature_c * 100.0f);
    if (temperature_centi_c < -32767L || temperature_centi_c > 32767L) {
        return false;
    }

    const std::int16_t signed_centi_c = static_cast<std::int16_t>(temperature_centi_c);
    out_payload[0] = static_cast<std::uint8_t>((signed_centi_c >> 8) & 0xFF);
    out_payload[1] = static_cast<std::uint8_t>(signed_centi_c & 0xFF);
    return true;
}

inline bool encode_distance_battery_payload(
    float measured_distance_m,
    float battery_voltage_v,
    std::uint8_t out_payload[4]
) {
    if (out_payload == nullptr || battery_voltage_v < 0.0f) {
        return false;
    }

    if (std::isnan(measured_distance_m)) {
        out_payload[0] = 0xFF;
        out_payload[1] = 0xFF;
    } else {
        if (measured_distance_m < 0.0f) {
            return false;
        }
        const long distance_mm = lroundf(measured_distance_m * 1000.0f);
        if (distance_mm < 0L || distance_mm > 65534L) {
            return false;
        }
        out_payload[0] = static_cast<std::uint8_t>((distance_mm >> 8) & 0xFF);
        out_payload[1] = static_cast<std::uint8_t>(distance_mm & 0xFF);
    }

    const long battery_mv = lroundf(battery_voltage_v * 1000.0f);
    if (battery_mv < 0L || battery_mv > 65535L) {
        return false;
    }

    out_payload[2] = static_cast<std::uint8_t>((battery_mv >> 8) & 0xFF);
    out_payload[3] = static_cast<std::uint8_t>(battery_mv & 0xFF);
    return true;
}

inline bool encode_tide_distance_battery_payload(
    float tide_height_m,
    float measured_distance_m,
    float battery_voltage_v,
    float distance_stddev_m,
    float temperature_c,
    std::uint8_t out_payload[10]
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
    std::uint8_t temperature_payload[2] = {0, 0};
    if (!encode_temperature_payload(temperature_c, temperature_payload)) {
        return false;
    }

    if (std::isnan(distance_stddev_m)) {
        out_payload[6] = 0xFF;
        out_payload[7] = 0xFF;
    } else {
        if (distance_stddev_m < 0.0f) {
            return false;
        }
        const long stddev_mm = lroundf(distance_stddev_m * 1000.0f);
        if (stddev_mm < 0L || stddev_mm > 65534L) {
            return false;
        }
        out_payload[6] = static_cast<std::uint8_t>((stddev_mm >> 8) & 0xFF);
        out_payload[7] = static_cast<std::uint8_t>(stddev_mm & 0xFF);
    }

    out_payload[0] = tide_payload[0];
    out_payload[1] = tide_payload[1];
    out_payload[2] = distance_battery_payload[0];
    out_payload[3] = distance_battery_payload[1];
    out_payload[4] = distance_battery_payload[2];
    out_payload[5] = distance_battery_payload[3];
    out_payload[8] = temperature_payload[0];
    out_payload[9] = temperature_payload[1];
    return true;
}

}  // namespace tidegauge

#endif
