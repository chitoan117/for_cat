#pragma once
#include <stdint.h>
#include <math.h>
namespace d1_pump {
struct Gate {
 bool enabled=false,running=false,fault=false,driver_verified=false;
 uint32_t started=0,last_sample=0;
 unsigned hits=0,pulses=0;bool have_sample=false;
 const char* reason="DISABLED";
 static constexpr uint32_t FRESH_MS=1200,MAX_RUN_MS=10000;
 static constexpr float ON_CM=5.7f,OFF_CM=5.5f;
 static float percent(float){return NAN;}
 void disable(){enabled=false;running=false;hits=0;have_sample=false;reason="DISABLED";}
 void reset(){disable();fault=false;pulses=0;}
 bool arm(){if(!driver_verified||fault)return false;disable();enabled=true;pulses=0;reason="WAIT_D1";return true;}
 bool fail(const char* why){running=false;fault=true;hits=0;reason=why;return false;}
 bool step(uint32_t now,bool valid,float cm,uint32_t stamp){
  if(!enabled||!driver_verified||fault){running=false;return false;}
  const bool fresh=valid&&isfinite(cm)&&cm>=2&&cm<=400&&uint32_t(now-stamp)<=FRESH_MS;
  if(running){
   if(!fresh)return fail("D1_LOST_OFF");
   // Stop on the first fresh raw D1 target sample; no smoothing/debounce here.
   if(cm<=OFF_CM){running=false;hits=0;reason="TARGET_55CM";return false;}
   if(uint32_t(now-started)>=MAX_RUN_MS)return fail("TIME_LIMIT_OFF");
   return true;
  }
  if(!fresh){hits=0;have_sample=false;reason="D1_INVALID";return false;}
  if(cm<ON_CM){hits=0;reason=cm<=OFF_CM?"TARGET_55CM":"LEVEL_OK";return false;}
  if(have_sample&&stamp==last_sample)return false;
  if(have_sample&&uint32_t(stamp-last_sample)>FRESH_MS)hits=0;
  have_sample=true;last_sample=stamp;
  // Three distinct raw samples prevent a single noisy low-water reading starting a run.
  if(++hits<3){reason="CONFIRMING_D1";return false;}
  hits=0;++pulses;started=now;running=true;reason="FILLING_55CM";return true;
 }
};
}
