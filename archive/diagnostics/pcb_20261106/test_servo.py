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
namespace std { using ::strtol; inline bool isfinite(float v){return __builtin_isfinite(v);} inline float fabs(float v){return __builtin_fabsf(v);} }
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
for name in ['SERVO_OPEN_US','SERVO_CLOSE_US','SERVO_NEUTRAL_US','SERVO_FINE_MS','MAX_SERVO_ACTIVE_MS','CLOSE_AT_G','MAX_NORMAL_G','CAT_MIN_CM','CAT_MAX_CM','CAT_WAIT_TIMEOUT_MS','HX_WAIT_TIMEOUT_MS','WEIGHT_WAIT_TIMEOUT_MS']:
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
bool scale_ready=false; float scale_value=0; uint32_t scale_stamp=1;
bool benchScaleSample(uint32_t,float& grams,uint32_t& stamp){if(!scale_ready)return false;grams=scale_value;stamp=scale_stamp;return true;}
struct Sample { uint32_t now_ms=0; };
struct RawDistance { bool valid=false,fresh=false; uint32_t sampled_at_ms=0; float value=0; };
struct Hc { RawDistance raw; } hc;
void buzzerStop(){dog_running=false;}
float meal_plateau_ref_g=0,meal_stable_ref_g=0;
const char* meal_preference="NONE";
uint32_t meal_plateau_since=0,meal_closed_at=0,meal_stable_since=0;
uint32_t phase_at=0,started_at=0,servo_move_for_ms=0,last_scale_ms=0,last_hc_ms=0;
unsigned cat_hits=0;
char current_food='A';
'''
for marker in ['bool busy() {','void neutralMotor() {','void cancel(const char* reason, bool error) {',
               'bool startOpen(uint32_t now) {','void startClose(uint32_t now, bool by_weight) {',
               'bool acceptableScaleSample(const Sample& s) {',
               'void beginManualFeed(uint32_t now, const char* source) {',
               'bool beginCatWithScale(const Sample& s) {',
               'bool manualServoMove(bool opening, uint32_t duration, uint32_t now) {',
               'void diagServo(bool opening, uint32_t now) {','bool setMotionTime(const char* text, bool opening) {']:
    h+=block(marker)+'\n'
for name,marker in [('diagTick','  if (feed_stage == FeedStage::DIAG_OPEN || feed_stage == FeedStage::DIAG_CLOSE) {'),
                    ('openingTick','  if (feed_stage == FeedStage::OPENING) {'),
                    ('closingTick','  if (feed_stage == FeedStage::CLOSING) {'),
                    ('weightTick','  if (feed_stage == FeedStage::WAIT_WEIGHT) {'),
                    ('catTick','  if (feed_stage == FeedStage::WAIT_CAT) {'),
                    ('hxTick','  if (feed_stage == FeedStage::WAIT_HX) {'),
                    ('globalTick','  if (feed_stage != FeedStage::CLOSING && uint32_t(now - started_at) > 45000u) {')]:
    # WAIT_WEIGHT occurs in beginManualFeed too: select only the actual tick branch.
    saved=code
    if name=='weightTick': code=code[code.index('void tick(const Sample& s, uint32_t now) {'):]
    h+=f'void {name}(uint32_t now) {{ Sample s; s.now_ms=now;\n'+block(marker)+'\n}\n'
    code=saved
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
  fail_write=false; feed_stage=FeedStage::IDLE; cat_inspect_required=false;
  unsigned before_writes=writes;
  scale_ready=false; hx.signed_grams.valid=true; hx.signed_grams.value=0;
  beginManualFeed(9000,"WEB");
  assert(!pwm.moving()&&writes==before_writes); // No stale or synthetic 0g fallback.
  scale_ready=true; scale_value=0; scale_stamp=10000;
  beginManualFeed(10000,"BUTTON"); assert(pwm.moving()&&manual_feed_active);
  openingTick(11100); assert(feed_stage==FeedStage::WAIT_WEIGHT); assertStopped();
  scale_value=29; scale_stamp=15099; weightTick(15099);
  assert(feed_stage==FeedStage::WAIT_WEIGHT);
  scale_stamp=15100; weightTick(15100);
  assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
  closingTick(16000); assert(feed_stage==FeedStage::FAULT); assertStopped();
  // A valid measured threshold produces a normal close; >40g is not MASS OK.
  beginManualFeed(17000,"WEB"); openingTick(18100);
  scale_value=baseline_g+30; scale_stamp=18200; weightTick(18200);
  assert(close_on_weight); closingTick(19100); assert(feed_stage==FeedStage::DONE);
  scale_value=0; beginManualFeed(20000,"WEB"); openingTick(21100);
  scale_value=41; scale_stamp=21200; weightTick(21200);
  assert(!close_on_weight); closingTick(22100); assert(feed_stage==FeedStage::FAULT);
  // Loss of the scale during an open cycle triggers a bounded failure close.
  scale_value=0; scale_ready=true; beginManualFeed(23000,"WEB"); openingTick(24100);
  scale_ready=false; weightTick(25900); assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
  closingTick(26800); assert(feed_stage==FeedStage::FAULT); assertStopped();
  // Missing HX never energizes while waiting; valid nonzero CAT baseline blocks.
  feed_stage=FeedStage::WAIT_HX; started_at=30000; before_writes=writes;
  hxTick(55000); assert(writes==before_writes&&!pwm.moving());
  hxTick(55001); assert(feed_stage==FeedStage::FAULT);
  scale_ready=true; scale_value=3; Sample sample; sample.now_ms=60000;
  assert(!beginCatWithScale(sample)&&!pwm.moving());
  scale_value=0; assert(beginCatWithScale(sample));
  hc.raw={true,true,60100,10}; catTick(60100); assert(cat_hits==1);
  catTick(60101); assert(cat_hits==1); // Duplicate sample does not count.
  hc.raw.valid=false; hc.raw.fresh=false; catTick(60200); assert(cat_hits==0);
  hc.raw={true,true,60300,10}; catTick(60300);
  hc.raw.sampled_at_ms=60500; catTick(60500); assert(cat_hits==2&&!pwm.moving());
  hc.raw.sampled_at_ms=60700; catTick(60700); assert(feed_stage==FeedStage::OPENING&&pwm.moving());
  cancel("STOP",false);
  // Global deadline still grants the recovery close its 900ms, then stops.
  feed_stage=FeedStage::WAIT_WEIGHT; started_at=0; globalTick(45001);
  assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
  globalTick(45002); closingTick(45002); assert(pwm.moving());
  closingTick(45901); assertStopped(); assert(feed_stage==FeedStage::FAULT);
  puts("PASS: UNO PWM/durations, neutral hold, repeat/fine moves, busy rejection, automatic cycle, STOP, rollover, fault and bounds");
  puts("PASS: missing/stale scale manual block, mass threshold/overshoot/timeout, HX loss, consecutive HC1, no premature recovery-stop");
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
