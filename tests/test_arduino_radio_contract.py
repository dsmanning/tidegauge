import subprocess
from pathlib import Path


def test_actual_radio_adapter_defers_resets_preserves_adr_and_reserves_nonces(tmp_path):
    (tmp_path / 'lmic.h').write_text('''
#pragma once
#include <cstdint>
enum ev_t {EV_JOINING,EV_JOINED,EV_JOIN_FAILED,EV_JOIN_TXCOMPLETE,EV_TXCOMPLETE,EV_LINK_DEAD};
enum {OP_TXRXPEND=1,OP_JOINING=2,OP_REJOIN=4,OP_UNJOIN=8,OP_TXDATA=16};
constexpr int MAX_CLOCK_ERROR=65536, LMIC_ERROR_SUCCESS=0, LMIC_ERROR_TX_NOT_FEASIBLE=-3, LMIC_ERROR_TX_TOO_LARGE=-2;
struct {uint32_t devaddr=0,opmode=0; uint16_t devNonce=0; int datarate=3;} LMIC;
inline int reset_count=0, selected=-1, power_calls=0, link_check=-1, sends=0;
inline bool critical=false;
inline int maximum=255,last_port=0;
inline void LMIC_reset(){++reset_count; LMIC.devaddr=0; LMIC.opmode=0;}
inline void LMIC_shutdown(){LMIC.opmode=0;}
inline void LMIC_selectSubBand(int n){selected=n;}
inline void LMIC_setClockError(int){}
inline void LMIC_startJoining(){LMIC.opmode|=OP_JOINING;}
inline void LMIC_setAdrMode(int){}
inline void LMIC_setDrTxpow(int,int){++power_calls;}
inline void LMIC_setLinkCheckMode(int n){link_check=n;}
inline int LMIC_setTxData2_strict(int port,uint8_t*,int size,int){
 ++sends; if(size>maximum)return LMIC_ERROR_TX_NOT_FEASIBLE;
 last_port=port; LMIC.opmode|=OP_TXRXPEND; return 0;
}
inline int LMIC_setTxData2(int port,uint8_t* data,int size,int confirmed){
 LMIC.datarate=7; maximum=255; return LMIC_setTxData2_strict(port,data,size,confirmed);
}
inline int ms2osticks(int n){return n;}
inline bool os_queryTimeCriticalJobs(int){return critical;}
''')
    source = tmp_path / 'main.cpp'
    source.write_text('''
#include <cassert>
#include "src/adapters/lmic_radio.h"
using namespace tidegauge;
struct C:ClockPort {uint32_t t=0;uint32_t now_ms() override{return t;}};
struct Store:NonceStorage {
 uint32_t high=0; bool ok=true;
 bool load(uint32_t& n) override{n=high;return ok;}
 bool save(uint32_t n) override{high=n;return ok;}
};
int main(){
 C c; Store s; JoinNonce nonce(s); SubbandFallback band(2);
 LmicRadio r(c,nonce,band,true,10);
 r.begin(); assert(selected==1 && reset_count==1);
 r.on_event(EV_JOINING); assert(LMIC.devNonce==0 && s.high==32);
 r.on_event(EV_JOIN_TXCOMPLETE); assert(LMIC.devNonce==1);
 r.on_event(EV_JOIN_TXCOMPLETE);
 r.on_event(EV_JOIN_TXCOMPLETE);
 assert(reset_count==1); // Never reset inside LMIC's own callback.
 r.service(); assert(r.intentional_wait());
 c.t=60000; r.service(); assert(reset_count==2 && selected==0);
 LMIC.devaddr=1; LMIC.opmode=0; r.on_event(EV_JOINED);
 assert(link_check==1 && power_calls==0);
 uint8_t bytes[10]{}; assert(r.send(bytes,10,1)); assert(power_calls==0);
 assert(!r.send(bytes,10,1));
 LMIC.opmode=0; LMIC.datarate=3; maximum=11;
 uint8_t diagnostics[26]{}; assert(r.send(diagnostics,26,2));
 assert(LMIC.datarate==3 && last_port==1); // Defer status rather than sacrificing range.
 critical=true; assert(!r.can_sample());
 Store bad; bad.ok=false; JoinNonce broken(bad); LmicRadio failed(c,broken,band,true,10);
 failed.on_event(EV_JOINING); assert(failed.storage_failed());
 assert(!failed.joined() && failed.intentional_wait());
}
''')
    root = Path(__file__).resolve().parents[1] / 'arduino/ttn_otaa_lmic'
    binary = tmp_path / 'test'
    compiled = subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-I', str(tmp_path),
                              '-I', str(root), str(source), '-o', str(binary)], capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stderr
    subprocess.run([str(binary)], check=True, timeout=5)
