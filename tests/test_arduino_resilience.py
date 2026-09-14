from test_arduino_tide_math import _compile_and_run
import subprocess
import pytest


def test_watchdog_configuration_rejects_unsupported_delays() -> None:
    assert _compile_and_run('''
        #include <iostream>
        #include "runtime_config.h"
        int main(){std::cout << TIDEGAUGE_WATCHDOG_TIMEOUT_MS;}
    ''') == '8000'
    with pytest.raises(subprocess.CalledProcessError) as error:
        _compile_and_run('''
            #define TIDEGAUGE_WATCHDOG_TIMEOUT_MS 20000
            #include "runtime_config.h"
            int main(){}
        ''')
    assert 'watchdog' in error.value.stderr.lower()


def test_join_retry_backoff_is_bounded_and_wrap_safe() -> None:
    assert _compile_and_run('''
        #include <cassert>
        #include <iostream>
        #include "src/app/join_retry.h"
        int main(){
            tidegauge::JoinRetry r;
            uint32_t t=0xfffff000;
            r.schedule(t); assert(!r.due(t+59999)); assert(r.due(t+60000));
            r.started(); assert(!r.due(t+60000));
            r.schedule(t); assert(!r.due(t+119999)); assert(r.due(t+120000));
            for(int i=0;i<20;++i)r.schedule(t);
            assert(!r.due(t+3599999)); assert(r.due(t+3600000));
            r.joined(); r.schedule(t); assert(r.due(t+60000));
            std::cout<<"ok";
        }
    ''') == 'ok'


def test_nonce_reservations_survive_restart_and_fail_closed() -> None:
    assert _compile_and_run('''
        #include <cassert>
        #include <iostream>
        #include "src/app/join_nonce.h"
        using namespace tidegauge;
        struct Store : NonceStorage {
            uint32_t high=0; bool readable=true, writable=true;
            bool load(uint32_t& value) override{value=high; return readable;}
            bool save(uint32_t value) override{if(!writable)return false; high=value; return true;}
        };
        int main(){
            Store s; uint16_t nonce;
            JoinNonce a(s); assert(a.next(nonce) && nonce==0 && s.high==32);
            assert(a.next(nonce) && nonce==1);
            JoinNonce reboot(s); assert(reboot.next(nonce) && nonce==32 && s.high==64);
            s.writable=false; JoinNonce interrupted(s); assert(!interrupted.next(nonce));
            s.writable=true; s.readable=false; JoinNonce corrupt(s); assert(!corrupt.next(nonce));
            s.readable=true; s.high=65504; JoinNonce end(s);
            for(unsigned i=65504;i<65536;++i)assert(end.next(nonce) && nonce==i);
            assert(!end.next(nonce));
            JoinNonce exhausted(s); assert(!exhausted.next(nonce));
            std::cout<<"ok";
        }
    ''') == 'ok'


def test_nonce_record_rejects_corruption_and_out_of_range_values() -> None:
    assert _compile_and_run('''
        #include <cassert>
        #include <iostream>
        #include "src/app/join_nonce.h"
        int main(){
            uint8_t bytes[12]; uint32_t value;
            tidegauge::encode_nonce_record(65536,bytes);
            assert(tidegauge::decode_nonce_record(bytes,value) && value==65536);
            for(int i=0;i<12;++i){
                bytes[i]^=1; assert(!tidegauge::decode_nonce_record(bytes,value)); bytes[i]^=1;
            }
            tidegauge::encode_nonce_record(65537,bytes);
            assert(!tidegauge::decode_nonce_record(bytes,value));
            std::cout<<"ok";
        }
    ''') == 'ok'


def test_sensor_stages_timeouts_reconnection_and_sample_quality() -> None:
    assert _compile_and_run('''
        #include <cassert>
        #include <iostream>
        #include "src/app/sensor_cycle.h"
        using namespace tidegauge;
        struct Hardware : SensorHardware {
            bool on=false, missing=true; int pulses=0, scans=0;
            unsigned long pulse=4000;
            void power(bool value) override{on=value;}
            unsigned long read_pulse() override{++pulses; return pulse;}
            bool echo_high() override{return pulse==0;}
            void rescan_temperature() override{++scans;}
            void start_temperature() override{}
            float temperature() override{return missing ? NAN : 20.0f;}
            float battery() override{return 4.0f;}
        };
        int main(){
            Hardware h; SensorSettings cfg; cfg.samples=8; cfg.minimum_valid=3;
            SensorCycle s(h,cfg); Measurement m;
            s.start(0); assert(h.on);
            assert(!s.poll(1999,m) && h.pulses==0);
            for(unsigned i=0;i<8;++i) {
                assert(!s.poll(2000+i*85,m));
                assert(!s.poll(2045+i*85,m));
            }
            assert(!h.on && h.pulses==8);
            assert(!s.poll(3000,m));
            assert(s.poll(4000,m));
            assert(m.valid_samples==8 && std::isfinite(m.height) && std::isnan(m.temperature));
            // Retry discovery after three failures; a returning sensor recovers.
            for(unsigned cycle=1;cycle<4;++cycle){
                unsigned now=cycle*60000; s.start(now);
                for(unsigned i=0;i<8;++i){s.poll(now+2000+i*85,m); s.poll(now+2045+i*85,m);}
                if(cycle==3)h.missing=false;
                assert(s.poll(now+5000,m));
            }
            assert(h.scans>=2 && m.temperature==20);
            h.pulse=0; s.start(300000);
            for(unsigned i=0;i<8;++i){s.poll(302000+i*85,m); s.poll(302045+i*85,m);}
            assert(s.poll(305000,m));
            assert(m.timeout_samples==8 && m.echo_stuck && std::isnan(m.height));
            assert(m.battery==4 && m.temperature==20);
            s.reset(); assert(!h.on);
            std::cout<<"ok";
        }
    ''') == 'ok'


def test_intersample_gap_starts_after_blocking_pulse_returns() -> None:
    assert _compile_and_run('''
        #include <cassert>
        #include <iostream>
        #include "src/app/sensor_cycle.h"
        using namespace tidegauge;
        struct H:SensorHardware {
            int pulses=0;
            void power(bool)override{} bool echo_high()override{return false;}
            unsigned long read_pulse()override{++pulses;return 0;}
            void rescan_temperature()override{} void start_temperature()override{}
            float temperature()override{return 20;} float battery()override{return 4;}
        };
        int main(){
            H h; SensorSettings cfg; cfg.settle_ms=0; SensorCycle s(h,cfg); Measurement m;
            s.start(0); s.poll(0,m); assert(h.pulses==1);
            s.poll(45,m); assert(h.pulses==1);
            s.poll(84,m); assert(h.pulses==1);
            s.poll(85,m); assert(h.pulses==2);
            std::cout<<"ok";
        }
    ''') == 'ok'


def test_bad_samples_are_rejected_and_bad_fields_do_not_silence_payload() -> None:
    assert _compile_and_run('''
        #include <cassert>
        #include <iostream>
        #include "tide_math.h"
        #include "measurement.h"
        int main() {
            float median, deviation;
            float sparse[] = {0.4f, 0.8f, 1.2f};
            assert(!tidegauge::furthest_cluster_distance_stats_m(sparse, 3, .15f, 3, &median, &deviation));
            float invalid[] = {NAN, .4f, .41f};
            assert(!tidegauge::furthest_cluster_distance_stats_m(invalid, 3, .15f, 3, &median, &deviation));
            assert(!tidegauge::apply_distance_calibration_m(INFINITY, 1, 0, &median));
            tidegauge::Measurement m;
            m.height = 100; m.distance = INFINITY; m.temperature = 150;
            m.battery = 4.0f; m.stddev = NAN;
            uint8_t bytes[10]; m.encode(bytes);
            assert(bytes[0] == 0x80 && bytes[2] == 0xff && bytes[8] == 0x80);
            assert(bytes[4] == 0x0f && bytes[5] == 0xa0);
            m.battery = NAN; m.encode(bytes);
            assert(bytes[4] == 0xff && bytes[5] == 0xff);
            std::cout << "ok";
        }
    ''') == 'ok'


def test_math_rejects_nonfinite_and_overflow_before_integer_conversion() -> None:
    assert _compile_and_run('''
        #include <cassert>
        #include <iostream>
        #include "tide_math.h"
        int main(){
            float out; uint8_t bytes[10]; float invalid[]={NAN,1,2};
            assert(!tidegauge::compute_tide_height_m(INFINITY,1,0,&out));
            assert(!tidegauge::distance_from_pulse_us(100,INFINITY,&out));
            assert(!tidegauge::battery_voltage_from_adc_raw(100,INFINITY,4095,1,&out));
            assert(!tidegauge::median_distance_m(invalid,3,&out));
            assert(!tidegauge::distance_stddev_m(invalid,3,&out));
            for(float value : {INFINITY,-INFINITY,1e30f,-1e30f}) {
                assert(!tidegauge::encode_tide_height_payload(value,bytes));
                assert(!tidegauge::encode_temperature_payload(value,bytes));
                assert(!tidegauge::encode_distance_battery_payload(value,4,bytes));
                assert(!tidegauge::encode_distance_battery_payload(1,value,bytes));
                assert(!tidegauge::encode_tide_distance_battery_payload(1,1,4,value,20,bytes));
            }
            std::cout<<"ok";
        }
    ''') == 'ok'


def test_runtime_samples_without_network_and_recovers_stalled_radio() -> None:
    assert _compile_and_run('''
        #include <cassert>
        #include <iostream>
        #include "src/app/node_runtime.h"
        using namespace tidegauge;
        struct Clock : ClockPort { uint32_t t=0; uint32_t now_ms() override {return t;} };
        struct Sensor : SensorPort {
            int starts=0, resets=0; bool ready=true;
            void start(uint32_t) override {++starts;}
            bool poll(uint32_t, Measurement& m) override {m.battery=4; return ready;}
            void reset() override {++resets;}
        };
        struct Radio : RadioPort {
            bool online=false, pending=false, accept=true; int sends=0, joins=0;
            size_t last_size=0; uint8_t last_port=0;
            uint32_t progress=0;
            bool joined() override {return online;}
            bool busy() override {return pending;}
            bool can_sample() override {return true;}
            uint32_t progress_count() override {return progress;}
            bool send(const uint8_t* bytes, size_t size, uint8_t port) override {
                ++sends; if(!accept)return false;
                pending=true; last_size=size; last_port=port;
                if(port==2){assert(size==26 && bytes[10]==1 && bytes[13]==2);}
                return true;
            }
            void restart_join() override {++joins; online=false; pending=false;}
        };
        struct Watchdog : WatchdogPort {
            int feeds=0, reboots=0;
            void feed() override {++feeds;}
            void reboot(uint8_t) override {++reboots;}
        };
        int main() {
            Clock c; Sensor s; Radio r; Watchdog w;
            NodeRuntime n(c,s,r,w);
            n.tick(); n.tick(); assert(s.starts==1 && r.sends==0);
            c.t=60000; n.tick(); n.tick(); assert(s.starts==2);
            r.online=true; ++r.progress; n.tick(); assert(r.sends==1);
            assert(r.last_port==2 && r.last_size==26);
            // A lost completion must not stop sampling or feed forever.
            c.t=240001; n.tick(); assert(r.joins==1 && w.reboots==0);
            // No join progress after the long grace period escalates once.
            c.t+=1800001; n.tick(); assert(w.reboots==1);
            Clock retry_clock; Sensor retry_sensor; Radio retry_radio; Watchdog retry_watchdog;
            retry_radio.online=true; retry_radio.accept=false;
            NodeRuntime retry(retry_clock,retry_sensor,retry_radio,retry_watchdog);
            retry.tick(); retry.tick(); retry.tick(); assert(retry_radio.sends==1);
            retry_clock.t=4999; retry.tick(); assert(retry_radio.sends==1);
            retry_clock.t=5000; retry.tick(); assert(retry_radio.sends==2);
            std::cout << "ok";
        }
    ''') == 'ok'


def test_runtime_handles_sensor_stall_wraparound_and_gateway_outage() -> None:
    # Reuse the same fake contracts while exercising a long, active join.
    assert _compile_and_run('''
        #include <cassert>
        #include <iostream>
        #include "src/app/node_runtime.h"
        using namespace tidegauge;
        struct C : ClockPort {uint32_t t=0xfffff000; uint32_t now_ms() override{return t;}};
        struct S : SensorPort {
            int starts=0,resets=0; bool ready=false;
            void start(uint32_t) override {++starts;}
            bool poll(uint32_t,Measurement&) override{return ready;}
            void reset() override{++resets;}
        };
        struct R : RadioPort {
            uint32_t p=0; int resets=0; bool waiting=false, permit=true;
            bool intentional_wait() override{return waiting;}
            bool joined() override{return false;} bool busy() override{return true;}
            bool can_sample() override{return permit;}
            uint32_t progress_count() override{return p;}
            bool send(const uint8_t*,size_t,uint8_t) override{return false;}
            void restart_join() override{++resets;}
        };
        struct W : WatchdogPort {
            int boots=0; void feed() override{} void reboot(uint8_t) override{++boots;}
        };
        int main(){
            C c; S s; R r; W w; NodeRuntime n(c,s,r,w);
            n.tick(); c.t+=30001; n.tick(); assert(s.resets==1 && w.boots==0);
            c.t+=60000; n.tick(); c.t+=30001; n.tick(); assert(w.boots==1);
            C c2; S s2; R r2; W w2; s2.ready=true; NodeRuntime n2(c2,s2,r2,w2);
            for(int i=0;i<3000;++i){++r2.p; n2.tick(); n2.tick(); c2.t+=60000;}
            assert(w2.boots==0 && r2.resets==0 && s2.starts==3000);
            r2.waiting=true;
            for(int i=0;i<1440;++i){n2.tick(); n2.tick(); c2.t+=60000;}
            assert(w2.boots==0 && r2.resets==0);
            C c3; S s3; R r3; W w3; s3.ready=true; r3.permit=false;
            NodeRuntime diagnostic(c3,s3,r3,w3,5000,true);
            diagnostic.tick(); assert(s3.starts==1);
            std::cout<<"ok";
        }
    ''') == 'ok'
