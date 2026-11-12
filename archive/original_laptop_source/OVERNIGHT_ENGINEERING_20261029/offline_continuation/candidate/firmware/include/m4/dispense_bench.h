#pragma once

// Portable, supervised ONLY. Uses the existing HX711 sample/servo LEDC interfaces;
// no CAT, UARTv1, schedule, Web, water, or production feed requests.
#include <cmath>
#include <cstdint>
#include "servo_bench.h"

namespace m4 { namespace dispense_bench {
enum class State { DISARMED, ARMED, WAIT_BASELINE, OPEN, CLOSING, SETTLE, MEASURE,
                   FAULT_CLOSING, COMPLETE, FAULT };
enum class Reason { NONE, NOT_ARMED, INVALID_CONFIG, INVALID_TARGET, INVALID_ID, DUPLICATE,
                    INSPECTION_REQUIRED, BUSY, HX711_NOT_READY, HX711_NOT_CALIBRATED,
                    BASELINE_UNSTABLE, SCALE_UNSTABLE, SERVO_FAULT, MAX_PULSES_REACHED,
                    MAX_TIME_REACHED, MAX_GRAMS_EXCEEDED, INVALID_READING, NO_PROGRESS,
                     ABORTED, PERSISTENCE_FAULT, TARGET_OVERSHOOT };
inline const char* name(State s) {
  switch(s) {
    case State::DISARMED:return "DISARMED"; case State::ARMED:return "ARMED";
    case State::WAIT_BASELINE:return "WAIT_BASELINE"; case State::OPEN:return "SERVO_PULSE_OPEN";
    case State::CLOSING:return "SERVO_CLOSE"; case State::SETTLE:return "WAIT_SCALE_SETTLE";
    case State::MEASURE:return "MEASURE"; case State::FAULT_CLOSING:return "FAULT_CLOSING";
    case State::COMPLETE:return "COMPLETE"; default:return "FAULT";
  }
}
inline const char* name(Reason r) {
  switch(r) {
    case Reason::NONE:return "NONE"; case Reason::NOT_ARMED:return "NOT_ARMED";
    case Reason::INVALID_CONFIG:return "INVALID_CONFIG"; case Reason::INVALID_TARGET:return "INVALID_TARGET";
    case Reason::INVALID_ID:return "INVALID_REQUEST_ID";
    case Reason::DUPLICATE:return "DUPLICATE"; case Reason::INSPECTION_REQUIRED:return "INSPECTION_REQUIRED";
    case Reason::BUSY:return "BUSY"; case Reason::HX711_NOT_READY:return "HX711_NOT_READY";
    case Reason::HX711_NOT_CALIBRATED:return "HX711_NOT_CALIBRATED";
    case Reason::BASELINE_UNSTABLE:return "BASELINE_UNSTABLE";
    case Reason::SCALE_UNSTABLE:return "SCALE_UNSTABLE"; case Reason::SERVO_FAULT:return "SERVO_FAULT";
    case Reason::MAX_PULSES_REACHED:return "MAX_PULSES_REACHED";
    case Reason::MAX_TIME_REACHED:return "MAX_TIME_REACHED";
    case Reason::MAX_GRAMS_EXCEEDED:return "MAX_GRAMS_EXCEEDED";
    case Reason::INVALID_READING:return "INVALID_READING"; case Reason::NO_PROGRESS:return "NO_PROGRESS";
    case Reason::ABORTED:return "ABORTED"; case Reason::TARGET_OVERSHOOT:return "TARGET_OVERSHOOT";
    default:return "PERSISTENCE_FAULT";
  }
}
enum class Event { NONE, START, BASELINE, COARSE, FINE, CLOSE, SETTLE, MEASUREMENT,
                   COMPLETE, FAULT, PWM_OFF };
inline const char* name(Event e) {
  switch(e) {
    case Event::START:return "START"; case Event::BASELINE:return "BASELINE";
    case Event::COARSE:return "COARSE"; case Event::FINE:return "FINE";
    case Event::CLOSE:return "CLOSE_COMMANDED"; case Event::SETTLE:return "SETTLING";
    case Event::MEASUREMENT:return "MEASUREMENT"; case Event::COMPLETE:return "COMPLETE";
    case Event::FAULT:return "FAULT"; case Event::PWM_OFF:return "PWM_OFF_CLOSE_UNVERIFIED";
    default:return "NONE";
  }
}

struct Settings {
  uint16_t safe_min_us=0,safe_max_us=0,close_us=0,open_us=0;
  uint16_t coarse_ms=0,fine_ms=0,settle_ms=0;
  uint8_t max_pulses=0;
  float fine_threshold_g=0,tolerance_g=0,stable_range_g=0,max_target_g=0,max_dispensed_g=0;
  bool valid() const {
    return safe_min_us>=servo_bench::electrical_min_us && safe_max_us<=servo_bench::electrical_max_us &&
      safe_min_us<safe_max_us && safe_max_us-safe_min_us<=400 &&
      close_us>=safe_min_us && close_us<=safe_max_us && open_us>=safe_min_us &&
      open_us<=safe_max_us && open_us!=close_us && fine_ms>=20 &&
      coarse_ms>=fine_ms && coarse_ms<=250 && settle_ms>=500 && settle_ms<=5000 &&
      max_pulses>=1 && max_pulses<=12 &&
      std::isfinite(fine_threshold_g) && fine_threshold_g>0 &&
      std::isfinite(tolerance_g) && tolerance_g>=0 && tolerance_g<=2 &&
      std::isfinite(stable_range_g) && stable_range_g>0 && stable_range_g<=5 &&
      std::isfinite(max_target_g) && max_target_g>0 && max_target_g<=50 &&
      fine_threshold_g<=max_target_g && tolerance_g<max_target_g &&
      std::isfinite(max_dispensed_g) && max_dispensed_g>=max_target_g && max_dispensed_g<=75;
  }
};
struct Observation {
  uint32_t now_ms=0, sample_at_ms=0;
  bool healthy=false,calibrated=false,fresh=false;
  float grams=0;
  uint16_t calibration_id=0;
};
class Journal {
 public:
  virtual ~Journal()=default;
  virtual bool write(bool pending,uint32_t last_id)=0;
};

class Controller {
 public:
  Controller(servo_bench::Output& output,Journal& journal):output_(output),journal_(journal){}
  void boot(bool initialized,bool pending,uint32_t last_id) {
    const bool off=output_.off(); state_=off?State::DISARMED:State::FAULT;
    reason_=off?Reason::NONE:Reason::SERVO_FAULT;
    configured_=false; locked_=!initialized||pending; initialized_=initialized;
    last_id_=last_id; arms_=0; pulses_=0; current_id_=0; baseline_valid_=false;
  }
  bool inspect(uint32_t now) {
    if (state_!=State::DISARMED && state_!=State::COMPLETE && state_!=State::FAULT) return false;
    if (!output_.off() || !journal_.write(false,last_id_)) { fail(Reason::PERSISTENCE_FAULT,now); return false; }
    initialized_=true; locked_=false; configured_=false;
    state_=State::DISARMED; reason_=Reason::NONE; return true;
  }
  bool configure(Settings settings) {
    if (state_!=State::DISARMED || !initialized_ || locked_ || configured_ || arms_!=0 || !settings.valid()) return false;
    settings_=settings; configured_=true; return true;
  }
  Reason arm(Observation sample) {
    if (locked_ || !initialized_) return Reason::INSPECTION_REQUIRED;
    if (state_!=State::DISARMED || arms_>=3) return Reason::BUSY;
    if (!configured_) return Reason::INVALID_CONFIG;
    const auto ok=check(sample);
    if (ok!=Reason::NONE) return ok;
    if (!output_.start(settings_.close_us)) { fail(Reason::SERVO_FAULT,sample.now_ms); return reason_; }
    servo_attached_=true;
    ++arms_; armed_at_=sample.now_ms; state_=State::ARMED; reason_=Reason::NONE;
    calibration_id_=sample.calibration_id; last_sample_at_=sample.sample_at_ms;
    return Reason::NONE;
  }
  Reason start(uint32_t id,float target,Observation sample) {
    if (!id || id>0xffffffu) return Reason::INVALID_ID;
    if (id && id<=last_id_) return Reason::DUPLICATE;
    if (state_!=State::ARMED) return Reason::NOT_ARMED;
    if (!std::isfinite(target)||target<=0||target>settings_.max_target_g||
        target<=settings_.tolerance_g) return Reason::INVALID_TARGET;
    if (static_cast<uint32_t>(sample.now_ms-armed_at_)>=5000) return Reason::NOT_ARMED;
    const auto ok=check(sample);
    if (ok!=Reason::NONE) { fail(ok,sample.now_ms); return ok; }
    if (!journal_.write(true,id)) { fail(Reason::PERSISTENCE_FAULT,sample.now_ms); return reason_; }
    locked_=true; last_id_=id; current_id_=id; target_=target;
    started_at_=wait_at_=sample.now_ms; state_=State::WAIT_BASELINE;
    resetWindow(); last_sample_at_=sample.sample_at_ms;
    return Reason::NONE;
  }
  Reason abort(uint32_t now) {
    if (state_==State::FAULT_CLOSING || state_==State::FAULT) return Reason::BUSY;
    if (active()) { fail(Reason::ABORTED,now); return Reason::ABORTED; }
    if (state_==State::ARMED) { fail(Reason::ABORTED,now); return Reason::ABORTED; }
    return Reason::NOT_ARMED;
  }
  void disarm(uint32_t now) {
    if (state_==State::FAULT_CLOSING || state_==State::FAULT) return; // cannot extend fault-close timer
    if (active() || state_==State::ARMED) fail(Reason::ABORTED,now);
    else if (state_==State::COMPLETE) state_=State::DISARMED;
  }
  Event tick(Observation sample) {
    const auto now=sample.now_ms;
    if (state_==State::DISARMED || state_==State::COMPLETE || state_==State::FAULT) return Event::NONE;
    if (state_==State::FAULT_CLOSING) return closeHold(now);
    if (state_==State::ARMED) {
      if (static_cast<uint32_t>(now-armed_at_)>=5000) { fail(Reason::ABORTED,now); return Event::FAULT; }
      return Event::NONE;
    }
    if (static_cast<uint32_t>(now-started_at_)>=60000) { fail(Reason::MAX_TIME_REACHED,now); return Event::FAULT; }
    const auto ok=check(sample);
    if (ok!=Reason::NONE) { fail(ok,now); return Event::FAULT; }
    if (sample.calibration_id!=calibration_id_) { fail(Reason::INVALID_READING,now); return Event::FAULT; }
    if (state_==State::OPEN) {
      if (static_cast<uint32_t>(now-state_at_)<pulse_ms_) return Event::NONE;
      if (!output_.write(settings_.close_us)) { fail(Reason::SERVO_FAULT,now); return Event::FAULT; }
      state_=State::CLOSING; state_at_=now; return Event::CLOSE;
    }
    if (state_==State::CLOSING) {
      if (static_cast<uint32_t>(now-state_at_)<servo_bench::close_hold_ms) return Event::NONE;
      if (!output_.off()) { fail(Reason::SERVO_FAULT,now); return Event::FAULT; }
      servo_attached_=false;
      state_=State::SETTLE; state_at_=now; wait_at_=now; resetWindow(); return Event::SETTLE;
    }
    if (state_==State::SETTLE) {
      if (static_cast<uint32_t>(now-state_at_)<settings_.settle_ms) return Event::NONE;
      state_=State::MEASURE; wait_at_=now; return Event::NONE;
    }
    if (static_cast<uint32_t>(now-wait_at_)>=10000) {
      fail(state_==State::WAIT_BASELINE?Reason::BASELINE_UNSTABLE:Reason::SCALE_UNSTABLE,now);
      return Event::FAULT;
    }
    if (pending_pulse_) return Event::NONE;
    if (!sample.fresh || sample.sample_at_ms==last_sample_at_) return Event::NONE;
    last_sample_at_=sample.sample_at_ms;
    values_[window_count_%4]=sample.grams;
    ++window_count_;
    if (window_count_<4) return Event::NONE;
    float minimum=values_[0],maximum=values_[0],total=0;
    for (float value:values_) {
      if (value<minimum) minimum=value;
      if (value>maximum) maximum=value;
      total+=value;
    }
    if (maximum-minimum>settings_.stable_range_g) return Event::NONE;
    const float stable=total/4;
    if (state_==State::WAIT_BASELINE) {
      baseline_=stable; baseline_valid_=true; measured_=stable; dispensed_=0;
      state_=State::MEASURE; // pulse selection happens on the following tick
      previous_dispensed_=0; window_count_=0;
      fine_=(target_<=settings_.fine_threshold_g);
      pulse_ms_=fine_?settings_.fine_ms:settings_.coarse_ms;
      pending_pulse_=true;
      return Event::BASELINE;
    }
    measured_=stable; dispensed_=measured_-baseline_;
    if (!std::isfinite(dispensed_) || dispensed_<-settings_.stable_range_g) {
      fail(Reason::INVALID_READING,now); return Event::FAULT;
    }
    // A real stable drop between pulses is not extra dispensing. Bowl contact,
    // removal or simultaneous eating breaks attribution; never top it up blindly.
    if (pulses_>1 && dispensed_+settings_.stable_range_g<previous_dispensed_) {
      fail(Reason::INVALID_READING,now); return Event::FAULT;
    }
    if (dispensed_>settings_.max_dispensed_g) {
      fail(Reason::MAX_GRAMS_EXCEEDED,now); return Event::FAULT;
    }
    // The global safety maximum is not the successful target tolerance band.
    if (dispensed_>target_+settings_.tolerance_g) {
      fail(Reason::TARGET_OVERSHOOT,now); return Event::FAULT;
    }
    if (pulses_>0) {
      if (dispensed_-previous_dispensed_<settings_.stable_range_g/4) ++no_progress_;
      else no_progress_=0;
      if (no_progress_>=2) { fail(Reason::NO_PROGRESS,now); return Event::FAULT; }
    }
    previous_dispensed_=dispensed_;
    if (dispensed_>=target_-settings_.tolerance_g) {
      if (!journal_.write(false,last_id_)) { fail(Reason::PERSISTENCE_FAULT,now); return Event::FAULT; }
      locked_=false; state_=State::COMPLETE; reason_=Reason::NONE;
      return Event::COMPLETE;
    }
    if (pulses_>=settings_.max_pulses) { fail(Reason::MAX_PULSES_REACHED,now); return Event::FAULT; }
    const float remaining=target_-dispensed_;
    fine_=(remaining<=settings_.fine_threshold_g);
    pulse_ms_=fine_?settings_.fine_ms:settings_.coarse_ms;
    // Stay in MEASURE until next tick, allowing log of the stable reading first.
    state_=State::MEASURE; pending_pulse_=true; return Event::MEASUREMENT;
  }
  Event launchPulse(Observation sample) {
    if (state_!=State::MEASURE || !pending_pulse_) return Event::NONE;
    pending_pulse_=false;
    if (check(sample)!=Reason::NONE || sample.calibration_id!=calibration_id_ ||
        static_cast<uint32_t>(sample.now_ms-started_at_)>=60000) {
      fail(Reason::HX711_NOT_READY,sample.now_ms); return Event::FAULT;
    }
    if ((!servo_attached_ && !output_.start(settings_.close_us)) ||
        !output_.write(settings_.open_us)) {
      fail(Reason::SERVO_FAULT,sample.now_ms); return Event::FAULT;
    }
    servo_attached_=true;
    ++pulses_; state_=State::OPEN; state_at_=sample.now_ms;
    return fine_?Event::FINE:Event::COARSE;
  }
  bool active() const { return state_==State::WAIT_BASELINE || state_==State::OPEN ||
    state_==State::CLOSING || state_==State::SETTLE || state_==State::MEASURE || state_==State::FAULT_CLOSING; }
  State state() const { return state_; }
  Reason reason() const { return reason_; }
  bool configured() const { return configured_; }
  bool locked() const { return locked_; }
  bool baselineValid() const { return baseline_valid_; }
  bool pulsePending() const { return pending_pulse_; }
  uint8_t pulses() const { return pulses_; }
  uint8_t arms() const { return arms_; }
  uint32_t id() const { return current_id_; }
  float baseline() const { return baseline_; }
  float measured() const { return measured_; }
  float dispensed() const { return dispensed_; }
  float target() const { return target_; }
  uint16_t pulseMs() const { return pulse_ms_; }
  uint32_t elapsed(uint32_t now) const { return current_id_?static_cast<uint32_t>(now-started_at_):0; }
  Settings settings() const { return settings_; }
 private:
  Reason check(const Observation& s) const {
    if (!s.calibrated || s.calibration_id==0) return Reason::HX711_NOT_CALIBRATED;
    if (!s.healthy || !std::isfinite(s.grams) || s.grams<0 || s.grams>100000 ||
        static_cast<uint32_t>(s.now_ms-s.sample_at_ms)>1500) return Reason::HX711_NOT_READY;
    return Reason::NONE;
  }
  void resetWindow() { window_count_=0; for (float& v:values_) v=0; }
  void fail(Reason reason,uint32_t now) {
    reason_=reason; locked_=true; pending_pulse_=false;
    if (servo_attached_ && output_.write(settings_.close_us)) {
      state_=State::FAULT_CLOSING; state_at_=now;
    } else {
      output_.off(); servo_attached_=false; state_=State::FAULT;
    }
  }
  Event closeHold(uint32_t now) {
    if (static_cast<uint32_t>(now-state_at_)<servo_bench::close_hold_ms) return Event::NONE;
    if (!output_.off()) reason_=Reason::SERVO_FAULT;
    servo_attached_=false;
    state_=State::FAULT; return Event::PWM_OFF;
  }
  servo_bench::Output& output_;
  Journal& journal_;
  Settings settings_{};
  State state_=State::DISARMED;
  Reason reason_=Reason::NONE;
  bool initialized_=false,locked_=true,configured_=false,baseline_valid_=false,servo_attached_=false;
  bool pending_pulse_=false,fine_=false;
  uint8_t arms_=0,pulses_=0,no_progress_=0,window_count_=0;
  uint32_t last_id_=0,current_id_=0,armed_at_=0,started_at_=0;
  uint32_t state_at_=0,wait_at_=0,last_sample_at_=0;
  uint16_t calibration_id_=0,pulse_ms_=0;
  float values_[4]{},baseline_=0,measured_=0,dispensed_=0,previous_dispensed_=0,target_=0;
};
} } // namespace m4::dispense_bench
