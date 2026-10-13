#pragma once
#include <cmath>
#include <cstdint>
#include "health.h"

namespace m4 {
inline bool rawValid(double raw) { return std::isfinite(raw) && raw >= -8388608 && raw <= 8388607; }
class RawAverage {
 public:
  bool begin(uint8_t count) {
    if (!count || count > 64) return false;
    needed_ = count; count_ = 0; sum_ = 0; return true;
  }
  bool add(int32_t raw) {
    if (!rawValid(raw) || !needed_ || count_ >= needed_) return false;
    sum_ += raw; ++count_; return true;
  }
  bool ready() const { return needed_ && count_ == needed_; }
  double mean() const { return ready() ? static_cast<double>(sum_) / count_ : 0; }
  uint8_t count() const { return count_; }
 private:
  uint8_t needed_ = 0, count_ = 0;
  int64_t sum_ = 0;
};

struct ScaleCalibration {
  bool tared = false, calibrated = false;
  double tare_counts = 0, grams_per_count = 0;
  bool tare(double empty_average) {
    if (!rawValid(empty_average)) return false;
    tared = true; calibrated = false; tare_counts = empty_average; grams_per_count = 0; return true;
  }
  bool reference(double loaded_average, double known_grams) {
    if (!tared || !rawValid(loaded_average) || !std::isfinite(known_grams) || known_grams <= 0 ||
        loaded_average == tare_counts) return false;
    const double factor = known_grams / (loaded_average - tare_counts);
    if (!std::isfinite(factor) || factor == 0) return false;
    grams_per_count = factor; calibrated = true; return true;
  }
  bool valid() const {
    return calibrated && tared && rawValid(tare_counts) && std::isfinite(grams_per_count) && grams_per_count != 0;
  }
  Reading<float> grams(double raw, uint32_t now) const {
    Reading<float> result;
    if (!valid() || !rawValid(raw)) return result;
    const double value = (raw - tare_counts) * grams_per_count;
    if (!std::isfinite(value) || value < 0 || value > 100000) return result;
    result = {true, static_cast<float>(value), now, true};
    return result;
  }
};
struct CalibrationError {
  bool valid = false;
  double absolute_grams = 0, relative_percent = 0;
};
inline CalibrationError compareMass(double measured, double reference) {
  if (!std::isfinite(measured) || !std::isfinite(reference) || measured < 0 || reference <= 0) return {};
  const double error = std::fabs(measured - reference);
  return {true, error, 100 * error / reference}; // no invented PASS tolerance
}

struct LevelCalibration {
  bool calibrated = false;
  float full_cm = 0, empty_cm = 0;
  bool valid() const { return calibrated && std::isfinite(full_cm) && std::isfinite(empty_cm) &&
                             full_cm > 0 && empty_cm > full_cm; }
  bool set(float full, float empty) {
    LevelCalibration next{true, full, empty};
    if (!next.valid()) return false;
    *this = next; return true;
  }
  Reading<float> percent(const Reading<float>& distance, float minimum, float maximum) const {
    if (!valid() || !distance.valid || !std::isfinite(distance.value) ||
        !std::isfinite(minimum) || !std::isfinite(maximum) || minimum <= 0 || maximum <= minimum ||
        distance.value < minimum || distance.value > maximum) return {};
    float value = 100 * (empty_cm - distance.value) / (empty_cm - full_cm);
    if (value < 0) value = 0;
    if (value > 100) value = 100;
    return {true, value, distance.sampled_at_ms, distance.fresh};
  }
};
}  // namespace m4
