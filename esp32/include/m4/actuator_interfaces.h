#pragma once
#include "board_config.h"
#include "io.h"

#ifndef SERVO_DIAGNOSTIC_ENABLED
#define SERVO_DIAGNOSTIC_ENABLED 0
#endif
#ifndef PUMP_DIAGNOSTIC_ENABLED
#define PUMP_DIAGNOSTIC_ENABLED 0
#endif
#if SERVO_DIAGNOSTIC_ENABLED != 0 || PUMP_DIAGNOSTIC_ENABLED != 0
#error "M4 pre-hardware preparation contains no active servo/pump diagnostic binary"
#endif

namespace m4 {
inline bool futureOutputPermission(bool actuator_enabled, bool component_diagnostic_enabled,
                                   bool gpio_verified, bool valid_output_gpio) {
  return actuator_enabled && component_diagnostic_enabled && gpio_verified && valid_output_gpio;
}
class ServoInterface {
 public:
  virtual ~ServoInterface() = default;
  virtual bool initialize(Pin pin) = 0;
  virtual bool requestClosed(uint32_t now_ms) = 0;
  virtual bool requestDispense(uint32_t now_ms) = 0;
  virtual void safeStop() = 0;
  virtual Status health() const = 0;
};
class DisabledServo final : public ServoInterface {
 public:
  bool initialize(Pin) override { return false; } // no angles, pulse widths or PWM implementation
  bool requestClosed(uint32_t) override { return false; }
  bool requestDispense(uint32_t) override { return false; }
  void safeStop() override {}
  Status health() const override { return {Health::NOT_CONFIGURED, Reason::ACTUATORS_DISABLED}; }
  bool physicalOutput() const { return false; }
};
enum class PumpState : uint8_t { OFF, ON, FAULT };
class PumpInterface {
 public:
  virtual ~PumpInterface() = default;
  virtual bool initialize(Pin pin) = 0;
  virtual bool requestOn(uint32_t now_ms, uint32_t maximum_ms) = 0;
  virtual void off() = 0;
  virtual Status health() const = 0;
};
class DisabledPump final : public PumpInterface {
 public:
  bool initialize(Pin) override { state = PumpState::OFF; return false; }
  bool requestOn(uint32_t, uint32_t) override { state = PumpState::FAULT; return false; }
  void off() override { state = PumpState::OFF; }
  Status health() const override { return {Health::NOT_CONFIGURED, Reason::ACTUATORS_DISABLED}; }
  bool physicalOutput() const { return false; }
  PumpState state = PumpState::OFF;
};
static_assert(ACTUATOR_OUTPUTS_ENABLED == 0 && SERVO_DIAGNOSTIC_ENABLED == 0 && PUMP_DIAGNOSTIC_ENABLED == 0,
              "No physical actuator output is present in this preparation");
}  // namespace m4
