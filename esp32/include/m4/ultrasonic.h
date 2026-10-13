#pragma once
#include "io.h"
#include "calibration.h"

namespace m4 {
class MedianFilter {
 public:
  bool add(float value) {
    if (!std::isfinite(value)) return false;
    values_[cursor_] = value; cursor_ = (cursor_ + 1) % 5;
    if (count_ < 5) ++count_;
    return true;
  }
  void clear() { count_ = cursor_ = 0; }
  bool ready() const { return count_ > 0; }
  float median() const {
    if (!count_) return 0;
    float sorted[5];
    for (uint8_t i = 0; i < count_; ++i) sorted[i] = values_[i];
    for (uint8_t i = 1; i < count_; ++i) {
      float value = sorted[i]; int j = i-1;
      while (j >= 0 && sorted[j] > value) { sorted[j+1] = sorted[j]; --j; }
      sorted[j+1] = value;
    }
    return sorted[count_/2];
  }
 private:
  float values_[5]{};
  uint8_t count_ = 0, cursor_ = 0;
};
struct UltrasonicConfig {
  Pin trigger{}, echo{};
  float minimum_cm = 0, maximum_cm = 0; // must be explicitly supplied from module/range review
  uint32_t echo_timeout_us = 30000;
  float sound_cm_per_us = 0.0343f; // physics starting assumption; environment/range still need calibration
};
enum class EchoPhase : uint8_t { IDLE, PULSE_LOW, PULSE_HIGH, WAIT_RISE, WAIT_FALL };
class Ultrasonic {
 public:
  explicit Ultrasonic(PinIO& io) : io_(io) {}
  bool begin(UltrasonicConfig config) {
    active_ = false; phase_ = EchoPhase::IDLE; raw = filtered = {}; config_ = config;
    if (!outputValid(io_, config.trigger) || !inputValid(io_, config.echo) ||
        config.trigger.number == config.echo.number || !std::isfinite(config.minimum_cm) ||
        !std::isfinite(config.maximum_cm) || config.minimum_cm <= 0 || config.maximum_cm <= config.minimum_cm ||
        !std::isfinite(config.sound_cm_per_us) || config.sound_cm_per_us <= 0 ||
        config.echo_timeout_us < 100 || config.echo_timeout_us > 100000) {
      status = {}; return false;
    }
    io_.output(config.trigger.number); io_.write(config.trigger.number, false);
    io_.input(config.echo.number, Pull::NONE);
    active_ = true; phase_ = EchoPhase::IDLE; filter_.clear();
    status = {Health::INITIALIZING, Reason::NONE}; return true;
  }
  bool trigger(uint32_t now_us) {
    if (!active_ || phase_ != EchoPhase::IDLE) return false;
    raw.fresh = filtered.fresh = false; // retain last good value while a bounded acquisition is pending
    if (io_.read(config_.echo.number)) { fail(Reason::INVALID_DATA); return false; }
    io_.write(config_.trigger.number, false); phase_ = EchoPhase::PULSE_LOW;
    began_ = phase_at_ = now_us; return true;
  }
  void poll(uint32_t now_us, uint32_t now_ms) {
    raw.fresh = filtered.fresh = false;
    if (!active_ || phase_ == EchoPhase::IDLE) return;
    if (static_cast<uint32_t>(now_us - began_) >= config_.echo_timeout_us) { fail(Reason::TIMEOUT); return; }
    switch (phase_) {
      case EchoPhase::PULSE_LOW:
        if (static_cast<uint32_t>(now_us - phase_at_) >= 2) {
          io_.write(config_.trigger.number, true); phase_ = EchoPhase::PULSE_HIGH; phase_at_ = now_us;
        }
        break;
      case EchoPhase::PULSE_HIGH:
        if (static_cast<uint32_t>(now_us - phase_at_) >= 10) {
          io_.write(config_.trigger.number, false); phase_ = EchoPhase::WAIT_RISE;
        }
        break;
      case EchoPhase::WAIT_RISE:
        if (io_.read(config_.echo.number)) { rise_at_ = now_us; phase_ = EchoPhase::WAIT_FALL; }
        break;
      case EchoPhase::WAIT_FALL:
        if (!io_.read(config_.echo.number)) {
          const auto width = static_cast<uint32_t>(now_us - rise_at_);
          // timeout <=100000us bounds width below 2^24: exact integer→float conversion.
          const float distance = static_cast<float>(width) * config_.sound_cm_per_us / 2;
          phase_ = EchoPhase::IDLE;
          if (!width || !std::isfinite(distance) || distance < config_.minimum_cm || distance > config_.maximum_cm) {
            fail(Reason::RANGE_INVALID); return;
          }
          raw = {true, distance, now_ms, true}; filter_.add(distance);
          filtered = {true, filter_.median(), now_ms, true}; status = {Health::HEALTHY, Reason::NONE};
        }
        break;
      default: break;
    }
  }
  const UltrasonicConfig& config() const { return config_; }
  bool busy() const { return phase_ != EchoPhase::IDLE; }
  Status status{};
  Reading<float> raw{}, filtered{};
 private:
  void fail(Reason reason) {
    if (active_) io_.write(config_.trigger.number, false);
    raw = filtered = {}; filter_.clear(); phase_ = EchoPhase::IDLE;
    status = {reason == Reason::TIMEOUT ? Health::NOT_CONNECTED : Health::FAULT, reason};
  }
  PinIO& io_;
  UltrasonicConfig config_{};
  MedianFilter filter_{};
  EchoPhase phase_ = EchoPhase::IDLE;
  uint32_t began_ = 0, phase_at_ = 0, rise_at_ = 0;
  bool active_ = false;
};

class LevelSensor {
 public:
  explicit LevelSensor(PinIO& io) : distance(io) {}
  void update() {
    percent = calibration.percent(distance.filtered, distance.config().minimum_cm, distance.config().maximum_cm);
    status = distance.status;
    if (distance.status.health == Health::HEALTHY && !calibration.valid())
      status = {Health::NOT_CALIBRATED, Reason::NOT_CALIBRATED};
    else if (distance.status.health == Health::HEALTHY && !percent.valid)
      status = {Health::FAULT, Reason::RANGE_INVALID};
  }
  Ultrasonic distance;
  LevelCalibration calibration{};
  Reading<float> percent{};
  Status status{};
};
}  // namespace m4
