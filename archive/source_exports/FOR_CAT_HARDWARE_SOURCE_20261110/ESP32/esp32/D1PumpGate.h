#pragma once
#include <stdint.h>
#include <math.h>
namespace d1_pump {
struct Gate {
 bool enabled=false,running=false,fault=false,driver_verified=false,resting=false,refilling=false;
 uint32_t started=0,rest_at=0,last_sample=0;
 unsigned hits=0,pulses=0;bool have_sample=false;
 const char* reason="DISABLED";
 static constexpr uint32_t FRESH_MS=1200,PULSE_MS=1000,SETTLE_MS=5000;
 static constexpr unsigned MAX_PULSES=3;
 static float percent(float){return NAN;} // No precise percentage from noisy sub-mm target.
 void disable(){enabled=false;running=false;resting=false;refilling=false;hits=0;have_sample=false;if(!fault)reason="DISABLED";}
 void reset(){disable();fault=false;pulses=0;reason="DISABLED";}
 bool arm(){if(!driver_verified||fault)return false;disable();enabled=true;pulses=0;reason="WAIT_D1";return true;}
 void stopPulse(uint32_t now,const char* why){running=false;resting=true;rest_at=now;hits=0;reason=why;}
 bool step(uint32_t now,bool valid,float cm,uint32_t stamp){
  if(!enabled||!driver_verified||fault){running=false;return false;}
  bool fresh=valid&&isfinite(cm)&&cm>=2&&cm<=400&&uint32_t(now-stamp)<=FRESH_MS;
  if(running){
   if(!fresh){stopPulse(now,"D1_LOST_OFF");return false;}
   if(cm<=5.9f){refilling=false;stopPulse(now,"TARGET_59CM");return false;}
   if(uint32_t(now-started)>=PULSE_MS){stopPulse(now,"PULSE_COMPLETE");return false;}
   return true;
  }
  if(resting&&uint32_t(now-rest_at)<SETTLE_MS){hits=0;reason="SETTLING";return false;}
  resting=false;
  if(!fresh){hits=0;reason="D1_INVALID";return false;}
  if(cm<=5.9f){refilling=false;hits=0;reason="TARGET_59CM";return false;}
  if(cm>6.4f||(!refilling&&cm<6.1f)){hits=0;reason="OUTSIDE_TRIGGER_BAND";return false;}
  if(have_sample&&stamp==last_sample)return false;
  if(have_sample&&uint32_t(stamp-last_sample)>FRESH_MS)hits=0;
  have_sample=true;last_sample=stamp;
  if(++hits<3){reason="CONFIRMING_D1";return false;}
  hits=0;
  if(pulses>=MAX_PULSES){fault=true;reason="PULSE_LIMIT";return false;}
  ++pulses;started=now;refilling=true;running=true;reason="PULSE_ON";return true;
 }
};
}
