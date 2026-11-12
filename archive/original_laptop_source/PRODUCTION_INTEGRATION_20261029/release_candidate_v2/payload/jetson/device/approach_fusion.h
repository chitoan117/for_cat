#pragma once
#include "decision_logic.h"
#include "food_roi.h"
namespace forcat {
struct RoiAiEvidence {
 std::string species="UNKNOWN";bool fresh=false,roi_calibrated=false;
 uint32_t sequence=0;uint64_t stamp=0;
 // FULL_FRAME is the default scope, never proof of membership at the tray.
 food_roi::Mode roi_mode=food_roi::Mode::FULL_FRAME;
  bool config_valid=true,bbox_available=true,decision_eligible=true;
  std::string producer_epoch="";
 bool scopeAllowed()const{return food_roi::evidenceAllowed(roi_mode,roi_mode,config_valid,roi_calibrated,bbox_available,decision_eligible);}
};
struct ApproachEvidence {
 uint32_t boot=0,link=0,now=0,sample=0,event=0,event_at=0;
 bool valid=false,confirmed=false;double cm=0;
};
enum class ApproachAction {NONE,AUTO_CAT,DOG_WARNING};
class ApproachFusion {
  AutoCatGate cat_,dog_;uint32_t consumed_=0;bool anchored_=false;uint32_t mcu_anchor_=0;uint64_t host_anchor_=0;
  std::string ai_epoch_;
 static NearConfig temporal(){NearConfig c;c.distance_cm=20;return c;}
 public:
 ApproachFusion():cat_(temporal(),"CAT"),dog_(temporal(),"DOG"){}
  void reset(){cat_.reset();dog_.reset();consumed_=0;anchored_=false;ai_epoch_.clear();}
  ApproachAction update(const ApproachEvidence& a,const RoiAiEvidence& ai,uint64_t now){
    if(!ai.producer_epoch.empty() && ai.producer_epoch!=ai_epoch_){
      cat_.reset();dog_.reset();ai_epoch_=ai.producer_epoch;
      // Keep consumed_ across detector restarts: an old near event cannot feed twice.
    }
   if(!anchored_){anchored_=true;mcu_anchor_=a.now;host_anchor_=now;}
   const uint64_t elapsed=static_cast<uint32_t>(a.now-mcu_anchor_);
   const bool transport=now>=host_anchor_ && now-host_anchor_+250>=elapsed && now-host_anchor_<=elapsed+750;
   const bool scope=ai.scopeAllowed();
   const bool fresh=transport && ai.fresh && scope && now>=ai.stamp && now-ai.stamp<=1500;
   cat_.observeSpecies(ai.species,fresh,scope,ai.sequence,now);
   dog_.observeSpecies(ai.species,fresh,scope,ai.sequence,now);
   if(!transport || !a.valid || !std::isfinite(a.cm) || a.cm<5 || a.cm>20 ||
      static_cast<uint32_t>(a.now-a.sample)>750 || !a.confirmed || !a.event || a.event<=consumed_ ||
      static_cast<uint32_t>(a.now-a.event_at)>1500 || !fresh)return ApproachAction::NONE;
   // Same1500ms observation window, no unrelated cached AI from an old encounter.
   const uint64_t event_host=now-static_cast<uint32_t>(a.now-a.event_at);
   if((ai.stamp>event_host?ai.stamp-event_host:event_host-ai.stamp)>1500)return ApproachAction::NONE;
   if(ai.species=="DOG" && dog_.stable()){consumed_=a.event;return ApproachAction::DOG_WARNING;}
   if(ai.species=="CAT" && cat_.stable()){consumed_=a.event;return ApproachAction::AUTO_CAT;}
   return ApproachAction::NONE;
 }
};
} // namespace forcat
