#pragma once
#include <cstdint>
#include "m4/servo_bench.h" // raw pulse Output interface only; NOT its position controller
namespace forcat_continuous {
struct PulseCalibration {
    uint16_t safe_min_us=0,safe_max_us=0,neutral_us=0,neutral_low_us=0,neutral_high_us=0;
    uint16_t open_rotation_us=0,close_rotation_us=0;
    bool continuous_type_verified=false,neutral_verified=false,directions_verified=false;
    bool valid()const{
        return continuous_type_verified && neutral_verified && directions_verified &&
          safe_min_us>=1000 && safe_max_us<=2000 && safe_min_us<safe_max_us && safe_max_us-safe_min_us<=100 &&
          neutral_low_us>=safe_min_us && neutral_high_us<=safe_max_us && neutral_low_us<=neutral_us && neutral_us<=neutral_high_us &&
          open_rotation_us>=safe_min_us && open_rotation_us<=safe_max_us && close_rotation_us>=safe_min_us && close_rotation_us<=safe_max_us &&
          ((open_rotation_us>neutral_high_us && close_rotation_us<neutral_low_us) ||
           (open_rotation_us<neutral_low_us && close_rotation_us>neutral_high_us));
    }
};
enum class Rotation {Detached,Neutral,OpenDirection,CloseDirection,Unknown};
class Driver {
    m4::servo_bench::Output& pwm_;PulseCalibration calibration_{};
    bool configured_=false,attached_=false;Rotation rotation_=Rotation::Detached;
    bool rotate(uint16_t us,Rotation direction){
        if(!configured_ || !attached_)return false;
        const bool ok=pwm_.write(us);rotation_=ok?direction:Rotation::Unknown;return ok;
    }
 public:
    explicit Driver(m4::servo_bench::Output& pwm):pwm_(pwm){}
    bool boot(){configured_=false;calibration_={};return detach();}
    bool configure(PulseCalibration calibration){if(configured_ || attached_ || !calibration.valid())return false;calibration_=calibration;configured_=true;return true;}
    bool attachNeutral(){
        if(!configured_ || attached_)return false;
        attached_=true; // failure leaves attachment UNKNOWN until successful detach
        const bool ok=pwm_.start(calibration_.neutral_us);rotation_=ok?Rotation::Neutral:Rotation::Unknown;return ok;
    }
    bool rotateOpen(){return rotate(calibration_.open_rotation_us,Rotation::OpenDirection);}
    bool rotateClose(){return rotate(calibration_.close_rotation_us,Rotation::CloseDirection);}
    bool neutral(){
        if(!attached_)return true;
        const bool ok=pwm_.write(calibration_.neutral_us);rotation_=ok?Rotation::Neutral:Rotation::Unknown;return ok;
    }
    bool detach(){const bool ok=pwm_.off();if(ok){attached_=false;rotation_=Rotation::Detached;}else rotation_=Rotation::Unknown;return ok;}
    bool attached()const{return attached_;}
    Rotation rotation()const{return rotation_;}
};
} // namespace forcat_continuous
