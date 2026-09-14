#ifndef TIDEGAUGE_ARDUINO_SENSOR_H
#define TIDEGAUGE_ARDUINO_SENSOR_H
#include <Arduino.h>
#include <DallasTemperature.h>
#include "../app/sensor_cycle.h"
namespace tidegauge {
class ArduinoSensor : public SensorHardware {
public:
    ArduinoSensor(DallasTemperature& temperature, int trig, int echo, int power,
                  int battery, float ratio, unsigned long timeout, uint8_t resolution)
        : temperature_(temperature), trig_(trig), echo_(echo), power_(power), battery_(battery),
          ratio_(ratio), timeout_(timeout), resolution_(resolution) {}
    void power(bool on) override {if(power_>=0) digitalWrite(power_,on ? HIGH : LOW);}
    bool echo_high() override {return digitalRead(echo_)==HIGH;}
    unsigned long read_pulse() override {
        digitalWrite(trig_,LOW); delayMicroseconds(2);
        digitalWrite(trig_,HIGH); delayMicroseconds(20); digitalWrite(trig_,LOW);
        return pulseIn(echo_,HIGH,timeout_);
    }
    void rescan_temperature() override {
        temperature_.begin(); temperature_.setResolution(resolution_);
        temperature_.setWaitForConversion(false);
    }
    void start_temperature() override {temperature_.requestTemperatures();}
    float temperature() override {return temperature_.getTempCByIndex(0);}
    float battery() override {
        float value=NAN;
        battery_voltage_from_adc_raw(analogRead(battery_),3.3f,4095,ratio_,&value);
        return value;
    }
private:
    DallasTemperature& temperature_; int trig_,echo_,power_,battery_;
    float ratio_; unsigned long timeout_; uint8_t resolution_;
};
}
#endif
