#pragma once

// Single isolated supervised actuator test. No dependency on feed controller,
// AI, serial v1, pump or stored calibration. Does not assert mechanical closure.
#include <cstdint>

namespace m4 {
namespace servo_bench {
constexpr int pin = 6;
constexpr uint16_t electrical_min_us = 1000, electrical_max_us = 2000;
constexpr uint16_t maximum_test_span_us = 100; // INITIAL horn-detached small-motion envelope
constexpr uint8_t maximum_arms_per_boot = 3;
constexpr uint32_t arm_timeout_ms = 2000, move_hold_ms = 250;
constexpr uint32_t close_hold_ms = 350, hard_deadline_ms = 3000;

struct Positions {
  uint16_t safe_min_us = 0, safe_max_us = 0, close_us = 0, open_us = 0;
  bool valid() const {
    return safe_min_us >= electrical_min_us && safe_max_us <= electrical_max_us &&
           safe_min_us < safe_max_us && safe_max_us - safe_min_us <= maximum_test_span_us &&
           close_us >= safe_min_us && close_us <= safe_max_us &&
           open_us >= safe_min_us && open_us <= safe_max_us && open_us != close_us;
  }
};

class Output {
 public:
  virtual ~Output() = default;
  virtual bool start(uint16_t pulse_us) = 0;
  virtual bool write(uint16_t pulse_us) = 0;
  virtual bool off() = 0; // failure must be surfaced; OFF is not a closure sensor
};

enum class State { DISARMED, ARMED, MOVING, CLOSING, FAULT };
enum class Result {
  ACCEPTED, REJECTED_CONFIG, REJECTED_ARM, REJECTED_BUSY,
  REJECTED_LIMIT, REJECTED_POSITION, REJECTED_FAULT, OUTPUT_FAULT
};
inline const char* name(State s) {
  switch (s) {
    case State::DISARMED: return "DISARMED";
    case State::ARMED: return "ARMED";
    case State::MOVING: return "MOVING";
    case State::CLOSING: return "CLOSING";
    default: return "FAULT";
  }
}
inline const char* name(Result r) {
  switch (r) {
    case Result::ACCEPTED: return "ACCEPTED";
    case Result::REJECTED_CONFIG: return "REJECTED_CONFIG";
    case Result::REJECTED_ARM: return "REJECTED_NOT_ARMED";
    case Result::REJECTED_BUSY: return "REJECTED_BUSY";
    case Result::REJECTED_LIMIT: return "REJECTED_LIMIT";
    case Result::REJECTED_POSITION: return "REJECTED_POSITION";
    case Result::REJECTED_FAULT: return "REJECTED_FAULT";
    default: return "OUTPUT_FAULT";
  }
}

class Controller {
 public:
  explicit Controller(Output& output) : output_(output) {}
  void boot() { const bool off=output_.off(); state_ = off ? State::DISARMED : State::FAULT; positions_ = {};
                configured_ = false; arms_ = moves_ = 0; pulse_us_ = 0; }
  Result configure(Positions positions) {
    if (state_ != State::DISARMED || configured_ || arms_ != 0) return Result::REJECTED_BUSY;
    if (!positions.valid()) return Result::REJECTED_CONFIG;
    positions_ = positions; configured_ = true; return Result::ACCEPTED;
  }
  Result arm(uint32_t now) {
    if (state_ == State::FAULT) return Result::REJECTED_FAULT;
    if (state_ != State::DISARMED) return Result::REJECTED_BUSY;
    if (!configured_) return Result::REJECTED_CONFIG;
    if (arms_ >= maximum_arms_per_boot) return Result::REJECTED_LIMIT;
    // Attaching PWM at the candidate CLOSE pulse can itself move the horn.
    // This is NOT proof of a mechanically closed gate.
    if (!output_.start(positions_.close_us)) return fault();
    ++arms_; pulse_us_ = positions_.close_us; armed_at_ = now;
    state_ = State::ARMED; return Result::ACCEPTED;
  }
  Result move(uint16_t pulse_us, uint32_t now) {
    if (state_ == State::FAULT) return Result::REJECTED_FAULT;
    if (state_ == State::DISARMED) return Result::REJECTED_ARM;
    if (state_ != State::ARMED) return Result::REJECTED_BUSY;
    if (pulse_us < positions_.safe_min_us || pulse_us > positions_.safe_max_us ||
        pulse_us == positions_.close_us) return Result::REJECTED_POSITION;
    if (moves_ >= maximum_arms_per_boot) return Result::REJECTED_LIMIT;
    if (!output_.write(pulse_us)) return fault();
    ++moves_; pulse_us_ = pulse_us; move_at_ = now;
    state_ = State::MOVING; return Result::ACCEPTED;
  }
  Result open(uint32_t now) { return move(positions_.open_us, now); }
  Result close(uint32_t now) {
    if (state_ == State::FAULT) return Result::REJECTED_FAULT;
    if (state_ == State::DISARMED) return Result::REJECTED_ARM;
    if (state_ == State::CLOSING) return Result::REJECTED_BUSY;
    return returnToReference(now);
  }
   Result disarm(uint32_t now) {
    if (state_ == State::FAULT) { output_.off(); return Result::REJECTED_FAULT; }
    if (state_ == State::DISARMED) return Result::ACCEPTED;
    if (state_ == State::CLOSING) return Result::REJECTED_BUSY;
     return returnToReference(now);
   }
   Result emergencyStop() {
     const bool stopped=output_.off();pulse_us_=0;state_=State::FAULT;
     return stopped?Result::ACCEPTED:Result::OUTPUT_FAULT;
   } // immediate PWM-off, latched; not a mechanical CLOSE or power-cut proof
  // Called first on each loop, independent of serial input. Returns event text;
  // every automatic close/disarm/fault is recorded by the firmware.
  const char* tick(uint32_t now) {
    if (state_ == State::DISARMED || state_ == State::FAULT) return nullptr;
    if (static_cast<uint32_t>(now - armed_at_) >= hard_deadline_ms) {
      fault(); return "HARD_DEADLINE_PWM_OFF_CLOSE_UNVERIFIED";
    }
    if (state_ == State::ARMED && static_cast<uint32_t>(now - armed_at_) >= arm_timeout_ms) {
      if (returnToReference(now) != Result::ACCEPTED) return "AUTO_CLOSE_FAILED_PWM_OFF";
      return "ARM_TIMEOUT_RETURN_TO_CLOSE_REFERENCE";
    }
    if (state_ == State::MOVING && static_cast<uint32_t>(now - move_at_) >= move_hold_ms) {
      if (returnToReference(now) != Result::ACCEPTED) return "AUTO_CLOSE_FAILED_PWM_OFF";
      return "MOVE_TIMEOUT_RETURN_TO_CLOSE_REFERENCE";
    }
    if (state_ == State::CLOSING && static_cast<uint32_t>(now - closing_at_) >= close_hold_ms) {
      const bool stopped=output_.off(); pulse_us_ = 0;
      state_ = stopped ? State::DISARMED : State::FAULT;
      return stopped ? "CLOSE_HOLD_DONE_PWM_OFF_DISARMED_CLOSE_UNVERIFIED" :
                       "PWM_OFF_FAILED_FAULT_REMOVE_SERVO_POWER";
    }
    return nullptr;
  }
  State state() const { return state_; }
  bool configured() const { return configured_; }
  uint8_t arms() const { return arms_; }
  uint8_t moves() const { return moves_; }
  uint16_t pulse() const { return pulse_us_; }
  Positions positions() const { return positions_; }
 private:
  Result fault() {
    output_.off(); pulse_us_ = 0; state_ = State::FAULT;
    return Result::OUTPUT_FAULT;
  }
  Result returnToReference(uint32_t now) {
    if (!output_.write(positions_.close_us)) return fault();
    pulse_us_ = positions_.close_us; closing_at_ = now;
    state_ = State::CLOSING; return Result::ACCEPTED;
  }
  Output& output_;
  Positions positions_{};
  State state_ = State::DISARMED;
  uint32_t armed_at_ = 0, move_at_ = 0, closing_at_ = 0;
  uint16_t pulse_us_ = 0;
  uint8_t arms_ = 0, moves_ = 0;
  bool configured_ = false;
};
} // namespace servo_bench
} // namespace m4
