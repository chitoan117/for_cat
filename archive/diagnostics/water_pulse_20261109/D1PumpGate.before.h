#pragma once
#include <stdint.h>
#include <math.h>
namespace d1_pump {
struct Gate {
  bool enabled=false, running=false, fault=false, driver_verified=false;
  uint32_t started=0, last_sample=0;
  unsigned hits=0;
  bool have_sample=false;
  const char* reason="DISABLED";
  static constexpr uint32_t FRESH_MS=1200, MAX_RUN_MS=10000;
  static float percent(float cm) {
    if(!isfinite(cm)||cm<2||cm>400)return NAN;
    return fmaxf(0.0f,fminf(100.0f,100.0f*(22.7f-cm)/1.2f));
  }
  void disable() { enabled=false; running=false; hits=0; have_sample=false; reason=fault?reason:"DISABLED"; }
  void reset() { disable();fault=false;reason="DISABLED"; }
  bool arm() { if(!driver_verified||fault)return false;disable();enabled=true;reason="WAIT_D1";return true; }
  void fail(const char* why) { running=false;fault=true;hits=0;reason=why; }
  bool step(uint32_t now,bool valid,float cm,uint32_t stamp) {
    if(!enabled||!driver_verified||fault) {running=false;return false;}
    if(running && uint32_t(now-started)>=MAX_RUN_MS) {fail("TIMEOUT");return false;}
    const bool fresh=valid && isfinite(cm) && cm>=2 && cm<=400 && uint32_t(now-stamp)<=FRESH_MS;
    if(!fresh) {if(running)fail("D1_LOST");else{hits=0;reason="D1_INVALID";}return false;}
    if(running) {
      if(cm<=21.5f) {running=false;hits=0;reason="D1_FULL_215CM";}
      return running;
    }
    if(cm<=22.1f) {hits=0;reason="BOWL_SUFFICIENT";return false;}
    if(have_sample && stamp==last_sample)return false;
    if(have_sample && uint32_t(stamp-last_sample)>FRESH_MS)hits=0;
    last_sample=stamp;have_sample=true;
    if(++hits<2) {reason="CONFIRMING_D1";return false;}
    hits=0;running=true;started=now;reason="REFILLING_BELOW_50PCT";return true;
  }
};
}
