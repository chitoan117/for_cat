#pragma once
#include "continuous_dispense.h"
namespace user_settings {
// Fill ONLY from the actual continuous-rotation mechanism's measurements.
// Zero/false values intentionally leave this complete project unable to ARM.
inline forcat_continuous::Settings settings(){
    forcat_continuous::Settings s;
    s.pulses.safe_min_us=0; s.pulses.safe_max_us=0;
    s.pulses.neutral_us=0; s.pulses.neutral_low_us=0; s.pulses.neutral_high_us=0;
    s.pulses.open_rotation_us=0; s.pulses.close_rotation_us=0;
    s.pulses.continuous_type_verified=false;
    s.pulses.neutral_verified=false; s.pulses.directions_verified=false;
    s.opening_ms=0; s.closing_ms=0; s.travel_timing_verified=false;
    s.neutral_hold_ms=100; s.settle_ms=1000; s.stable_span_ms=200;
    s.baseline_timeout_ms=5000; s.settle_timeout_ms=6000;
    s.no_progress_ms=3000; s.total_timeout_ms=20000; s.stable_range_g=1;
    s.closing_lead_g=10; // 35 - 10 = 25 g trial trigger, final acceptance 30..40 g
    s.supervised_early_close_trial=true;
    s.detach_after_neutral=false;
    // STOP/lease loss always requests neutral. Other mass faults can optionally
    // use one bounded close rotation, only after separately reviewing this choice.
    s.supervised_bounded_fault_close=false;
    return s;
}
// NVS is read first. No historical/approximate calibration is supplied here.
// Optional exact RAM backup import: full precision and provenance are mandatory.
constexpr bool exact_calibration_import_reviewed=false;
constexpr double tare_counts=0, grams_per_count=0;
constexpr const char* calibration_provenance="UNSET";
// Review actual ECHO level shifting and module range before enabling acquisition.
constexpr bool hc_sr04_wiring_reviewed=false;
constexpr float hc_min_cm=2, hc_max_cm=400;
}
