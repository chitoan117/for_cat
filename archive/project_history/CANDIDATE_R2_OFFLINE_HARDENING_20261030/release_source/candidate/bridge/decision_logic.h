#pragma once
#include <cmath>
#include <cstdint>
#include <deque>
#include <string>

namespace forcat {
struct NearConfig {
    double distance_cm=0; // UNCONFIGURED. Never a fabricated final CAT_NEAR value.
    uint64_t stable_ms=1500;
    unsigned minimum_samples=3;
    uint64_t maximum_gap_ms=1500;
    bool configured()const{return std::isfinite(distance_cm)&&distance_cm>0&&distance_cm<=400&&stable_ms>=100&&minimum_samples>=2;}
};
class AutoCatGate {
    std::string target_species_;
    NearConfig config_;uint64_t began_=0,last_sample_at_=0;uint32_t previous_=0;unsigned samples_=0;
    bool have_sample_=false,emitted_=false,stable_=false;
public:
    explicit AutoCatGate(NearConfig config={},std::string target="CAT"):target_species_(std::move(target)),config_(config){}
    void reset(){samples_=0;have_sample_=emitted_=stable_=false;}
    bool update(const std::string& species,bool fresh,bool valid,double distance,uint32_t sequence,uint64_t now){
        if(!config_.configured() || species!=target_species_ || !fresh || !valid || !std::isfinite(distance) || distance<=0 || distance>config_.distance_cm){reset();return false;}
        if(have_sample_ && (now<last_sample_at_ || now-last_sample_at_>config_.maximum_gap_ms))reset();
        if(have_sample_ && sequence==previous_)return false;
        previous_=sequence;
        last_sample_at_=now;
        if(!have_sample_){began_=now;have_sample_=true;}
        if(now<began_){reset();return false;}
        if(samples_<config_.minimum_samples)++samples_;
        stable_=samples_>=config_.minimum_samples && now-began_>=config_.stable_ms;
        if(stable_ && !emitted_){emitted_=true;return true;}
        return false;
    }
    bool stable()const{return stable_;}
    // Same temporal confirmation for reviewed ROI species; no second HC gate.
    bool observeSpecies(const std::string& species,bool fresh,bool roi_valid,uint32_t sequence,uint64_t now){
        return update(species,fresh,roi_valid,config_.distance_cm,sequence,now);
    }
    bool configured()const{return config_.configured();}
};
enum class FoodBehavior {IDLE,APPROACHING,NEAR_FOOD,EATING,LEAVING};
inline const char* name(FoodBehavior state){switch(state){case FoodBehavior::APPROACHING:return "APPROACHING";case FoodBehavior::NEAR_FOOD:return "NEAR_FOOD";case FoodBehavior::EATING:return "EATING";case FoodBehavior::LEAVING:return "LEAVING";default:return "IDLE";}}
class FoodBehaviorFsm {
    FoodBehavior state_=FoodBehavior::IDLE;
    uint64_t leaving_at_=0,baseline_at_=0;
    std::deque<double> samples_;
    double baseline_=0,minimum_decrease_;
    uint64_t sustained_ms_;
    bool baseline_valid_=false;
public:
    // Weight trend parameters also remain unconfigured (0) until measured noise
    // and gram calibration exist. Synthetic tests explicitly supply their values.
    FoodBehaviorFsm(double minimum_decrease_g=0,uint64_t sustained_ms=1500):minimum_decrease_(minimum_decrease_g),sustained_ms_(sustained_ms){}
    FoodBehavior update(bool cat,bool near_stable,bool calibrated,bool weight_valid,double grams,uint64_t now){
        if(!cat){
            samples_.clear();baseline_valid_=false;
            if(state_!=FoodBehavior::IDLE && state_!=FoodBehavior::LEAVING){state_=FoodBehavior::LEAVING;leaving_at_=now;}
            else if(state_==FoodBehavior::LEAVING && now>=leaving_at_ && now-leaving_at_>=500)state_=FoodBehavior::IDLE;
            return state_;
        }
        if(!near_stable){state_=FoodBehavior::APPROACHING;samples_.clear();baseline_valid_=false;return state_;}
        if(state_!=FoodBehavior::EATING)state_=FoodBehavior::NEAR_FOOD;
        if(!calibrated || !weight_valid || !std::isfinite(grams) || minimum_decrease_<=0){
            state_=FoodBehavior::NEAR_FOOD;samples_.clear();baseline_valid_=false;return state_;
        }
        samples_.push_back(grams);if(samples_.size()>3)samples_.pop_front();
        if(samples_.size()==3){
            double filtered=0;for(double value:samples_)filtered+=value/3;
            if(!baseline_valid_){baseline_=filtered;baseline_at_=now;baseline_valid_=true;}
            else if(now>=baseline_at_ && now-baseline_at_>=sustained_ms_ && baseline_-filtered>=minimum_decrease_)state_=FoodBehavior::EATING;
        }
        return state_;
    }
    FoodBehavior state()const{return state_;}
};
struct WaterConfig {
    double low_distance_cm=0,target_distance_cm=0; // no geometry/threshold guessing
    uint64_t cooldown_ms=10000,maximum_runtime_ms=5000;
    bool configured()const{return std::isfinite(low_distance_cm)&&std::isfinite(target_distance_cm)&&target_distance_cm>0&&low_distance_cm>target_distance_cm&&low_distance_cm<=400&&maximum_runtime_ms>0;}
};
class WaterDryRun {
    WaterConfig config_;bool requested_=false,have_stop_=false;uint64_t began_=0,stopped_=0;
    std::string reason_="THRESHOLDS_UNCONFIGURED";
    void off(const std::string& reason,uint64_t now){if(requested_){have_stop_=true;stopped_=now;}requested_=false;reason_=reason;}
public:
    explicit WaterDryRun(WaterConfig config={}):config_(config){}
    bool update(bool valid,double distance,bool safety_allowed,uint64_t now){
        if(!config_.configured()){off("THRESHOLDS_UNCONFIGURED",now);return false;}
        if(!valid || !std::isfinite(distance) || distance<=0){off("INVALID_SENSOR_FAILSAFE_OFF",now);return false;}
        if(!safety_allowed){off("SAFETY_BLOCKED",now);return false;}
        if(requested_){
            if(now<began_ || now-began_>=config_.maximum_runtime_ms)off("MAX_RUNTIME_OFF",now);
            else if(distance<=config_.target_distance_cm)off("TARGET_REACHED_OFF",now);
            else reason_="LOW_DRY_RUN_REQUEST";
        }else if(distance>=config_.low_distance_cm){
            if(have_stop_ && (now<stopped_ || now-stopped_<config_.cooldown_ms))reason_="COOLDOWN";
            else {requested_=true;began_=now;reason_="LOW_DRY_RUN_REQUEST";}
        }else reason_="LEVEL_IN_BAND_OFF";
        return requested_;
    }
    bool requested()const{return requested_;}
    const std::string& reason()const{return reason_;}
    static constexpr bool actuator_execution=false;
};
} // namespace forcat
