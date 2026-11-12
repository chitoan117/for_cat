from pathlib import Path
import subprocess,os
r=Path(__file__).parent
s=(r/'esp32/esp32.ino').read_text(encoding='utf-8')
s=s[s.index('namespace pcb_levels {'):]
def block(marker):
    a=s.index(marker); b=s.index('{',a); n=1; e=b+1
    while n:
        if s[e]=='{': n+=1
        if s[e]=='}': n-=1
        e+=1
    return s[a:e]
h='''#include <assert.h>
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
'''
for marker in ['float percent(', 'void off(', 'void disable()', 'void tick(']: h+=block(marker)+'\n'
h+='''}
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
'''
(r/'water_test.cpp').write_text(h,encoding='utf-8')
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(r.parent/'timed_close_20261103/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(r/'zig-local-cache')
subprocess.run([r'D:\Agent_Cat\for_cat\.tools-zig\zig-x86_64-windows-0.16.0\zig.exe','c++','-std=c++17','-nostdlib++','-fno-exceptions','-fno-rtti',str(r/'water_test.cpp'),'-o',str(r/'water_test.exe')],check=True,env=env)
p=subprocess.run([str(r/'water_test.exe')],capture_output=True,text=True,check=True)
(r/'water_test_result.txt').write_text(p.stdout);print(p.stdout)
