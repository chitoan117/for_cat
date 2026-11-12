#pragma once
// Demo-only consumption thresholds. Not identity/behavior AI and not a physical
// preference claim. It never calls a feeder/servo or any repository itself.
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>
namespace offline_demo {
struct Weight {double grams=0;uint64_t at=0;bool valid=false;uint32_t generation=1;};
struct Preference {
 bool ready=false,valid=false;
 std::string food,classification="UNCERTAIN",reason;
 double starting=0,remaining=0,consumed=0;
 uint64_t started_at=0,finished_at=0;
};
inline bool stable(const std::vector<Weight>& samples,uint64_t now,uint32_t generation,double& value){
 if(samples.size()<4)return false;
 double low=samples.front().grams,high=low,sum=0;
 for(const auto& s:samples){
   if(!s.valid||!std::isfinite(s.grams)||s.grams<0||s.generation!=generation||now<s.at||now-s.at>1500)return false;
   if(s.grams<low)low=s.grams;if(s.grams>high)high=s.grams;sum+=s.grams;
 }
 if(high-low>0.5)return false;
 value=sum/static_cast<double>(samples.size());return true;
}
class Consumption {
 Preference result_;std::vector<Weight> last_;uint32_t generation_=0;bool active_=false;double minimum_seen_=0;
 public:
 bool begin(const std::string& food,const std::vector<Weight>& settled,uint64_t now,uint32_t generation,bool simulation_only){
   if(active_||!simulation_only||food.empty()||food.size()>64)return false;
   double first=0;if(!stable(settled,now,generation,first)||first<=0)return false;
   result_={};result_.food=food;result_.starting=first;result_.started_at=now;
   generation_=generation;last_=settled;minimum_seen_=first;active_=true;return true;
 }
 void observe(const Weight& s,uint64_t now){
   if(!active_||result_.ready)return;
   if(!s.valid||!std::isfinite(s.grams)){invalidate("SENSOR_INVALID");return;}
   if(s.grams<0){invalidate("NEGATIVE_WEIGHT");return;}
   if(s.generation!=generation_){invalidate("CALIBRATION_OR_TARE_CHANGED");return;}
   if(now<s.at||now-s.at>1500||(!last_.empty()&&s.at<=last_.back().at)){invalidate("INVALID_SAMPLE_TIMESTAMP");return;}
   if(!last_.empty()&&s.at-last_.back().at>1500)invalidate("SENSOR_DATA_GAP");
   if(s.grams>minimum_seen_+0.5)invalidate("FOOD_ADDED_OR_WEIGHT_CONTACT");
   if(s.grams<minimum_seen_)minimum_seen_=s.grams;
   last_.push_back(s);if(last_.size()>4)last_.erase(last_.begin());
 }
 void invalidate(const std::string& why){if(active_&&result_.reason.empty())result_.reason=why;}
 Preference finish(uint64_t now){
   if(!active_)return result_;
   if(now<result_.started_at){invalidate("CLOCK_REGRESSION");return result_;}
   if(now-result_.started_at<60000)return result_;
   result_.ready=true;result_.finished_at=now;active_=false;
   double remaining=0;
   if(!stable(last_,now,generation_,remaining)){if(result_.reason.empty())result_.reason="UNSTABLE_OR_STALE_WEIGHT";return result_;}
   result_.remaining=remaining;
   if(!result_.reason.empty())return result_;
   const double amount=result_.starting-remaining;
   if(!std::isfinite(amount)||amount<0||amount>result_.starting){result_.reason="WEIGHT_INCREASE_OR_INVALID_CONSUMPTION";return result_;}
   result_.valid=true;result_.consumed=amount;
   result_.classification=amount>=18?"LIKE":amount<=5?"DISLIKE":"UNCERTAIN";
   result_.reason="SIMULATED_CONSUMPTION_THRESHOLDS_NOT_BEHAVIOR_AI";return result_;
 }
 bool active()const{return active_;}
};
} // namespace offline_demo
