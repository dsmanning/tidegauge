#ifndef TIDEGAUGE_SENSOR_CYCLE_H
#define TIDEGAUGE_SENSOR_CYCLE_H
#include "../ports/node_ports.h"
namespace tidegauge {
struct SensorHardware {
    virtual void power(bool on) = 0;
    virtual unsigned long read_pulse() = 0; // Adapter must bound this to <=45 ms.
    virtual bool echo_high() = 0;
    virtual void rescan_temperature() = 0;
    virtual void start_temperature() = 0;
    virtual float temperature() = 0;
    virtual float battery() = 0;
    virtual ~SensorHardware() = default;
};
struct SensorSettings {
    size_t samples=64, minimum_valid=16;
    uint32_t settle_ms=2000, gap_ms=40;
    float speed=.000343f, scale=1, offset=0, reference=1.5f, datum=0;
    float min_distance=.02f, max_distance=6.0f;
};
class SensorCycle : public SensorPort {
public:
    SensorCycle(SensorHardware& hardware, SensorSettings settings) : hw_(hardware), cfg_(settings) {}
    void start(uint32_t now) override {
        result_=Measurement{}; count_=0; stage_=Stage::settle; at_=now;
        hw_.power(true);
    }
    void reset() override {hw_.power(false); stage_=Stage::idle;}
    bool poll(uint32_t now, Measurement& result) override {
        if (stage_==Stage::idle) return false;
        if(stage_==Stage::gap_started) {
            at_=now; stage_=Stage::sample; return false;
        }
        if (stage_==Stage::settle) {
            if(now-at_<cfg_.settle_ms) return false;
            stage_=Stage::sample; at_=now-cfg_.gap_ms;
        }
        if(stage_==Stage::sample) {
            if(now-at_<cfg_.gap_ms) return false;
            result_.echo_stuck |= hw_.echo_high();
            float distance;
            const auto pulse=hw_.read_pulse();
            if(pulse==0) ++result_.timeout_samples;
            else if(distance_from_pulse_us(pulse,cfg_.speed,&distance) &&
                    std::isfinite(distance) && distance>=cfg_.min_distance && distance<=cfg_.max_distance &&
                    result_.valid_samples<100) samples_[result_.valid_samples++]=distance;
            at_=now;
            if(++count_<cfg_.samples) {stage_=Stage::gap_started; return false;}
            hw_.power(false);
            float raw, deviation;
            if(result_.valid_samples>=cfg_.minimum_valid &&
               furthest_cluster_distance_stats_m(samples_,result_.valid_samples,.15f,3,&raw,&deviation) &&
               apply_distance_calibration_m(raw,cfg_.scale,cfg_.offset,&result_.distance)) {
                result_.stddev=deviation*cfg_.scale;
                compute_tide_height_m(cfg_.reference,result_.distance,cfg_.datum,&result_.height);
            }
            if(!discovered_ || temperature_failures_>=3) {
                hw_.rescan_temperature(); discovered_=true; temperature_failures_=0;
            }
            hw_.start_temperature(); stage_=Stage::temperature_started;
            return false;
        }
        // Anchor after the hardware call has returned (discovery/conversion
        // commands may themselves take time). Never read a partial conversion.
        if(stage_==Stage::temperature_started) {
            at_=now; stage_=Stage::temperature; return false;
        }
        if(stage_==Stage::temperature && now-at_>=750) {
            result_.temperature=bounded(hw_.temperature(),-55,125);
            if(std::isnan(result_.temperature)) ++temperature_failures_;
            else temperature_failures_=0;
            result_.battery=hw_.battery(); result_.sanitize();
            result=result_; stage_=Stage::idle; return true;
        }
        return false;
    }
private:
    enum class Stage {idle,settle,sample,gap_started,temperature_started,temperature};
    SensorHardware& hw_; SensorSettings cfg_; Measurement result_;
    Stage stage_=Stage::idle; float samples_[100]{};
    uint32_t at_=0; size_t count_=0; uint8_t temperature_failures_=0; bool discovered_=false;
};
}
#endif
