#pragma once
#include "ultrasonic.h"

namespace m4 {
// Owner-declared four-channel wiring. Disabled on boot; no physical PASS inferred.
// 80ms quiet + 500ms per channel are initial bench settings, not validated thresholds.
class QuadLevelSampler {
 public:
  QuadLevelSampler(LevelSensor& a, LevelSensor& b, LevelSensor& c, LevelSensor& d)
      : sensors_{&a,&b,&c,&d} {}
  bool busy() const {
    for (auto sensor:sensors_) if (sensor->distance.busy()) return true;
    return false;
  }
  bool disableAll() {
    if (busy()) return false;
    for (unsigned i=0;i<4;++i) {
      enabled_[i]=false;
      sensors_[i]->distance.raw=sensors_[i]->distance.filtered={};
      sensors_[i]->distance.status={};sensors_[i]->status={};sensors_[i]->percent={};
    }
    return true;
  }
  bool selectOnly(unsigned channel,UltrasonicConfig config) {
    if (channel>=4 || busy()) return false;
    disableAll();
    reviewed_[channel]=sensors_[channel]->distance.begin(config);
    enabled_[channel]=reviewed_[channel];
    next_=channel;
    return enabled_[channel];
  }
  bool selectAllReviewed() {
    if (busy()) return false;
    for (bool reviewed:reviewed_) if (!reviewed) return false;
    disableAll();
    for (auto& value:enabled_) value=true;
    return true;
  }
  bool enabled(unsigned channel) const { return channel<4 && enabled_[channel]; }
  bool reviewed(unsigned channel) const { return channel<4 && reviewed_[channel]; }
  uint32_t guardMs() const { return guard_ms_; }
  bool setGuardMs(uint32_t value) {
    if(busy() || (value!=60 && value!=80 && value!=100)) return false;
    guard_ms_=value;return true; // RAM only; no geometry, calibration or output permission change
  }
  bool hasUpdate(unsigned channel) const { return channel<4 && seen_[channel]; }
  uint32_t lastUpdate(unsigned channel) const { return updated_[channel]; }
  const Reading<float>& lastValid(unsigned channel) const { return history_[channel]; }
  bool poll(uint32_t now_us,uint32_t now_ms) {
    const bool was_busy=busy();
    for (unsigned i=0;i<4;++i) if (enabled_[i]) {
      const bool acquiring=sensors_[i]->distance.busy();
      sensors_[i]->distance.poll(now_us,now_ms); sensors_[i]->update();
      if(acquiring && !sensors_[i]->distance.busy()) record(i,now_ms);
    }
    if (was_busy && !busy()) { quiet_at_=now_ms;quiet_=true; }
    return busy();
  }
  bool start(uint32_t now_us,uint32_t now_ms) {
    if (busy() || (quiet_ && static_cast<uint32_t>(now_ms-quiet_at_)<guard_ms_)) return false;
    for (unsigned attempt=0;attempt<4;++attempt) {
      const auto channel=next_;next_=(next_+1)%4;
      if (!enabled_[channel] || static_cast<uint32_t>(now_ms-last_[channel])<500) continue;
      last_[channel]=now_ms;
      const bool started=sensors_[channel]->distance.trigger(now_us);
      if (!started) { record(channel,now_ms);quiet_at_=now_ms;quiet_=true; }
      return started;
    }
    return false;
  }
 private:
  void record(unsigned channel,uint32_t now_ms) {
    seen_[channel]=true;updated_[channel]=now_ms;
    if(sensors_[channel]->distance.filtered.valid && sensors_[channel]->distance.filtered.fresh)
      history_[channel]=sensors_[channel]->distance.filtered;
  }
  LevelSensor* sensors_[4];
  bool enabled_[4]{},reviewed_[4]{},quiet_=false;
  unsigned next_=0;
  uint32_t last_[4]{},quiet_at_=0;
  bool seen_[4]{};
  uint32_t updated_[4]{};
  uint32_t guard_ms_=80;
  Reading<float> history_[4]{};
};
} // namespace m4
