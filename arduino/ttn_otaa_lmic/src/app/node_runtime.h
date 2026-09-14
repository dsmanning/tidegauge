#ifndef TIDEGAUGE_NODE_RUNTIME_H
#define TIDEGAUGE_NODE_RUNTIME_H
#include "../ports/node_ports.h"
namespace tidegauge {
// Unsigned elapsed times remain correct across millis() wraparound.
class NodeRuntime {
public:
    NodeRuntime(ClockPort& clock, SensorPort& sensor, RadioPort& radio,
                WatchdogPort& watchdog, uint32_t interval_ms = 60000, bool diagnostic = false)
        : clock_(clock), sensor_(sensor), radio_(radio), watchdog_(watchdog),
          interval_(interval_ms), diagnostic_(diagnostic) {}

    void tick() {
        if (halted_) return;
        const uint32_t now = clock_.now_ms();
        uptime_ms_ += static_cast<uint32_t>(now - previous_tick_);
        previous_tick_ = now;
        if (!started_) {
            started_ = true; sample_at_ = now - interval_; radio_at_ = now;
        }
        const uint32_t progress = radio_.progress_count();
        if (progress != progress_) {
            progress_ = progress; radio_at_ = now;
            if (awaiting_tx_ && radio_.joined() && !radio_.busy()) {
                awaiting_tx_ = false; radio_failures_ = 0;
            }
        }
        if (sampling_ && now - sensor_at_ > 30000) {
            sensor_.reset(); sampling_ = false; ++recoveries;
            if (++sensor_failures_ >= 2) { halt(1); return; }
        }
        const bool can_sample=diagnostic_ || radio_.can_sample();
        if (!sampling_ && now - sample_at_ >= interval_ && can_sample) {
            sample_at_ += ((now - sample_at_) / interval_) * interval_;
            sensor_at_ = now; sampling_ = true; sensor_.start(now);
        }
        if (sampling_ && can_sample && sensor_.poll(now, latest)) {
            latest.sanitize(); sampling_ = false; sensor_failures_ = 0;
            have_sample_ = true; ++measurements;
        }
        if (!diagnostic_) {
            // A bounded adapter retry delay or a fail-closed storage fault is
            // deliberate. Rebooting cannot repair either condition.
            if(radio_.intentional_wait()) radio_at_=now;
            const uint32_t deadline = radio_.joined() ? 180000 : 1800000;
            const uint32_t since = awaiting_tx_ ? now - tx_at_ : now - radio_at_;
            if (!radio_.intentional_wait() && since > deadline) {
                ++recoveries;
                if (++radio_failures_ >= 2) { halt(2); return; }
                awaiting_tx_ = false; radio_.restart_join(); radio_at_ = now;
            }
            if (have_sample_ && radio_.joined() && !radio_.busy() &&
                (!attempted_ || now-last_attempt_>=5000)) {
                attempted_=true; last_attempt_=now;
                uint8_t bytes[26]{}; latest.encode(bytes);
                const bool status = sent_ % 15 == 0;
                if (status) {
                    bytes[10]=1; // diagnostic schema
                    bytes[11]=(std::isnan(latest.height) ? 1 : 0) |
                        (std::isnan(latest.temperature) ? 2 : 0) |
                        (std::isnan(latest.battery) ? 4 : 0) | (latest.echo_stuck ? 8 : 0);
                    bytes[12]=reset_reason; bytes[13]=2; // firmware revision
                    const uint32_t seconds=uptime_ms_/1000;
                    for(unsigned i=0;i<4;++i) bytes[14+i]=seconds>>(24-8*i);
                    bytes[18]=recoveries>>8; bytes[19]=recoveries;
                    bytes[20]=latest.valid_samples; bytes[21]=latest.timeout_samples;
                    bytes[22]=watchdog_boots>>8; bytes[23]=watchdog_boots;
                    bytes[24]=measurements>>8; bytes[25]=measurements;
                }
                if (radio_.send(bytes, status ? 26 : 10, status ? 2 : 1)) {
                    ++sent_;
                    have_sample_ = false; awaiting_tx_ = true; tx_at_ = now;
                }
            }
        }
        watchdog_.feed();
    }
    Measurement latest;
    uint32_t measurements = 0;
    uint16_t recoveries = 0;
    uint16_t watchdog_boots = 0;
    uint8_t reset_reason = 0;
private:
    void halt(uint8_t reason) { halted_ = true; watchdog_.reboot(reason); }
    ClockPort& clock_; SensorPort& sensor_; RadioPort& radio_; WatchdogPort& watchdog_;
    uint32_t interval_, sample_at_=0, sensor_at_=0, radio_at_=0, tx_at_=0, progress_=0;
    bool diagnostic_, started_=false, sampling_=false, have_sample_=false, awaiting_tx_=false, halted_=false;
    uint8_t sensor_failures_=0, radio_failures_=0;
    uint32_t previous_tick_=0, sent_=0, last_attempt_=0;
    bool attempted_=false;
    uint64_t uptime_ms_=0;
};
}
#endif
