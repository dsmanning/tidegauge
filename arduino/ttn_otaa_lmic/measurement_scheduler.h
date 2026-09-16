#ifndef TIDEGAUGE_MEASUREMENT_SCHEDULER_H
#define TIDEGAUGE_MEASUREMENT_SCHEDULER_H

#include <cstdint>

namespace tidegauge {

class MeasurementScheduler {
   public:
    explicit MeasurementScheduler(std::uint32_t interval_s)
        : interval_s_(interval_s == 0 ? 1 : interval_s), next_due_s_(0), has_sample_(false), latest_(0) {}

    bool due(std::uint32_t now_s) const {
        return static_cast<std::int32_t>(now_s - next_due_s_) >= 0;
    }

    void mark_sampled(std::uint32_t sampled_at_s, std::uint16_t value) {
        latest_ = value;
        has_sample_ = true;
        next_due_s_ = sampled_at_s + interval_s_;
    }

    bool has_sample() const { return has_sample_; }
    std::uint32_t next_due() const { return next_due_s_; }

    bool take_latest(std::uint16_t *out_value) {
        if (!has_sample_ || out_value == nullptr) return false;
        *out_value = latest_;
        has_sample_ = false;
        return true;
    }

   private:
    std::uint32_t interval_s_;
    std::uint32_t next_due_s_;
    bool has_sample_;
    std::uint16_t latest_;
};

}  // namespace tidegauge

#endif
