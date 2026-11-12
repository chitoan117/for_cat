#pragma once
#include <Arduino.h>
#include "board_config.h"
#include "current_hardware.h"
#include "servo_bench.h"

// THE shared GPIO6 LEDC adapter for isolated supervised servo/dispense benches.
// Normal binary firmware never includes/uses it. Off is NOT a closure sensor.
namespace m4 {
class LedcServoOutput final : public servo_bench::Output {
 public:
  bool off() override {
    bool stopped=true;
    if (attached_) {
      const bool zero=ledcWrite(servo_bench::pin,0);
      const bool detached=ledcDetach(servo_bench::pin);
      attached_=!detached;
      stopped=zero && detached;
    }
    digitalWrite(servo_bench::pin,LOW);
    pinMode(servo_bench::pin,OUTPUT);
    digitalWrite(servo_bench::pin,LOW);
    return stopped;
  }
  bool start(uint16_t pulse_us) override {
    if (attached_ || !valid(pulse_us)) return false;
    if (!ledcAttach(servo_bench::pin,50,16)) { off(); return false; }
    attached_=true;
    if (!write(pulse_us)) { off(); return false; }
    return true;
  }
  bool write(uint16_t pulse_us) override {
    if (!attached_ || !valid(pulse_us)) return false;
    const uint32_t duty=(static_cast<uint32_t>(pulse_us)*65536u+10000u)/20000u;
    return ledcWrite(servo_bench::pin,duty);
  }
  bool attached() const { return attached_; }
 private:
  static bool valid(uint16_t us) {
    return us>=servo_bench::electrical_min_us && us<=servo_bench::electrical_max_us;
  }
  bool attached_=false;
};
static_assert(current_hardware::SERVO_SIGNAL==servo_bench::pin,"GPIO6 servo contract");
} // namespace m4
