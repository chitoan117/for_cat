#pragma once
#include <cmath>
#include <cstdint>
#include "servo_bench.h"

namespace m4 { namespace cat_feed_demo {
constexpr float TARGET_G=35.0f;
constexpr uint16_t CLOSED_US=1500, OPEN_US=1000; // nominal500..2500us/180deg:90 ->45
enum class State { IDLE, BASELINE, OPEN, CLOSING, SETTLING, COMPLETE, FAULT };
enum class Reason { NONE, TARGET, DOG_OR_CAT_LOST, LINK_TIMEOUT, SCALE_INVALID,
                    CALIBRATION_CHANGED, BASELINE_UNSTABLE, NO_PROGRESS, MAX_OPEN,
                    WEIGHT_DROP, OVERSHOOT, OUTPUT_ERROR, JOURNAL_ERROR, ABORTED,
                    FINAL_UNSTABLE, FINAL_UNDER_TARGET };
inline const char* name(State s) {
  switch(s) {
    case State::IDLE:return "IDLE"; case State::BASELINE:return "BASELINE";
    case State::OPEN:return "OPEN"; case State::CLOSING:return "CLOSING";
    case State::SETTLING:return "SETTLING"; case State::COMPLETE:return "COMPLETE";
    default:return "FAULT";
  }
}
inline const char* name(Reason r) {
  switch(r) {
    case Reason::NONE:return "NONE"; case Reason::TARGET:return "TARGET_REACHED";
    case Reason::DOG_OR_CAT_LOST:return "DOG_OR_CAT_LOST"; case Reason::LINK_TIMEOUT:return "CAT_LEASE_EXPIRED";
    case Reason::SCALE_INVALID:return "SCALE_INVALID"; case Reason::CALIBRATION_CHANGED:return "CALIBRATION_CHANGED";
    case Reason::BASELINE_UNSTABLE:return "BASELINE_UNSTABLE"; case Reason::NO_PROGRESS:return "NO_PROGRESS";
    case Reason::MAX_OPEN:return "MAX_OPEN_TIME"; case Reason::WEIGHT_DROP:return "WEIGHT_DROP";
    case Reason::OVERSHOOT:return "OVERSHOOT"; case Reason::OUTPUT_ERROR:return "OUTPUT_ERROR";
    case Reason::JOURNAL_ERROR:return "JOURNAL_ERROR"; case Reason::ABORTED:return "ABORTED";
    case Reason::FINAL_UNSTABLE:return "FINAL_UNSTABLE"; default:return "FINAL_UNDER_TARGET";
  }
}
struct Sample {
  uint32_t now=0,stamp=0;
  bool valid=false,fresh=false;
  float grams=0;
  uint16_t calibration_id=0;
};
class Journal {
 public:
  virtual ~Journal()=default;
  virtual bool write(bool pending,uint32_t id)=0;
};
class Controller {
 public:
  Controller(servo_bench::Output& output,Journal& journal):out_(output),journal_(journal) {}
  void boot(bool ready,bool pending,uint32_t last) {
    initialized_=ready; pending_=pending; last_id_=last;
    attached_=baseline_valid_=false; id_=0; samples_=0; baseline_=delta_=peak_=0;
    state_=out_.off()?State::IDLE:State::FAULT;
    reason_=state_==State::FAULT?Reason::OUTPUT_ERROR:Reason::NONE;
  }
  bool initializeJournal() {
    if (active() || state_!=State::IDLE || initialized_ || pending_) return false;
    initialized_=journal_.write(false,last_id_); return initialized_;
  }
  bool start(uint32_t id,const Sample& sample) {
    if (state_!=State::IDLE || !initialized_ || pending_ || !id || id<=last_id_ || !good(sample)) return false;
    if (!journal_.write(true,id)) { state_=State::FAULT; reason_=Reason::JOURNAL_ERROR; return false; }
    id_=last_id_=id; pending_=true; calibration_id_=sample.calibration_id;
    started_=lease_=phase_at_=sample.now; last_stamp_=sample.stamp;
    baseline_valid_=false; delta_=peak_=progress_mark_=0; samples_=0;
    state_=State::BASELINE; reason_=Reason::NONE; return true;
  }
  bool catLease(uint32_t id,uint32_t now) {
    if (id!=id_ || !active()) return false;
    lease_=now; return true;
  }
  void abort(uint32_t now,Reason reason=Reason::ABORTED) {
    if (state_==State::BASELINE || state_==State::OPEN) close(now,reason);
  }
  void tick(const Sample& s) {
    if (!active()) return;
    if (state_==State::CLOSING) {
      if (static_cast<uint32_t>(s.now-phase_at_)<350) return;
      if (!out_.off()) { state_=State::FAULT; reason_=Reason::OUTPUT_ERROR; return; }
      attached_=false;
      if (reason_!=Reason::TARGET) { state_=State::FAULT; return; }
      state_=State::SETTLING; phase_at_=s.now; samples_=0; last_stamp_=s.stamp; return;
    }
    if (!good(s)) { close(s.now,Reason::SCALE_INVALID); return; }
    if (s.calibration_id!=calibration_id_) { close(s.now,Reason::CALIBRATION_CHANGED); return; }
    if (state_==State::BASELINE || state_==State::OPEN) {
      if (static_cast<uint32_t>(s.now-lease_)>=1000) { close(s.now,Reason::LINK_TIMEOUT); return; }
    }
    if (state_==State::BASELINE && static_cast<uint32_t>(s.now-phase_at_)>=6000) {
      close(s.now,Reason::BASELINE_UNSTABLE); return;
    }
    if (state_==State::OPEN && static_cast<uint32_t>(s.now-phase_at_)>=15000) {
      close(s.now,Reason::MAX_OPEN); return;
    }
    if (state_==State::SETTLING) {
      if (static_cast<uint32_t>(s.now-phase_at_)>=6000) { close(s.now,Reason::FINAL_UNSTABLE); return; }
      if (static_cast<uint32_t>(s.now-phase_at_)<500) return;
    }
    if (!s.fresh || s.stamp==last_stamp_) return;
    last_stamp_=s.stamp;
    if (state_==State::OPEN) {
      delta_=s.grams-baseline_;
      if (!std::isfinite(delta_) || delta_<-0.7f || delta_+0.7f<peak_) { close(s.now,Reason::WEIGHT_DROP); return; }
      if (delta_>40) { close(s.now,Reason::OVERSHOOT); return; }
      if (delta_>=TARGET_G) { close(s.now,Reason::TARGET); return; } // never smoothed/deadbanded
      if (delta_>peak_) peak_=delta_;
      if (delta_>=progress_mark_+0.2f) { progress_mark_=delta_; progress_at_=s.now; }
      if (static_cast<uint32_t>(s.now-progress_at_)>=3000) close(s.now,Reason::NO_PROGRESS);
      return;
    }
    window_[samples_%4]=s.grams; ++samples_;
    if (samples_<4) return;
    float low=window_[0], high=window_[0],sum=0;
    for (float v:window_) { if(v<low)low=v; if(v>high)high=v; sum+=v; }
    if (high-low>0.2f) return;
    const float mean=sum/4;
    if (state_==State::BASELINE) {
      baseline_=mean; baseline_valid_=true;
      if (!out_.start(CLOSED_US)) { close(s.now,Reason::OUTPUT_ERROR); return; }
      attached_=true;
      if (!out_.write(OPEN_US)) { close(s.now,Reason::OUTPUT_ERROR); return; }
      state_=State::OPEN; phase_at_=progress_at_=s.now; return;
    }
    delta_=mean-baseline_;
    if (delta_>40) { close(s.now,Reason::OVERSHOOT); return; }
    if (delta_<TARGET_G-0.7f) { close(s.now,Reason::FINAL_UNDER_TARGET); return; }
    if (!journal_.write(false,last_id_)) { close(s.now,Reason::JOURNAL_ERROR); return; }
    pending_=false; state_=State::COMPLETE; reason_=Reason::TARGET;
  }
  bool active() const { return state_==State::BASELINE || state_==State::OPEN || state_==State::CLOSING || state_==State::SETTLING; }
  State state() const { return state_; }
  Reason reason() const { return reason_; }
  bool initialized() const { return initialized_; }
  bool pending() const { return pending_; }
  bool baselineValid() const { return baseline_valid_; }
  float baseline() const { return baseline_; }
  float delta() const { return delta_; }
  uint32_t id() const { return id_; }
  uint32_t lastId() const { return last_id_; }
 private:
  static bool good(const Sample& s) {
    return s.valid && s.calibration_id && std::isfinite(s.grams) && std::fabs(s.grams)<=1500 &&
           static_cast<uint32_t>(s.now-s.stamp)<600;
  }
  void close(uint32_t now,Reason why) {
    reason_=why;
    if (attached_) {
      if (out_.write(CLOSED_US)) { state_=State::CLOSING; phase_at_=now; }
      else { out_.off(); attached_=false; state_=State::FAULT; reason_=Reason::OUTPUT_ERROR; }
    } else { state_=State::FAULT; }
  }
  servo_bench::Output& out_; Journal& journal_;
  State state_=State::IDLE; Reason reason_=Reason::NONE;
  bool initialized_=false,pending_=true,attached_=false,baseline_valid_=false;
  uint32_t last_id_=0,id_=0,started_=0,lease_=0,phase_at_=0,progress_at_=0,last_stamp_=0;
  unsigned samples_=0;
  uint16_t calibration_id_=0;
  float baseline_=0,delta_=0,peak_=0,progress_mark_=0,window_[4]{};
};
} }  // namespace m4::cat_feed_demo
