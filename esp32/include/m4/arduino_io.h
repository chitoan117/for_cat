#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <Preferences.h>
#include <driver/gpio.h>
#include "io.h"
#include "calibration_record.h"

namespace m4 {
class ArduinoPins final : public PinIO {
 public:
  bool inputAllowed(int pin) const override {
    if (pin < 0 || pin > 48 || !GPIO_IS_VALID_GPIO(pin)) return false;
#if defined(CONFIG_IDF_TARGET_ESP32S3)
    // Conservative exclusions; physical header/module review is STILL required.
    if ((pin >= 26 && pin <= 37) || pin==0 || pin==3 || pin==19 || pin==20 ||
        (pin >= 39 && pin <= 46)) return false; // SPI/OPI, straps, USB/JTAG/UART0
#else
    if ((pin >= 6 && pin <= 11) || pin==0 || pin==2 || pin==5 || pin==12 || pin==15 || pin==1 || pin==3) return false;
#endif
    return true;
  }
  bool outputAllowed(int pin) const override { return inputAllowed(pin) && GPIO_IS_VALID_OUTPUT_GPIO(pin); }
  void input(int pin, Pull pull) override { pinMode(pin, pull==Pull::UP ? INPUT_PULLUP : pull==Pull::DOWN ? INPUT_PULLDOWN : INPUT); }
  void output(int pin) override { pinMode(pin, OUTPUT); }
  bool read(int pin) override { return digitalRead(pin)==HIGH; }
  void write(int pin, bool high) override { digitalWrite(pin, high ? HIGH : LOW); }
  void pauseMicros(uint32_t short_us) override { if (short_us <= 10) delayMicroseconds(short_us); }
  void enterCritical() override { portENTER_CRITICAL(&mux_); }
  void exitCritical() override { portEXIT_CRITICAL(&mux_); }
 private:
  portMUX_TYPE mux_ = portMUX_INITIALIZER_UNLOCKED;
};
class ArduinoI2C final : public I2CBus {
 public:
  explicit ArduinoI2C(PinIO& pins) : pins_(pins) {}
  bool begin(Pin sda, Pin scl, uint16_t timeout_ms) override {
    configured_ = false;
    if (!outputValid(pins_,sda) || !outputValid(pins_,scl) || sda.number==scl.number ||
        !timeout_ms || timeout_ms>100) return false; // NO Wire.begin/default pins on invalid config
    Wire.setTimeOut(timeout_ms);
    configured_=Wire.begin(sda.number,scl.number,100000); return configured_;
  }
  bool configured() const override { return configured_; }
  bool ping(uint8_t address) override {
    if (!configured_ || address<8 || address>0x77) return false;
    Wire.beginTransmission(address); return Wire.endTransmission(true)==0;
  }
  bool readRegisters(uint8_t address,uint8_t first,uint8_t* output,size_t count) override {
    if (!configured_ || !output || !count || count>32 || address<8 || address>0x77) return false;
    Wire.beginTransmission(address); Wire.write(first);
    if (Wire.endTransmission(false)!=0) return false;
    const auto received=Wire.requestFrom(address,static_cast<uint8_t>(count),static_cast<uint8_t>(true));
    if (received!=count || static_cast<size_t>(Wire.available())<count) return false;
    for (size_t i=0;i<count;++i) output[i]=static_cast<uint8_t>(Wire.read());
    return true;
  }
  bool writeRegisters(uint8_t address,uint8_t first,const uint8_t* data,size_t count) override {
    return packet(address,first,data,count);
  }
  bool packet(uint8_t address,uint8_t control,const uint8_t* data,size_t count) override {
    if (!configured_ || !data || !count || count>31 || address<8 || address>0x77) return false;
    Wire.beginTransmission(address); Wire.write(control);
    if (Wire.write(data,count)!=count) { Wire.endTransmission(true); return false; }
    return Wire.endTransmission(true)==0;
  }
 private:
  PinIO& pins_;
  bool configured_=false;
};
enum class CalibrationLoad : uint8_t { MISSING, INVALID, LOADED };
class NvsCalibration {
 public:
  CalibrationLoad load(CalibrationRecord& record) {
    record = {}; // missing/invalid factor means NOT_CALIBRATED
    Preferences prefs;
    if (!prefs.begin("m4-calibration",true)) return CalibrationLoad::MISSING;
    if (!prefs.isKey("sensors-v1")) { prefs.end(); return CalibrationLoad::MISSING; }
    uint8_t bytes[calibration_record::SIZE];
    const bool read=prefs.getBytesLength("sensors-v1")==sizeof(bytes) &&
                    prefs.getBytes("sensors-v1",bytes,sizeof(bytes))==sizeof(bytes);
    prefs.end();
    return read && calibration_record::decode(bytes,record) ? CalibrationLoad::LOADED : CalibrationLoad::INVALID;
  }
  bool save(const CalibrationRecord& record) {
    uint8_t bytes[calibration_record::SIZE];
    if (!calibration_record::encode(record,bytes)) return false;
    Preferences prefs;
    if (!prefs.begin("m4-calibration",false)) return false;
    const bool ok=prefs.putBytes("sensors-v1",bytes,sizeof(bytes))==sizeof(bytes);
    prefs.end(); return ok;
  }
};
}  // namespace m4
