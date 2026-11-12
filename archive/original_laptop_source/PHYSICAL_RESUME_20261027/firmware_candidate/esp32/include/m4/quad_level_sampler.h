#pragma once
#include "ultrasonic.h"

namespace m4 {
// Diagnostic-only proposal. Disabled on boot; one echo acquisition at a time.
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
  bool poll(uint32_t now_us,uint32_t now_ms) {
    const bool was_busy=busy();
    for (unsigned i=0;i<4;++i) if (enabled_[i]) {
      sensors_[i]->distance.poll(now_us,now_ms); sensors_[i]->update();
    }
    if (was_busy && !busy()) { quiet_at_=now_ms;quiet_=true; }
    return busy();
  }
  bool start(uint32_t now_us,uint32_t now_ms) {
    if (busy() || (quiet_ && static_cast<uint32_t>(now_ms-quiet_at_)<80)) return false;
    for (unsigned attempt=0;attempt<4;++attempt) {
      const auto channel=next_;next_=(next_+1)%4;
      if (!enabled_[channel] || static_cast<uint32_t>(now_ms-last_[channel])<500) continue;
      last_[channel]=now_ms;
      const bool started=sensors_[channel]->distance.trigger(now_us);
      if (!started) { quiet_at_=now_ms;quiet_=true; }
      return started;
    }
    return false;
  }
 private:
  LevelSensor* sensors_[4];
  bool enabled_[4]{},reviewed_[4]{},quiet_=false;
  unsigned next_=0;
  uint32_t last_[4]{},quiet_at_=0;
};
} // namespace m4
