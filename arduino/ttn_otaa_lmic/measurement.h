#ifndef TIDEGAUGE_MEASUREMENT_H
#define TIDEGAUGE_MEASUREMENT_H
#include "tide_math.h"

namespace tidegauge {
inline float bounded(float value, float lo, float hi) {
    return std::isfinite(value) && value >= lo && value <= hi ? value : NAN;
}

struct Measurement {
    float height = NAN, distance = NAN, battery = NAN, stddev = NAN, temperature = NAN;
    std::uint8_t valid_samples = 0, timeout_samples = 0;
    bool echo_stuck = false;

    void sanitize() {
        height = bounded(height, -32.767f, 32.767f);
        distance = bounded(distance, 0, 65.534f);
        battery = bounded(battery, 0, 65.534f);
        stddev = bounded(stddev, 0, 65.534f);
        temperature = bounded(temperature, -55, 125);
    }

    void encode(std::uint8_t bytes[10]) const {
        Measurement m = *this;
        m.sanitize();
        // Each optional field is sanitized separately, so a sensor fault cannot
        // suppress battery/status or another working sensor's reading.
        encode_tide_distance_battery_payload(m.height, m.distance,
            std::isnan(m.battery) ? 0 : m.battery, m.stddev, m.temperature, bytes);
        if (std::isnan(m.battery)) bytes[4] = bytes[5] = 0xff;
    }
};
}
#endif
