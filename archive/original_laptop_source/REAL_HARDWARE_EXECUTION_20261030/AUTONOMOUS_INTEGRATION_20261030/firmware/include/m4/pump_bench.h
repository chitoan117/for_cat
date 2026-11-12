#pragma once
#include <cstdint>

// Serial-only supervised pump test policy; never reads AI/DRINKING/water sensor.
// OFF is a commanded GPIO level, not a verified pump current/flow measurement.
namespace m4 { namespace pump_bench {
enum class State { DISARMED, ARMED, ON, FAULT };
enum class Result { ACCEPTED, REJECTED_DISARMED, REJECTED_BUSY, REJECTED_LIMIT,
                    REJECTED_COOLDOWN, REJECTED_DURATION, OUTPUT_FAULT };
inline const char* name(State s) {
  switch(s) { case State::DISARMED:return "DISARMED";case State::ARMED:return "ARMED";
             case State::ON:return "ON";default:return "FAULT"; }
}
inline const char* name(Result r) {
  switch(r) { case Result::ACCEPTED:return "ACCEPTED";
    case Result::REJECTED_DISARMED:return "REJECTED_DISARMED";
    case Result::REJECTED_BUSY:return "REJECTED_BUSY";
    case Result::REJECTED_LIMIT:return "REJECTED_LIMIT";
    case Result::REJECTED_COOLDOWN:return "REJECTED_COOLDOWN";
    case Result::REJECTED_DURATION:return "REJECTED_DURATION";
    default:return "OUTPUT_FAULT"; }
}
class Output {
 public:
  virtual ~Output()=default;
  virtual bool on()=0;
  virtual bool off()=0;
};
class Controller {
 public:
  explicit Controller(Output& output):output_(output){}
  void boot() { const bool safe=output_.off();state_=safe?State::DISARMED:State::FAULT;
                pulses_=0; ever_pulsed_=false;active_for_ms_=0; }
  Result arm(uint32_t now) {
    if(state_==State::FAULT || state_==State::ON) return Result::REJECTED_BUSY;
    if(state_!=State::DISARMED) return Result::REJECTED_BUSY;
    if(pulses_>=3) return Result::REJECTED_LIMIT;
    if(ever_pulsed_ && static_cast<uint32_t>(now-off_at_)<1000) return Result::REJECTED_COOLDOWN;
    state_=State::ARMED;armed_at_=now;return Result::ACCEPTED;
  }
  Result pulse(uint32_t now,uint32_t ms) {
    if(state_!=State::ARMED) return Result::REJECTED_DISARMED;
    if(ms<20 || ms>500) return Result::REJECTED_DURATION;
    if(static_cast<uint32_t>(now-armed_at_)>=2000) {
      safeOff(now);return Result::REJECTED_DISARMED;
    }
    if(!output_.on()) {safeOff(now);state_=State::FAULT;return Result::OUTPUT_FAULT;}
    ++pulses_;ever_pulsed_=true;on_at_=now;active_for_ms_=ms;
    state_=State::ON;return Result::ACCEPTED;
  }
  bool tick(uint32_t now) {
    if(state_==State::ARMED && static_cast<uint32_t>(now-armed_at_)>=2000) {
      safeOff(now);return true;
    }
    if(state_==State::ON && static_cast<uint32_t>(now-on_at_)>=active_for_ms_) {
      safeOff(now);return true;
    }
    return false;
  }
  Result stop(uint32_t now) {
    if(state_==State::FAULT) return Result::OUTPUT_FAULT;
    if(!safeOff(now)) return Result::OUTPUT_FAULT;
    return Result::ACCEPTED;
  }
  State state() const {return state_;}
  uint8_t pulses() const {return pulses_;}
  uint32_t onMs() const {return active_for_ms_;}
 private:
  bool safeOff(uint32_t now) {
    const bool okay=output_.off();state_=okay?State::DISARMED:State::FAULT;
    off_at_=now;active_for_ms_=0;return okay;
  }
  Output& output_;
  State state_=State::DISARMED;
  uint8_t pulses_=0;
  bool ever_pulsed_=false;
  uint32_t armed_at_=0,on_at_=0,off_at_=0,active_for_ms_=0;
};
} } // namespace m4::pump_bench
