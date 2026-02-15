#ifndef TIDEGAUGE_CONFIG_H
#define TIDEGAUGE_CONFIG_H

#include <cstdint>

namespace tg_config {

// TTN OTAA credentials as uppercase/lowercase hex (no separators).
inline constexpr char DEV_EUI_HEX[] = "0000000000000000";
inline constexpr char APP_EUI_HEX[] = "0000000000000000";
inline constexpr char APP_KEY_HEX[] = "00000000000000000000000000000000";
inline constexpr std::uint8_t US915_SUBBAND = 2;

// Site calibration constants:
// tide_height_m = GEOMETRY_REFERENCE_M - measured_distance_m - DATUM_OFFSET_M
inline constexpr float GEOMETRY_REFERENCE_M = 1.500f;
inline constexpr float DATUM_OFFSET_M = 0.000f;

}  // namespace tg_config

#endif
