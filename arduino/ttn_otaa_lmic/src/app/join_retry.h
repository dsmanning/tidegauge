#ifndef TIDEGAUGE_JOIN_RETRY_H
#define TIDEGAUGE_JOIN_RETRY_H
#include <cstdint>
namespace tidegauge {
class JoinRetry {
public:
    void schedule(uint32_t now) {
        at_=now; delay_=next_delay_; pending_=true;
        next_delay_=next_delay_>=1800000 ? 3600000 : next_delay_*2;
    }
    bool due(uint32_t now) const {return pending_ && now-at_>=delay_;}
    bool pending() const {return pending_;}
    void started() {pending_=false;}
    void joined() {pending_=false; next_delay_=60000;}
private:
    uint32_t at_=0, delay_=0, next_delay_=60000; bool pending_=false;
};
}
#endif
