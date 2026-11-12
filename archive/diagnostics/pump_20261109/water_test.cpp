#include <assert.h>
#include <stdint.h>
#include <math.h>
#include <stdio.h>
#undef isfinite
namespace std { inline bool isfinite(float v){return __builtin_isfinite(v);} }
namespace m4 {
struct LevelCalibration { bool calibrated; float full_cm,empty_cm; bool valid()const {return calibrated&&std::isfinite(full_cm)&&std::isfinite(empty_cm)&&full_cm>0&&empty_cm>full_cm;} };
struct Measurement { bool valid=true; float value=0; uint32_t sampled_at_ms=0; };
struct Ultrasonic { Measurement raw,filtered; };
}
bool sensors_enabled=true;
int gpio=0; constexpr int LOW=0,HIGH=1;
namespace current_hardware {constexpr int PUMP_CONTROL=7;}
void digitalWrite(int p,int v){assert(p==7);gpio=v;}
m4::Ultrasonic bowl_d1,tank_d2;
namespace pcb_levels {
m4::LevelCalibration bowl{true,2,12},tank{true,2,12};
float target=90; bool enabled=true,running=false,fault=false; bool driver_confirmed=true,storage=true;
uint32_t started=0,low_stamp=0; unsigned low_hits=0;
const char* reason="DISABLED";
constexpr uint32_t FRESH_MS=1200,MAX_RUN_MS=30000;
float percent(const m4::Ultrasonic& u, const m4::LevelCalibration& g, uint32_t now) {
  if (!sensors_enabled || !g.valid() || !u.raw.valid || !u.filtered.valid
      || !std::isfinite(u.raw.value) || !std::isfinite(u.filtered.value)
      || u.raw.value<2 || u.raw.value>400 || u.filtered.value<2 || u.filtered.value>400
      || uint32_t(now-u.raw.sampled_at_ms)>FRESH_MS
      || uint32_t(now-u.filtered.sampled_at_ms)>FRESH_MS) return NAN;
  float p=100.0f*(g.empty_cm-u.filtered.value)/(g.empty_cm-g.full_cm);
  return p<0 ? 0 : (p>100 ? 100 : p);
}
void off(const char* why) {
  if (driver_confirmed) digitalWrite(current_hardware::PUMP_CONTROL, LOW); // Confirmed PCB HIGH=ON only.
  running=false; low_hits=0; reason=why;
}
void disable() { enabled=false; off("DISABLED"); }
void tick(uint32_t now) {
  if (!enabled || fault) { off(fault ? reason : "DISABLED"); return; }
  float bp=percent(bowl_d1,bowl,now), tp=percent(tank_d2,tank,now);
  if (!driver_confirmed || !storage || !std::isfinite(bp)||!std::isfinite(tp)||!std::isfinite(target) || target<=50 || target>100) { if(running) fault=true; off("INVALID_LEVEL_OR_CALIBRATION"); return; }
  if (tp<=0.0f) { if(running) fault=true; off("RESERVOIR_EMPTY"); return; }
  if (running) {
    if (uint32_t(now-started)>=MAX_RUN_MS) { fault=true; off("TIMEOUT_LATCHED"); return; }
    if (bp>=target) { off("TARGET_REACHED"); return; }
    return;
  }
  if (bp>=50.0f) { low_hits=0; reason="BOWL_SUFFICIENT"; return; }
  if (low_stamp==bowl_d1.raw.sampled_at_ms) return;
  if (uint32_t(bowl_d1.raw.sampled_at_ms-low_stamp)>FRESH_MS) low_hits=0;
  low_stamp=bowl_d1.raw.sampled_at_ms;
  if (++low_hits<3) { reason="CONFIRMING_LOW_LEVEL"; return; }
  digitalWrite(current_hardware::PUMP_CONTROL,HIGH);
  running=true; started=now; reason="REFILLING";
}
}
using namespace pcb_levels;
void sample(uint32_t t,float bp,float tp=50) {
  bowl_d1.raw.sampled_at_ms=bowl_d1.filtered.sampled_at_ms=t;
  tank_d2.raw.sampled_at_ms=tank_d2.filtered.sampled_at_ms=t;
  bowl_d1.raw.value=bowl_d1.filtered.value=12-bp/10;
  tank_d2.raw.value=tank_d2.filtered.value=12-tp/10;
}
void reset(){disable();enabled=true;fault=false;low_stamp=0;bowl_d1.raw.valid=tank_d2.raw.valid=true;}
void start(uint32_t t){for(int i=0;i<3;i++){sample(t+i,49);tick(t+i);} assert(running&&gpio==1);}
int main(){
  sample(10,50);tick(10);assert(!running&&low_hits==0);
  sample(11,49);tick(11);tick(11);assert(low_hits==1&&!running);
  sample(12,49);tick(12);assert(!running);sample(13,49);tick(13);assert(running&&gpio==1);
  sample(14,89);tick(14);assert(running);sample(15,90);tick(15);assert(!running&&gpio==0);
  reset();start(20);tank_d2.raw.valid=false;tick(23);assert(!running&&gpio==0);
  reset();start(30);sample(33,40,0);tick(33);assert(!running&&gpio==0);
  reset();start(40);tick(1243);assert(!running&&gpio==0);
  reset();start(50);sample(30052,40);tick(30052);assert(fault&&!running&&gpio==0);
  sample(30053,40);tick(30053);assert(!running);
  reset();start(0xfffffff0u);sample(30000,40);tick(30000);assert(fault&&!running);
  reset();bowl.calibrated=false;sample(100,20);tick(100);assert(!running);bowl.calibrated=true;
  reset();start(200);disable();assert(!enabled&&!running&&gpio==0);
  reset();driver_confirmed=false;sample(300,20);tick(300);assert(!running);driver_confirmed=true;
  reset();storage=false;sample(400,20);tick(400);assert(!running);storage=true;
  reset();start(500);tank_d2.raw.valid=false;tick(503);assert(fault&&!running);tank_d2.raw.valid=true;for(int i=0;i<5;i++){sample(510+i,20);tick(510+i);}assert(!running);
  reset();sample(600,49);tick(600);sample(2000,49);tick(2000);assert(low_hits==1&&!running);
  reset();bowl_d1.raw.value=NAN;tick(2100);assert(!running);
  puts("PASS: 50% start boundary, 3 distinct readings, target stop, invalid/stale/empty tank stop, calibration gate, timeout latch, rollover, manual disable");
}
