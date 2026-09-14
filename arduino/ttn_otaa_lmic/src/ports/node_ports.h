#ifndef TIDEGAUGE_NODE_PORTS_H
#define TIDEGAUGE_NODE_PORTS_H
#include "../../measurement.h"
namespace tidegauge {
struct ClockPort { virtual uint32_t now_ms() = 0; virtual ~ClockPort() = default; };
struct SensorPort {
    virtual void start(uint32_t now) = 0;
    virtual bool poll(uint32_t now, Measurement& result) = 0;
    virtual void reset() = 0;
    virtual ~SensorPort() = default;
};
struct RadioPort {
    virtual bool joined() = 0;
    virtual bool busy() = 0;
    virtual bool can_sample() = 0;
    virtual uint32_t progress_count() = 0;
    virtual bool intentional_wait() {return false;}
    virtual bool send(const uint8_t* bytes, size_t size, uint8_t port) = 0;
    virtual void restart_join() = 0;
    virtual ~RadioPort() = default;
};
struct WatchdogPort {
    virtual void feed() = 0;
    virtual void reboot(uint8_t reason) = 0;
    virtual ~WatchdogPort() = default;
};
}
#endif
