#pragma once
#include "ultrasonic.h"

namespace m4 {
// Polling ultrasonic edges must never compete with RTC/HX711/I2C/serial work.
// One bounded acquisition at a time; independent 500ms minimum periods and an
// 80ms quiet interval after every completion/failure reduce acoustic interference.
// These scheduling constants are proposals, not physical range/calibration PASS.
class DualLevelSampler {
 public:
  enum class Channel : uint8_t { FOOD, WATER };
  DualLevelSampler(LevelSensor& food, LevelSensor& water) : food_(food), water_(water) {}
  bool enable(Channel channel, UltrasonicConfig config) {
    if (busy()) return false;
    const bool ok = selected(channel).distance.begin(config);
    (channel == Channel::FOOD ? food_enabled_ : water_enabled_) = ok;
    return ok;
  }
  bool enabled(Channel channel) const { return channel == Channel::FOOD ? food_enabled_ : water_enabled_; }
  bool busy() const { return food_.distance.busy() || water_.distance.busy(); }
  bool poll(uint32_t now_us, uint32_t now_ms) {
    const bool was_busy=busy();
    food_.distance.poll(now_us,now_ms); water_.distance.poll(now_us,now_ms);
    food_.update(); water_.update();
    if (was_busy && !busy()) { quiet_at_=now_ms; quiet_=true; }
    return busy();
  }
  bool start(uint32_t now_us, uint32_t now_ms) {
    if (busy() || (quiet_ && static_cast<uint32_t>(now_ms-quiet_at_) < 80)) return false;
    for (unsigned attempt=0; attempt<2; ++attempt) {
      const auto channel=next_;
      next_=channel == Channel::FOOD ? Channel::WATER : Channel::FOOD;
      auto& last=channel == Channel::FOOD ? last_food_ : last_water_;
      if (!enabled(channel) || static_cast<uint32_t>(now_ms-last) < 500) continue;
      last=now_ms;
      const bool started=selected(channel).distance.trigger(now_us);
      // A stuck-high echo also gets the quiet/retry budget instead of a tight loop.
      if (!started) { quiet_at_=now_ms; quiet_=true; }
      return started;
    }
    return false;
  }
 private:
  LevelSensor& selected(Channel channel) { return channel == Channel::FOOD ? food_ : water_; }
  LevelSensor &food_, &water_;
  bool food_enabled_=false, water_enabled_=false, quiet_=false;
  Channel next_=Channel::FOOD;
  uint32_t last_food_=0,last_water_=0,quiet_at_=0;
};
} // namespace m4
