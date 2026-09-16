#ifndef TIDEGAUGE_RECOVERY_POLICY_H
#define TIDEGAUGE_RECOVERY_POLICY_H

#include <cstdint>

namespace tidegauge {

class RecoveryPolicy {
   public:
    RecoveryPolicy(std::uint32_t deadline_s, std::uint32_t max_backoff_s)
        : deadline_s_(deadline_s == 0 ? 1 : deadline_s),
          max_backoff_s_(max_backoff_s < deadline_s_ ? deadline_s_ : max_backoff_s) {}

    bool expired(std::uint32_t started_s, std::uint32_t now_s) const {
        return static_cast<std::uint32_t>(now_s - started_s) >= deadline_s_;
    }

    std::uint32_t backoff_seconds(std::uint8_t failure_count) const {
        std::uint32_t result = deadline_s_;
        for (std::uint8_t i = 0; i < failure_count && result < max_backoff_s_; ++i) {
            result = (result > max_backoff_s_ / 2) ? max_backoff_s_ : result * 2;
        }
        return result > max_backoff_s_ ? max_backoff_s_ : result;
    }

   private:
    std::uint32_t deadline_s_;
    std::uint32_t max_backoff_s_;
};

}  // namespace tidegauge

#endif
