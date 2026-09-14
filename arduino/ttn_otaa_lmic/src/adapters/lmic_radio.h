#ifndef TIDEGAUGE_LMIC_RADIO_H
#define TIDEGAUGE_LMIC_RADIO_H
#include <lmic.h>
#include "../ports/node_ports.h"
#include "../app/join_nonce.h"
#include "../app/join_retry.h"
#include "../../subband_fallback.h"
namespace tidegauge {
class LmicRadio : public RadioPort {
public:
    LmicRadio(ClockPort& clock, JoinNonce& nonce, SubbandFallback& bands, bool adr, int8_t power)
        : clock_(clock), nonce_(nonce), bands_(bands), adr_(adr), power_(power) {}
    void begin() {
        if(failed_) return;
        LMIC_reset(); LMIC_selectSubBand(bands_.lmic_subband());
        LMIC_setClockError(MAX_CLOCK_ERROR / 100);
        LMIC_startJoining();
    }
    void service() {
        if(retry_requested_) {
            retry_requested_=false;
            LMIC_shutdown();
            if(rotate_) {bands_.rotate_to_next(); rotate_=false;}
            retry_.schedule(clock_.now_ms());
        }
        if(!failed_ && retry_.due(clock_.now_ms())) {retry_.started(); begin();}
    }
    void on_event(ev_t event) {
        if(event==EV_JOINING) supply_nonce();
        if(event==EV_JOIN_TXCOMPLETE) {
            ++progress_;
            supply_nonce();
            if(bands_.note_join_txcomplete(3)) {rotate_=true; retry_requested_=true;}
        }
        if(event==EV_JOIN_FAILED) {++progress_; rotate_=true; retry_requested_=true;}
        if(event==EV_JOINED) {
            ++progress_; bands_.note_joined(); retry_.joined();
            LMIC_setAdrMode(adr_ ? 1 : 0);
            // ADR owns power while enabled, including link-loss fallback.
            if(!adr_) LMIC_setDrTxpow(LMIC.datarate,power_);
            LMIC_setLinkCheckMode(1);
        }
        if(event==EV_TXCOMPLETE) ++progress_;
    }
    bool joined() override {
        return !failed_ && !retry_requested_ && !retry_.pending() && LMIC.devaddr!=0 &&
            !(LMIC.opmode & (OP_JOINING|OP_REJOIN|OP_UNJOIN));
    }
    bool busy() override {return (LMIC.opmode & (OP_TXRXPEND|OP_TXDATA))!=0;}
    bool can_sample() override {return !os_queryTimeCriticalJobs(ms2osticks(1000));}
    uint32_t progress_count() override {return progress_;}
    bool intentional_wait() override {return failed_ || retry_.pending() || retry_requested_;}
    bool storage_failed() const {return failed_;}
    bool send(const uint8_t* bytes, size_t size, uint8_t port) override {
        if(!joined() || busy() || size>255) return false;
        auto result=LMIC_setTxData2_strict(port,const_cast<uint8_t*>(bytes),static_cast<uint8_t>(size),0);
        // At low data rates a status extension may not fit. Keep the robust
        // data rate and send the compatible measurement instead.
        if(port==2 && size==26 &&
           (result==LMIC_ERROR_TX_NOT_FEASIBLE || result==LMIC_ERROR_TX_TOO_LARGE)) {
            result=LMIC_setTxData2_strict(1,const_cast<uint8_t*>(bytes),10,0);
        }
        return result==LMIC_ERROR_SUCCESS;
    }
    void restart_join() override {retry_requested_=true;}
private:
    void supply_nonce() {
        uint16_t value;
        if(!nonce_.next(value)) {
            failed_=true; LMIC_shutdown(); return;
        }
        LMIC.devNonce=value;
    }
    ClockPort& clock_; JoinNonce& nonce_; SubbandFallback& bands_; JoinRetry retry_;
    bool adr_, failed_=false, retry_requested_=false, rotate_=false;
    int8_t power_; uint32_t progress_=0;
};
}
#endif
