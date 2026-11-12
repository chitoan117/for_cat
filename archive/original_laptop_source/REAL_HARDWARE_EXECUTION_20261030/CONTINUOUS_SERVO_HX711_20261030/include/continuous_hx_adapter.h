#pragma once
#include <cstring>
#include "m4/hx711.h"
#include "continuous_dispense.h"
namespace forcat_continuous {
// Read-only adapter to the SAME passed control reading. Never uses display_grams,
// never tare/refit/save, and detects exact calibration-context changes locally.
class HxAdapter {
    m4::ScaleCalibration previous_{};bool have_=false,exhausted_=false;uint32_t generation_=0;
 public:
    Sample read(const m4::Hx711& hx,uint32_t now){
        const auto& cal=hx.calibration;
        const bool changed=!have_ || previous_.tared!=cal.tared || previous_.calibrated!=cal.calibrated ||
            std::memcmp(&previous_.tare_counts,&cal.tare_counts,sizeof(double)) ||
            std::memcmp(&previous_.grams_per_count,&cal.grams_per_count,sizeof(double));
        if(changed){if(generation_==UINT32_MAX)exhausted_=true;else ++generation_;previous_=cal;have_=true;}
        return {now,hx.grams.sampled_at_ms,exhausted_?0:generation_,
            hx.status.health==m4::Health::HEALTHY && hx.grams.valid,cal.valid()&&!exhausted_,hx.grams.fresh,
            hx.grams.valid?hx.grams.value:0}; // value is never qualified unless healthy=true
    }
};
} // namespace forcat_continuous
