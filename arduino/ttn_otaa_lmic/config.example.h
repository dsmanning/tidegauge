#ifndef TIDEGAUGE_CONFIG_H
#define TIDEGAUGE_CONFIG_H

#include <cstddef>
#include <cstdint>

namespace tg_config {

// TTN OTAA credentials as uppercase/lowercase hex (no separators).
inline constexpr char DEV_EUI_HEX[] = "0000000000000000";
inline constexpr char APP_EUI_HEX[] = "0000000000000000";
inline constexpr char APP_KEY_HEX[] = "00000000000000000000000000000000";
inline constexpr std::uint8_t US915_SUBBAND = 2;
inline constexpr bool RAPID_DIAGNOSTIC_MODE = false;
inline constexpr std::uint32_t RAPID_DIAGNOSTIC_INTERVAL_S = 5;
inline constexpr std::size_t ULTRASONIC_SAMPLE_COUNT = 10;
inline constexpr std::uint32_t ULTRASONIC_INTERSAMPLE_DELAY_MS = 40;
inline constexpr std::uint32_t ULTRASONIC_TIMEOUT_US = 45000;
inline constexpr float SPEED_OF_SOUND_M_PER_US = 0.000343f;

// Site calibration constants:
// tide_height_m = GEOMETRY_REFERENCE_M - measured_distance_m - DATUM_OFFSET_M
// corrected_distance_m = measured_distance_m * DISTANCE_SCALE + DISTANCE_OFFSET_M
// Keep DISTANCE_SCALE at 1.0 and DISTANCE_OFFSET_M at 0.0 unless field-calibrated.
inline constexpr float DISTANCE_SCALE = 1.000f;
inline constexpr float DISTANCE_OFFSET_M = 0.000f;
inline constexpr float GEOMETRY_REFERENCE_M = 1.500f;
inline constexpr float DATUM_OFFSET_M = 0.000f;

}  // namespace tg_config

#endif
