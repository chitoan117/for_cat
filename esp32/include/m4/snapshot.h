#pragma once
#include "rtc.h"
#include <cmath>
#include "safety_logic.h"

namespace m4 {
struct SensorSnapshot {
  uint32_t sampled_at_ms = 0;
  Status rtc{}, load_cell{}, food{}, water{};
  Reading<DateTime> rtc_time{};
  Reading<int32_t> raw_weight{};
  Reading<float> grams{}, food_distance_cm{}, food_percent{}, water_distance_cm{}, water_percent{};
  Reading<float> food_raw_distance_cm{}, water_raw_distance_cm{};
  safety::WaterState water_state = safety::WaterState::SAFE_BOOT;
  bool would_request_pump = false;
  bool physical_pump_on = false;
  bool hardware_verified = false; // never becomes true from compilation or host samples
};
template<class T> inline bool recent(const Reading<T>& reading, uint32_t now) {
  return reading.valid && static_cast<uint32_t>(now-reading.sampled_at_ms) <= 2000;
}
inline bool percentage(const Reading<float>& reading, uint32_t now) {
  return recent(reading,now) && std::isfinite(reading.value) && reading.value >= 0 && reading.value <= 100;
}
inline safety::FeedInputs feedInputs(const SensorSnapshot& snapshot, bool servo_verified_ready = false) {
  safety::FeedInputs input{};
  input.now_ms = snapshot.sampled_at_ms;
  input.rtc_valid = snapshot.rtc.health == Health::HEALTHY && recent(snapshot.rtc_time,snapshot.sampled_at_ms) && validDate(snapshot.rtc_time.value);
  if (input.rtc_valid) {
    const auto& time = snapshot.rtc_time.value;
    input.epoch_seconds = epoch(time);
    input.day = time.year * 10000 + time.month * 100 + time.day;
  }
  input.scale = snapshot.load_cell.health == Health::HEALTHY && recent(snapshot.grams,snapshot.sampled_at_ms) &&
                std::isfinite(snapshot.grams.value) && snapshot.grams.value >= 0 && snapshot.grams.value <= 100000 ? safety::Health::OK : safety::Health::FAULT;
  if (snapshot.grams.valid) input.measured_grams = snapshot.grams.value;
  input.food_available = snapshot.food.health == Health::HEALTHY && percentage(snapshot.food_percent,snapshot.sampled_at_ms) && snapshot.food_percent.value > 0;
  input.servo = servo_verified_ready ? safety::Health::OK : safety::Health::NOT_VALIDATED;
  return input; // no GPIO action, sensor/display independence explicit
}
inline safety::WaterInputs shadowWaterInputs(const SensorSnapshot& snapshot) {
  safety::WaterInputs input{};
  input.now_ms = snapshot.sampled_at_ms;
  input.sensor = snapshot.water.health == Health::HEALTHY && percentage(snapshot.water_percent,snapshot.sampled_at_ms) ? safety::Health::OK : safety::Health::FAULT;
  if (snapshot.water_percent.valid) input.level_percent = snapshot.water_percent.value;
  input.pump = safety::Health::OK; // hypothetical ready pump ONLY for would-request policy, never physical health
  return input;
}
inline void tickShadowWater(safety::WaterController& controller, const SensorSnapshot& snapshot) {
  const auto input=shadowWaterInputs(snapshot);
  // Stability/recovery counts require new samples; filling timers must still run between samples.
  if (input.sensor != safety::Health::OK || snapshot.water_percent.fresh ||
      controller.state()==safety::WaterState::FILLING) controller.tick(input);
}
}  // namespace m4
