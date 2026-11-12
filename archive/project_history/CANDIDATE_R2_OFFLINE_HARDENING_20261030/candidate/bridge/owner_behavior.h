#pragma once
// Portable candidate policy only. No model, camera, serial or actuator adapter.
#include "food_roi.h"
#include "decision_logic.h"
#include <cmath>
#include <string>
#include <vector>
namespace forcat { namespace owner_behavior {
enum class Identity {UNKNOWN,OWNER_CAT,OTHER_CAT,DOG};
struct Input {
    uint64_t now=0,captured=0;uint32_t sequence=0;
    Identity identity=Identity::UNKNOWN;
    std::string identity_source="UNVALIDATED";
    bool simulation=false,public_dataset=false,dog_present=false,distance_valid=false;
    double confidence=0,distance=0,consumed=0;
    bool consumption_valid=false;
    bool feeding_active=false;
    std::string identity_token="SYNTHETIC_OWNER_A";
    food_roi::Box box{.35,.35,.65,.65};
};
struct Decision {
    bool would_request_35g=false;
    bool cancel_active_feed=false;
    static constexpr bool actuator_execution=false;
    std::string state="IDLE",reason="NO_ELIGIBLE_OWNER";
};
class Policy {
    food_roi::Config roi_;
    AutoCatGate near_;bool seen_=false,confirmed_=false,have_feed_=false;
    uint64_t confirmed_at_=0,last_feed_=0;
    bool have_input_=false,have_distance_=false;
    uint64_t last_now_=0,last_capture_=0;
    uint32_t last_sequence_=0;
    double last_distance_=0;
    std::string identity_token_;
public:
    static NearConfig temporal(){NearConfig c;c.distance_cm=20;return c;}
    explicit Policy(const food_roi::Config& roi):roi_(roi),near_(temporal(),"OWNER_CAT"){}
    Decision update(const Input& in){
        Decision d;
        if(have_input_&&(in.now<last_now_||in.captured<last_capture_||static_cast<uint32_t>(in.sequence-last_sequence_)>0x7fffffffu)){
            near_.reset();confirmed_=seen_=have_distance_=false;d.reason="OUT_OF_ORDER_AI_OR_CLOCK";
            d.cancel_active_feed=in.feeding_active;return d;
        }
        const bool owner=in.simulation&&!in.public_dataset&&in.identity_source=="SYNTHETIC_OWNER_FIXTURE"&&
            in.identity==Identity::OWNER_CAT&&!in.identity_token.empty()&&std::isfinite(in.confidence)&&in.confidence>=.9&&in.confidence<=1;
        const bool fresh=in.now>=in.captured&&in.now-in.captured<=1500;
        const bool member=food_roi::evaluate(roi_,in.box,640,480)==food_roi::Relation::IN_ROI;
        const bool valid=owner&&fresh&&member&&!in.dog_present&&in.distance_valid&&std::isfinite(in.distance)&&in.distance>=5&&in.distance<=20;
        if(!valid){
            d.state=seen_?"LEAVING":"IDLE";
            d.reason=in.public_dataset?"PUBLIC_CAT_IS_NOT_OWNER":!fresh?"STALE_AI":in.dog_present||in.identity==Identity::DOG?"DOG_BLOCK":!member?"NO_REVIEWED_FOOD_ROI":"IDENTITY_OR_DISTANCE_NOT_QUALIFIED";
            near_.reset();seen_=confirmed_=have_distance_=false;d.cancel_active_feed=in.feeding_active;return d;
        }
        if(have_input_&&in.sequence==last_sequence_){d.state="AWAIT_FRESH_AI";d.reason="DUPLICATE_FRAME_NOT_NEW_EVIDENCE";return d;}
        have_input_=true;last_now_=in.now;last_capture_=in.captured;last_sequence_=in.sequence;
        if(identity_token_!=in.identity_token){near_.reset();confirmed_=false;identity_token_=in.identity_token;have_distance_=false;}
        if(have_distance_&&std::fabs(in.distance-last_distance_)>8){near_.reset();confirmed_=false;last_distance_=in.distance;d.state="APPROACHING";d.reason="SYNTHETIC_DISTANCE_JUMP_FILTER";d.cancel_active_feed=in.feeding_active;return d;}
        have_distance_=true;last_distance_=in.distance;
        seen_=true;const bool event=near_.update("OWNER_CAT",true,true,in.distance,in.sequence,in.now);
        if(!near_.stable()){confirmed_=false;d.state="APPROACHING";d.reason="DEBOUNCING";return d;}
        if(!confirmed_){confirmed_=true;confirmed_at_=in.now;}
        d.state=in.consumption_valid&&std::isfinite(in.consumed)&&in.consumed>=1&&in.now-confirmed_at_>=1000?"EATING":in.now-confirmed_at_>=3000?"SNIFFING":"NEAR_FOOD";
        d.reason="SIMULATED_BEHAVIOR_NOT_TRAINED_MODEL";
        if(event){
            if(have_feed_&&(in.now<last_feed_||in.now-last_feed_<7200000)){d.reason="COOLDOWN";return d;}
            d.would_request_35g=true;have_feed_=true;last_feed_=in.now;
        }
        return d;
    }
};
struct Weight {double grams;uint64_t at;uint32_t generation;bool valid;};
struct PreferenceConfig {double dislike_max=5,like_min=18,stable_range=.5;uint64_t minimum_ms=60000;};
struct Preference {bool valid=false;double consumed=0;std::string classification="UNCERTAIN",reason="INVALID_OR_INSUFFICIENT_EVIDENCE";};
inline bool stable(const std::vector<Weight>& values,uint64_t now,double range,double& mean){
    if(values.size()!=4||!std::isfinite(range)||range<=0)return false;
    double low=values[0].grams,high=low,sum=0;uint64_t previous=0;
    for(const auto& v:values){
        if(!v.valid||!std::isfinite(v.grams)||v.grams<0||v.generation!=values[0].generation||now<v.at||now-v.at>1500||v.at<=previous)return false;
        previous=v.at;low=std::min(low,v.grams);high=std::max(high,v.grams);sum+=v.grams;
    }
    mean=sum/4;return high-low<=range;
}
inline Preference preference(const std::vector<Weight>& start,const std::vector<Weight>& end,uint64_t began,uint64_t now,const PreferenceConfig& config,bool continuous_owner_observation,bool simulation){
    Preference p;double first=0,last=0;
    if(!simulation||!continuous_owner_observation||!std::isfinite(config.dislike_max)||!std::isfinite(config.like_min)||config.dislike_max<0||config.like_min<=config.dislike_max||!config.minimum_ms||now<began||now-began<config.minimum_ms||
       !stable(start,began,config.stable_range,first)||!stable(end,now,config.stable_range,last)||start[0].generation!=end[0].generation||last>first)return p;
    p.valid=true;p.consumed=first-last;
    p.classification=p.consumed>=config.like_min?"LIKE":p.consumed<=config.dislike_max?"DISLIKE":"UNCERTAIN";
    p.reason="SIMULATED_CONSUMPTION_THRESHOLDS_NOT_ANIMAL_PREFERENCE_PROOF";return p;
}
} }
