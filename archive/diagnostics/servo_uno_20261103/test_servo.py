from pathlib import Path
import subprocess,os
root=Path(__file__).parent
code=(root/'esp32/esp32.ino').read_text(encoding='utf-8')
def block(marker):
    start=code.index(marker)
    begin=code.index('{',start)
    depth=1
    end=begin+1
    while depth:
        if code[end]=='{': depth+=1
        elif code[end]=='}': depth-=1
        end+=1
    return code[start:end]

h=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#undef isfinite
namespace std { using ::strtol; inline bool isfinite(float v){return __builtin_isfinite(v);} }
void operator delete(void* p) noexcept { free(p); }
void operator delete(void* p, size_t) noexcept { free(p); }
constexpr int LOW=0,OUTPUT=1,PIN_CLOSE_LIMIT=47;
unsigned gpio_reads=0, attaches=0, detaches=0, writes=0;
bool hw_attached=false, fail_write=false;
uint32_t duty=0;
bool ledcAttach(int pin,int hz,int bits){assert(pin==6&&hz==50&&bits==14);++attaches;hw_attached=true;return true;}
bool ledcDetach(int pin){assert(pin==6);++detaches;hw_attached=false;return true;}
bool ledcWrite(int pin,uint32_t value){assert(pin==6);++writes;if(fail_write)return false;duty=value;return true;}
void digitalWrite(int,int){}
void pinMode(int,int){}
int digitalRead(int){++gpio_reads;return LOW;}
struct Serial { template<class... T> void printf(const char*,T...){} void print(const char*){} } serial;
Serial& protocolSerial(){return serial;}
namespace servo_bench {
constexpr int pin=6;
constexpr uint16_t electrical_min_us=1000,electrical_max_us=2000;
class Output { public: virtual ~Output()=default; virtual bool start(uint16_t)=0; virtual bool write(uint16_t)=0; virtual bool off()=0; };
}
'''
h+=block('class LedcServoOutput final : public servo_bench::Output {')+';\nLedcServoOutput pwm;\n'
h+=r'''
enum class FeedStage { IDLE, FAULT, OPENING, WAIT_WEIGHT, WAIT_HX, WAIT_CAT, CLOSING, DIAG_OPEN, DIAG_CLOSE, DONE };
enum class BenchCal { Idle, Tare };
BenchCal bench_cal=BenchCal::Idle;
constexpr bool USE_CLOSE_LIMIT_SWITCH=false;
'''
for name in ['SERVO_OPEN_US','SERVO_CLOSE_US','SERVO_NEUTRAL_US','SERVO_FINE_MS','MAX_SERVO_ACTIVE_MS']:
    line=next(x for x in code.splitlines() if x.startswith('constexpr ') and f' {name} =' in x)
    h+=line+'\n'
for name in ['open_ms','close_ms']:
    h+=next(x for x in code.splitlines() if x.startswith(f'uint16_t {name} ='))+'\n'
h+=r'''
FeedStage feed_stage=FeedStage::IDLE;
bool manual_feed_active=false,close_on_weight=false,limit_closed=true,physical_closed_verified=false;
bool cat_inspect_required=false,servo_armed=false,dog_running=false,demo_exited=false;
bool meal_logged=false,meal_start_locked=false;
float last_delta_g=35,meal_starting_g=0,meal_remaining_g=0,meal_consumed_g=0;
float baseline_g=0;
struct Measurement { bool valid=false; float value=0; };
struct Hx { Measurement signed_grams; } hx;
bool benchScaleSample(uint32_t,float&,uint32_t&){return false;}
void buzzerStop(){dog_running=false;}
float meal_plateau_ref_g=0,meal_stable_ref_g=0;
const char* meal_preference="NONE";
uint32_t meal_plateau_since=0,meal_closed_at=0,meal_stable_since=0;
uint32_t phase_at=0,started_at=0,servo_move_for_ms=0,last_scale_ms=0;
unsigned cat_hits=0;
char current_food='A';
'''
for marker in ['bool busy() {','void neutralMotor() {','void cancel(const char* reason, bool error) {',
               'bool startOpen(uint32_t now) {','void startClose(uint32_t now, bool by_weight) {',
               'void beginManualFeed(uint32_t now, const char* source) {',
               'bool manualServoMove(bool opening, uint32_t duration, uint32_t now) {',
               'void diagServo(bool opening, uint32_t now) {','bool setMotionTime(const char* text, bool opening) {']:
    h+=block(marker)+'\n'
for name,marker in [('diagTick','  if (feed_stage == FeedStage::DIAG_OPEN || feed_stage == FeedStage::DIAG_CLOSE) {'),
                    ('openingTick','  if (feed_stage == FeedStage::OPENING) {'),
                    ('closingTick','  if (feed_stage == FeedStage::CLOSING) {')]:
    h+=f'void {name}(uint32_t now) {{\n'+block(marker)+'\n}\n'
h+=r'''
uint32_t expectedDuty(unsigned us){return (us*16384u+10000u)/20000u;}
void assertStopped(){assert(hw_attached&&!pwm.moving()&&duty==expectedDuty(1500));}
int main(){
  assert(SERVO_OPEN_US==1400&&SERVO_CLOSE_US==1600&&SERVO_NEUTRAL_US==1500);
  assert(open_ms==1100&&close_ms==900&&SERVO_FINE_MS==170);
  assert(!pwm.attached()); // Boot output remains detached until a movement command.
  assert(manualServoMove(true,open_ms,100));
  assert(duty==expectedDuty(1400)&&attaches==1&&pwm.moving());
  assert(!manualServoMove(false,close_ms,200)); // No restart or queue while moving.
  beginManualFeed(200,"WEB"); // A web/button feed must not preempt servo adjustment.
  assert(phase_at==100&&servo_move_for_ms==1100);
  diagTick(1199); assert(pwm.moving()); diagTick(1200); assertStopped();
  assert(manualServoMove(false,close_ms,1300));
  assert(attaches==1&&duty==expectedDuty(1600)); // Reuse neutral PWM.
  diagTick(2199); assert(pwm.moving()); diagTick(2200); assertStopped();
  assert(manualServoMove(false,SERVO_FINE_MS,2300));
  diagTick(2469); assert(pwm.moving()); diagTick(2470); assertStopped();
  assert(manualServoMove(true,SERVO_FINE_MS,2500));
  assert(duty==expectedDuty(1400)); diagTick(2670); assertStopped();
  assert(manualServoMove(true,open_ms,2800)); cancel("STOP",false); assertStopped();
  assert(cat_inspect_required);
  assert(manualServoMove(false,SERVO_FINE_MS,3000));
  diagTick(3170); assertStopped(); // Explicit correction allowed after stop.
  assert(cat_inspect_required); // Correction does not unlock automatic feeding.
  cat_inspect_required=false;
  assert(startOpen(4000)); openingTick(5099); assert(pwm.moving());
  openingTick(5100); assertStopped(); assert(feed_stage==FeedStage::WAIT_WEIGHT);
  startClose(5200,true); assert(duty==expectedDuty(1600));
  closingTick(6099); assert(pwm.moving()); closingTick(6100); assertStopped();
  assert(feed_stage==FeedStage::DONE&&!physical_closed_verified);
  startClose(6200,false); closingTick(7100); assertStopped();
  assert(feed_stage==FeedStage::FAULT&&cat_inspect_required);
  feed_stage=FeedStage::IDLE;
  assert(manualServoMove(true,170,UINT32_MAX-100));
  diagTick(68); assert(pwm.moving()); diagTick(69); assertStopped();
  assert(setMotionTime("1100",true)); assert(setMotionTime("900",false));
  assert(!setMotionTime("99",true)&&!setMotionTime("5001",false));
  assert(!setMotionTime("900x",false));
  dog_running=true; assert(!manualServoMove(true,170,8000)); dog_running=false;
  bench_cal=BenchCal::Tare; assert(!manualServoMove(true,170,8000)); bench_cal=BenchCal::Idle;
  assert(!manualServoMove(true,0,8000)&&!manualServoMove(true,5001,8000));
  assert(manualServoMove(true,170,8000)); fail_write=true; neutralMotor();
  assert(!pwm.attached()&&detaches==1); // Output failure falls back to detach.
  assert(gpio_reads==0);
  puts("PASS: UNO PWM/durations, neutral hold, repeat/fine moves, busy rejection, automatic cycle, STOP, rollover, fault and bounds");
}
'''
(root/'servo_test.cpp').write_text(h,encoding='utf-8')
env=os.environ.copy()
env['ZIG_GLOBAL_CACHE_DIR']=str(root.parent/'timed_close_20261103/zig-global-cache')
env['ZIG_LOCAL_CACHE_DIR']=str(root/'zig-local-cache')
with (root/'native_build.log').open('w') as log:
    subprocess.run([r'D:\Agent_Cat\for_cat\.tools-zig\zig-x86_64-windows-0.16.0\zig.exe','c++','-std=c++17','-O0','-nostdlib++','-fno-exceptions','-fno-rtti',str(root/'servo_test.cpp'),'-o',str(root/'servo_test.exe')],env=env,check=True,stdout=log,stderr=log)
r=subprocess.run([str(root/'servo_test.exe')],capture_output=True,text=True,check=True)
(root/'native_test_result.txt').write_text(r.stdout,encoding='utf-8')
print(r.stdout)
# Check command routing and immediate 0 handling without copying CAT/DOG meanings.
assert 'if (!std::strcmp(line, "1")) {' in code
assert 'if (!std::strcmp(line, "2")) {' in code
assert "if (c == '0' && rxn == 0 && !discard)" in code
assert 'servo_fine_open' in code and 'servo_fine_close' in code
print('PASS: command compatibility and immediate standalone 0 handler present')
