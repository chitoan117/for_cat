#line 1 "D:\\Agent_Cat\\diagnostics\\backup30_20261111\\esp32\\MealPreferenceGate.h"
#pragma once
#include <stdint.h>
#include <math.h>
namespace meal_behavior {
enum class Phase { IDLE, CAPTURING, OBSERVING, FINAL, INVALID };
struct Tracker {
 Phase phase=Phase::IDLE;
 char food='A';
 float starting=NAN,remaining=NAN,consumed=NAN,ref=NAN;
 uint32_t begun=0,observed=0,stable_at=0,last_good=0,last_stamp=0;
 unsigned stable_samples=0;
 bool have_stamp=false,stable=false;
 const char* reason="NO_MEAL";
 static constexpr uint32_t WINDOW_MS=120000,STABLE_MS=3000,FRESH_MS=1200;
 const char* phaseName()const{
  switch(phase){case Phase::IDLE:return "IDLE";case Phase::CAPTURING:return "CAPTURING";
   case Phase::OBSERVING:return "OBSERVING";case Phase::FINAL:return "FINAL";default:return "INVALID";}
 }
 const char* preference()const{
  if(phase==Phase::INVALID)return "INVALID";
  if(phase!=Phase::FINAL)return phase==Phase::IDLE?"NONE":"WAITING";
  if(consumed>starting*.5f)return "LIKE";
  if(consumed<=5.5f)return "DISLIKE";
  return "MODERATE";
 }
 void begin(uint32_t now,char f){
  *this=Tracker{};phase=Phase::CAPTURING;food=f;begun=last_good=now;reason="WAIT_STABLE_PORTION";
 }
 bool beginVerified(uint32_t now,char f,float portion){
  if(!isfinite(portion)||portion<35||portion>40)return false;
  begin(now,f);phase=Phase::OBSERVING;starting=remaining=portion;consumed=0;
  observed=now;reason="OBSERVING";return true;
 }
 void reset(){*this=Tracker{};}
 void invalidate(const char* why){phase=Phase::INVALID;stable=false;reason=why;}
 void cancel(){if(phase==Phase::CAPTURING||phase==Phase::OBSERVING)invalidate("MEAL_INTERRUPTED");}
 uint32_t elapsed(uint32_t now)const{return phase==Phase::OBSERVING||phase==Phase::FINAL?uint32_t(now-observed):0;}
 bool finish(uint32_t now){
  if(phase!=Phase::OBSERVING||!stable||elapsed(now)<10000u||uint32_t(now-last_good)>FRESH_MS)return false;
  consumed=fmaxf(0,starting-remaining);phase=Phase::FINAL;reason="COMPLETE";return true;
 }
 void sample(uint32_t now,bool valid,float net,uint32_t stamp){
  if(phase!=Phase::CAPTURING&&phase!=Phase::OBSERVING)return;
  if(!valid||!isfinite(net)||uint32_t(now-stamp)>FRESH_MS){
   stable=false;ref=NAN;stable_samples=0;
   if(uint32_t(now-last_good)>10000u)invalidate("SCALE_LOST");
   return;
  }
  if(have_stamp&&last_stamp==stamp)return;
  have_stamp=true;last_stamp=stamp;last_good=now;
  if(net < -2.0f){invalidate("BOWL_REMOVED_OR_ZERO_CHANGED");return;}
  const bool capture=phase==Phase::CAPTURING;
  if(capture&&uint32_t(now-begun)>30000u){invalidate("NO_STABLE_STARTING_WEIGHT");return;}
  if((capture&&(net<20||net>70))||(!capture&&net>starting+2)){
   stable=false;ref=NAN;stable_samples=0;
   if(uint32_t(now-begun)>300000u)invalidate("UNSTABLE_OR_LOAD_CHANGED");
   return;
  }
  if(!isfinite(ref)||fabsf(net-ref)>.5f){ref=net;stable_at=now;stable_samples=1;stable=false;}
  else ++stable_samples;
  const uint32_t needed=capture?4000u:STABLE_MS;
  stable=stable_samples>=3&&uint32_t(now-stable_at)>=needed;
  if(capture){
   if(stable){starting=remaining=net;consumed=0;phase=Phase::OBSERVING;observed=now;reason="OBSERVING";stable_at=now;stable=false;stable_samples=1;}
   else if(uint32_t(now-begun)>30000u)invalidate("NO_STABLE_STARTING_WEIGHT");
   return;
  }
  if(stable){remaining=fminf(starting,fmaxf(0,net));consumed=fmaxf(0,starting-remaining);}
  if(elapsed(now)>=WINDOW_MS&&stable)finish(now);
  if(phase==Phase::OBSERVING&&elapsed(now)>WINDOW_MS+60000u)invalidate("NO_STABLE_FINAL_WEIGHT");
 }
};
}
