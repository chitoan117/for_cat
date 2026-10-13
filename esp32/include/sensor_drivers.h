#pragma once

// Portable contracts and deterministic substitutes. Real pins are unassigned;
// unvalidated physical interfaces never return a healthy sample.
#include <cstdint>
#include <cstring>
#include "safety_logic.h"

namespace drivers {
template <typename T>
struct Sample {
  safety::Health health = safety::Health::NOT_VALIDATED;
  T value{};
  uint32_t sampled_at_ms = 0;
};

template <typename T>
class Sensor {
 public:
  virtual ~Sensor() = default;
  virtual Sample<T> poll(uint32_t now_ms) = 0;  // bounded, no pulseIn or delay
};

template <typename T>
class UnvalidatedSensor final : public Sensor<T> {
 public:
  Sample<T> poll(uint32_t now_ms) override {
    return {safety::Health::NOT_VALIDATED, T{}, now_ms};
  }
};

template <typename T>
class SimSensor final : public Sensor<T> {
 public:
  void set(T value, safety::Health health = safety::Health::OK) {
    value_ = value; health_ = health;
  }
  Sample<T> poll(uint32_t now_ms) override { return {health_, value_, now_ms}; }
 private:
  T value_{};
  safety::Health health_ = safety::Health::NOT_VALIDATED;
};

template <typename T>
class FreshnessCheckedSensor final : public Sensor<T> {
 public:
  FreshnessCheckedSensor(Sensor<T>& source, uint32_t max_age_ms)
      : source_(source), max_age_ms_(max_age_ms) {}
  Sample<T> poll(uint32_t now_ms) override {
    Sample<T> result = source_.poll(now_ms);
    if (result.health == safety::Health::OK &&
        static_cast<uint32_t>(now_ms - result.sampled_at_ms) > max_age_ms_)
      result.health = safety::Health::FAULT;
    return result;
  }
 private:
  Sensor<T>& source_;
  uint32_t max_age_ms_;
};

using Hx711Grams = Sensor<float>;
using FoodUltrasonicPercent = Sensor<float>;
using WaterUltrasonicPercent = Sensor<float>;
using Ds3231EpochSeconds = Sensor<uint64_t>;

// Debounced button input; true once per stable press (requires explicit release).
class ButtonDebouncer {
 public:
  explicit ButtonDebouncer(uint32_t stable_ms = 40) : stable_ms_(stable_ms) {}
  bool update(bool pressed, uint32_t now_ms) {
    if (pressed != candidate_) { candidate_ = pressed; changed_at_ = now_ms; }
    if (pressed != stable_ && static_cast<uint32_t>(now_ms - changed_at_) >= stable_ms_) {
      stable_ = pressed;
      return pressed;
    }
    return false;
  }
 private:
  uint32_t stable_ms_, changed_at_ = 0;
  bool candidate_ = false, stable_ = false;
};

class StatusDisplay {
 public:
  virtual ~StatusDisplay() = default;
  virtual safety::Health health() const = 0;
  virtual void show(const char*) = 0;
};
class Buzzer {
 public:
  virtual ~Buzzer() = default;
  virtual safety::Health health() const = 0;
  virtual void alert() = 0;
};

class SimDisplay final : public StatusDisplay {
 public:
  safety::Health health() const override { return safety::Health::OK; }
  void show(const char* text) override {
    if (!text) { message_[0] = '\0'; return; }
    std::strncpy(message_, text, sizeof(message_) - 1);
    message_[sizeof(message_) - 1] = '\0';
  }
  const char* message() const { return message_; }
 private:
  char message_[32] = {};
};
class SimBuzzer final : public Buzzer {
 public:
  safety::Health health() const override { return safety::Health::OK; }
  void alert() override { if (alerts_ < UINT32_MAX) ++alerts_; }
  uint32_t alerts() const { return alerts_; }
 private:
  uint32_t alerts_ = 0;
};
class Servo {
 public:
  virtual ~Servo() = default;
  virtual safety::Health health() const = 0;
  virtual bool isClosed() const = 0;
  virtual void requestOpen(bool open) = 0;
};
class Pump {
 public:
  virtual ~Pump() = default;
  virtual safety::Health health() const = 0;
  virtual void requestOn(bool on) = 0;
};

class InertServo final : public Servo {
 public:
  safety::Health health() const override { return safety::Health::NOT_VALIDATED; }
  bool isClosed() const override { return true; }
  void requestOpen(bool) override {}  // no pins, always off
};
class InertPump final : public Pump {
 public:
  safety::Health health() const override { return safety::Health::NOT_VALIDATED; }
  void requestOn(bool) override {}  // no pins, always off
};
class SimServo final : public Servo {
 public:
  safety::Health health() const override { return health_; }
  bool isClosed() const override { return !open_; }
  void requestOpen(bool open) override { open_ = health_ == safety::Health::OK && open; }
  void setHealth(safety::Health health) { health_ = health; if (health != safety::Health::OK) open_ = false; }
 private:
  safety::Health health_ = safety::Health::NOT_VALIDATED;
  bool open_ = false;
};
class SimPump final : public Pump {
 public:
  safety::Health health() const override { return health_; }
  bool isOn() const { return on_; }
  void requestOn(bool on) override { on_ = health_ == safety::Health::OK && on; }
  void setHealth(safety::Health health) { health_ = health; if (health != safety::Health::OK) on_ = false; }
 private:
  safety::Health health_ = safety::Health::NOT_VALIDATED;
  bool on_ = false;
};
}  // namespace drivers
