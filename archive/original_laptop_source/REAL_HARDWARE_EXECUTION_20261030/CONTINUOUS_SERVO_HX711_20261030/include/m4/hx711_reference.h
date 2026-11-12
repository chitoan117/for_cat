#pragma once
#include "calibration.h"

namespace m4 {
// PHYSICAL_VALIDATED_ARDUINO_HX711_REFERENCE; see HX711_REFERENCE_PORT_20261028.
// Disjoint triplets match readStableRaw(), not a long moving average.
class Hx711Median3 {
 public:
  void reset() { count_ = 0; }
  bool add(int32_t raw, int32_t& result) {
    values_[count_++] = raw;
    if (count_ != 3) return false;
    count_ = 0;
    int32_t a=values_[0], b=values_[1], c=values_[2], t;
    if (a>b) { t=a; a=b; b=t; }
    if (b>c) { t=b; b=c; c=t; }
    if (a>b) { t=a; a=b; b=t; }
    result=b; return true;
  }
 private:
  int32_t values_[3]{};
  uint8_t count_=0;
};

// Signed, unsmoothed diagnostics are separate from the nonnegative control API.
// NVS retains grams_per_count; no change to its schema or calibration authority.
inline Reading<float> hx711SignedGrams(const ScaleCalibration& calibration, double raw, uint32_t now) {
  if (!calibration.valid() || !rawValid(raw)) return {};
  const double scale_factor=1.0/calibration.grams_per_count; // counts/gram
  const double grams=(raw-calibration.tare_counts)/scale_factor;
  if (!std::isfinite(scale_factor) || scale_factor==0 || !std::isfinite(grams) || std::fabs(grams)>100000) return {};
  return {true,static_cast<float>(grams),now,true};
}

class Hx711ReferenceDisplay {
 public:
  static constexpr float ZERO_DEADBAND=0.20f;
  static constexpr float FAST_CHANGE_THRESHOLD=1.0f;
  static constexpr float STABLE_ALPHA=0.40f;
  void reset() { displayed_=0; }
  Reading<float> update(const Reading<float>& measurement) {
    if (!measurement.valid || !std::isfinite(measurement.value)) { reset(); return {}; }
    if (!measurement.fresh) return {}; // smoothing only once per new triplet
    float current=measurement.value;
    if (current>-ZERO_DEADBAND && current<ZERO_DEADBAND) current=0;
    if (current<0 && current>-0.5f) current=0; // golden reference: DISPLAY ONLY
    if (std::fabs(current-displayed_)>=FAST_CHANGE_THRESHOLD) displayed_=current;
    else displayed_=STABLE_ALPHA*current+(1.0f-STABLE_ALPHA)*displayed_;
    if (displayed_>-ZERO_DEADBAND && displayed_<ZERO_DEADBAND) displayed_=0;
    return {true,displayed_,measurement.sampled_at_ms,true};
  }
 private:
  float displayed_=0;
};
}  // namespace m4
