import subprocess
from pathlib import Path


def test_hardware_adapter_bounds_echo_wait_and_uses_async_temperature(tmp_path):
    (tmp_path/'Arduino.h').write_text('''
#pragma once
#include <cstdint>
#include <vector>
constexpr int HIGH=1,LOW=0;
inline std::vector<int> edges,delays;
inline unsigned long observed_timeout=0;
inline void digitalWrite(int pin,int value){edges.push_back(pin*10+value);}
inline int digitalRead(int){return 1;}
inline void delayMicroseconds(int n){delays.push_back(n);}
inline unsigned long pulseIn(int pin,int value,unsigned long timeout){
 observed_timeout=timeout; return pin==5 && value==HIGH ? 0 : 999;
}
inline int analogRead(int pin){return pin==26 ? 3000 : -1;}
''')
    (tmp_path/'DallasTemperature.h').write_text('''
#pragma once
struct DallasTemperature {
 int scans=0,requests=0,resolution=0;bool wait=true;
 void begin(){++scans;} void setResolution(int n){resolution=n;}
 void setWaitForConversion(bool value){wait=value;}
 void requestTemperatures(){++requests;}
 float getTempCByIndex(int){return -127;}
};
''')
    source=tmp_path/'main.cpp'
    source.write_text('''
#include <cassert>
#include "src/adapters/arduino_sensor.h"
int main(){
 DallasTemperature t; tidegauge::ArduinoSensor h(t,6,5,10,26,1.545f,45000,10);
 h.power(true); h.power(false); assert(edges[0]==101 && edges[1]==100);
 assert(h.echo_high()); assert(h.read_pulse()==0 && observed_timeout==45000);
 assert(delays.size()==2 && delays[0]==2 && delays[1]==20);
 h.rescan_temperature(); assert(t.scans==1 && t.resolution==10 && !t.wait);
 h.start_temperature(); assert(t.requests==1 && h.temperature()==-127);
 assert(h.battery()>3.7f && h.battery()<3.8f);
}
''')
    root=Path(__file__).resolve().parents[1]/'arduino/ttn_otaa_lmic'
    binary=tmp_path/'test'
    result=subprocess.run(['g++','-std=c++17','-I',str(tmp_path),'-I',str(root),str(source),'-o',str(binary)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    subprocess.run([str(binary)],check=True,timeout=5)
