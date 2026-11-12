#pragma once
#include "io.h"

namespace m4 {
struct ButtonConfig {
  Pin pin{};
  Pull pull = Pull::NONE;
  bool active_low = true;
  uint32_t debounce_ms = 40, maximum_short_press_ms = 1000;
  bool event_on_press = false; // opt-in; preserve legacy short-release semantics
};
class ShortPress {
 public:
  void begin(bool pressed, uint32_t now, uint32_t debounce, uint32_t maximum) {
    stable_ = candidate_ = pressed; inhibited_ = pressed;
    changed_ = pressed_at_ = now; debounce_ = debounce; maximum_ = maximum;
  }
  bool update(bool pressed, uint32_t now) {
    if (pressed != candidate_) { candidate_ = pressed; changed_ = now; }
    if (candidate_ == stable_ || static_cast<uint32_t>(now - changed_) < debounce_) return false;
    stable_ = candidate_;
    if (stable_) { pressed_at_ = now; return false; }
    if (inhibited_) { inhibited_ = false; return false; }
    return static_cast<uint32_t>(now - pressed_at_) <= maximum_;
  }
  bool pressed() const { return stable_; }
 private:
  bool stable_ = false, candidate_ = false, inhibited_ = false;
  uint32_t changed_ = 0, pressed_at_ = 0, debounce_ = 40, maximum_ = 1000;
};
class ManualButton {
 public:
  explicit ManualButton(PinIO& io) : io_(io) {}
  bool begin(ButtonConfig config, uint32_t now) {
    active_ = false; config_ = config;
    if (!inputValid(io_, config.pin) || static_cast<uint8_t>(config.pull) > 2 || !config.debounce_ms || config.debounce_ms > 1000 ||
        config.maximum_short_press_ms < config.debounce_ms || config.maximum_short_press_ms > 10000) {
      status = {}; return false;
    }
    io_.input(config.pin.number, config.pull);
    raw_level = io_.read(config.pin.number);
    const bool pressed = config.active_low ? !raw_level : raw_level;
    debounced_level = raw_level; button_pressed = pressed;
    press_armed_ = !pressed; press_count = last_press_ms = 0;
    debounce_.begin(pressed, now, config.debounce_ms, config.maximum_short_press_ms);
    active_ = true; status = {Health::INITIALIZING, Reason::NONE}; return true;
  }
  bool poll(uint32_t now) {
    if (!active_) return false;
    raw_level = io_.read(config_.pin.number);
    status = {Health::HEALTHY, Reason::NONE};
    const bool previously_pressed = button_pressed;
    const bool short_release = debounce_.update(config_.active_low ? !raw_level : raw_level, now);
    button_pressed = debounce_.pressed();
    debounced_level = config_.active_low ? !button_pressed : button_pressed;
    if (!button_pressed) press_armed_ = true;
    if (!config_.event_on_press) return short_release;
    // A held-at-boot button must be released before it can request anything.
    if (!button_pressed || previously_pressed || !press_armed_) return false;
    press_armed_ = false;
    if (press_count != UINT32_MAX) ++press_count;
    last_press_ms = now;
    return true; // diagnostic intent only; caller must never execute actuators
  }
  Status status{};
  bool raw_level = true, debounced_level = true, button_pressed = false;
  uint32_t press_count = 0, last_press_ms = 0;
 private:
  PinIO& io_;
  ButtonConfig config_{};
  ShortPress debounce_{};
  bool active_ = false;
  bool press_armed_ = false;
};

enum class BuzzerPattern : uint8_t { CONFIRMATION, WARNING, FAULT };
class PatternState {
 public:
  void start(BuzzerPattern pattern, uint32_t now) {
    pattern_ = pattern; step_ = 0; step_at_ = now; active_ = true; on_ = true;
  }
  void stop() { active_ = on_ = false; }
  bool tick(uint32_t now) {
    if (!active_) return false;
    // One transition per tick, safe time-based progression without delay().
    const uint32_t duration = pattern_ == BuzzerPattern::CONFIRMATION ? 100 :
                              pattern_ == BuzzerPattern::WARNING ? 200 : 300;
    if (static_cast<uint32_t>(now - step_at_) >= duration) {
      ++step_; step_at_ = now;
      const uint8_t steps = pattern_ == BuzzerPattern::CONFIRMATION ? 2 : pattern_ == BuzzerPattern::WARNING ? 4 : 6;
      if (step_ >= steps) { stop(); return false; }
      on_ = step_ % 2 == 0;
    }
    return on_;
  }
  bool active() const { return active_; }
 private:
  BuzzerPattern pattern_ = BuzzerPattern::CONFIRMATION;
  uint32_t step_at_ = 0;
  uint8_t step_ = 0;
  bool active_ = false, on_ = false;
};
class Buzzer {
 public:
  explicit Buzzer(PinIO& io) : io_(io) {}
  bool begin(Pin pin, bool active_high = true) {
    ready_ = false; pin_ = pin; active_high_ = active_high;
    if (!outputValid(io_, pin)) { status = {}; return false; }
    io_.output(pin.number); io_.write(pin.number, !active_high); state.stop();
    ready_ = true; status = {Health::INITIALIZING, Reason::NONE}; return true;
  }
  bool start(BuzzerPattern pattern, uint32_t now) {
    if (!ready_) return false;
    state.start(pattern, now); return true;
  }
  void tick(uint32_t now) {
    if (!ready_) return;
    const bool on = state.tick(now);
    io_.write(pin_.number, on ? active_high_ : !active_high_);
    status = {Health::HEALTHY, Reason::NONE};
  }
  PatternState state{};
  Status status{};
 private:
  PinIO& io_; Pin pin_{};
  bool ready_ = false, active_high_ = true;
};
}  // namespace m4
