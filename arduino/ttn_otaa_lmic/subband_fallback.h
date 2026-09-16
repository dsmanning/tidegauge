#ifndef TIDEGAUGE_SUBBAND_FALLBACK_H
#define TIDEGAUGE_SUBBAND_FALLBACK_H

#include <cstdint>

namespace tidegauge {

class SubbandFallback {
   public:
    explicit SubbandFallback(std::uint8_t preferred_subband)
        : preferred_subband_(normalize_subband(preferred_subband)),
          current_subband_(preferred_subband_),
          join_txcomplete_count_(0),
          alternatives_tried_(0) {}

    std::uint8_t current_subband() const { return current_subband_; }

    bool note_join_txcomplete(std::uint8_t threshold) {
        if (threshold == 0) {
            threshold = 1;
        }
        ++join_txcomplete_count_;
        return join_txcomplete_count_ >= threshold;
    }

    void note_joined() { join_txcomplete_count_ = 0; }

    void rotate_to_next() {
        join_txcomplete_count_ = 0;
        if (current_subband_ == preferred_subband_) {
            current_subband_ = (preferred_subband_ == 1) ? 2 : 1;
            alternatives_tried_ = 1;
        } else if (alternatives_tried_ >= 7) {
            current_subband_ = preferred_subband_;
            alternatives_tried_ = 0;
        } else {
            current_subband_ = next_subband(current_subband_);
            if (current_subband_ == preferred_subband_) {
                current_subband_ = next_subband(current_subband_);
            }
            ++alternatives_tried_;
        }
    }

   private:
    static std::uint8_t normalize_subband(std::uint8_t subband) {
        if (subband < 1 || subband > 8) {
            return 1;
        }
        return subband;
    }

    static std::uint8_t next_subband(std::uint8_t subband) {
        return (subband >= 8) ? 1 : static_cast<std::uint8_t>(subband + 1);
    }

    std::uint8_t preferred_subband_;
    std::uint8_t current_subband_;
    std::uint8_t join_txcomplete_count_;
    std::uint8_t alternatives_tried_;
};

}  // namespace tidegauge

#endif
