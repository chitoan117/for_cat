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
for name in ['SERVO_OPEN_US','SERVO_CLOSE_US','SERVO_NEUTRAL_US','MAX_SERVO_ACTIVE_MS','CLOSE_AT_G','MAX_NORMAL_G','CAT_MIN_CM','CAT_MAX_CM','CAT_WAIT_TIMEOUT_MS','HX_WAIT_TIMEOUT_MS','WEIGHT_WAIT_TIMEOUT_MS']:
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
h+=block('enum class TimedGateStop : uint8_t {')+';\nTimedGateStop timed_gate_stop=TimedGateStop::UNKNOWN;\n'
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

h+='void confirmClosed() '+block('  if (!std::strcmp(line, "inspect_ok")) {').split('{',1)[1].join(['{','']).replace('bench_v8::','')+'\n'
h+=r'''
uint32_t expectedDuty(unsigned us){return (us*16384u+10000u)/20000u;}
void assertStopped(){assert(hw_attached&&!pwm.moving()&&duty==expectedDuty(1500));}
int main(){
 assert(open_ms==1100&&close_ms==900);
 assert(SERVO_OPEN_US==1400&&SERVO_CLOSE_US==1600&&SERVO_NEUTRAL_US==1500);
 assert(!pwm.attached()&&timed_gate_stop==TimedGateStop::UNKNOWN);
 // The unchanged startup policy allows a first isolated stroke from UNKNOWN.
 assert(manualServoMove(true,open_ms,100));
 assert(duty==expectedDuty(1400));
 assert(!manualServoMove(false,close_ms,200));
 beginManualFeed(200,"WEB"); assert(phase_at==100);
 diagTick(1199);assert(pwm.moving());diagTick(1200);assertStopped();
 assert(timed_gate_stop==TimedGateStop::OPEN);
 unsigned before=writes;
 assert(!manualServoMove(true,open_ms,1300)&&writes==before);
 assert(manualServoMove(false,close_ms,1400));
 diagTick(2299);assert(pwm.moving());diagTick(2300);assertStopped();
 assert(timed_gate_stop==TimedGateStop::CLOSED);
 before=writes;assert(!manualServoMove(false,close_ms,2400)&&writes==before);
 // No accumulating same-direction strokes across repeated button presses.
 for(uint32_t i=0;i<200;i++){
   uint32_t t=3000+i*2200;
   assert(manualServoMove(true,open_ms,t));diagTick(t+1100);assertStopped();
   before=writes;assert(!manualServoMove(true,open_ms,t+1101)&&writes==before);
   assert(manualServoMove(false,close_ms,t+1200));diagTick(t+2100);assertStopped();
   before=writes;assert(!manualServoMove(false,close_ms,t+2101)&&writes==before);
 }
 assert(manualServoMove(true,open_ms,500000));cancel("STOP",false);assertStopped();
 assert(cat_inspect_required&&timed_gate_stop==TimedGateStop::UNKNOWN);
 before=writes;
 assert(!manualServoMove(true,open_ms,500100));assert(!manualServoMove(false,close_ms,500100));
 scale_ready=true;scale_value=0;beginManualFeed(500200,"WEB");
 assert(cat_inspect_required&&writes==before&&!pwm.moving());
 confirmClosed();assert(!cat_inspect_required&&timed_gate_stop==TimedGateStop::CLOSED);
 assert(!physical_closed_verified); // Manual acknowledgement never becomes sensor evidence.
 // Actual normal feeding still waits for the unchanged measured30g threshold.
 scale_ready=false;before=writes;beginManualFeed(501000,"WEB");assert(writes==before);
 scale_ready=true;scale_value=0;scale_stamp=502000;
 beginManualFeed(502000,"BUTTON");assert(feed_stage==FeedStage::OPENING);
 openingTick(503099);assert(pwm.moving());openingTick(503100);assertStopped();
 assert(timed_gate_stop==TimedGateStop::OPEN);
 scale_value=29;scale_stamp=503200;weightTick(503200);assert(feed_stage==FeedStage::WAIT_WEIGHT);
 scale_value=30;scale_stamp=503300;weightTick(503300);assert(feed_stage==FeedStage::CLOSING&&close_on_weight);
 auto close_started=phase_at;before=writes;startClose(503700,true);assert(phase_at==close_started&&writes==before);
 closingTick(504199);assert(pwm.moving());closingTick(504200);assertStopped();
 assert(feed_stage==FeedStage::DONE&&timed_gate_stop==TimedGateStop::CLOSED&&!physical_closed_verified);
 // A manual-open gate cannot receive a second opening through the Web/feed path.
 assert(manualServoMove(true,open_ms,505000));diagTick(506100);assertStopped();before=writes;
 beginManualFeed(506200,"WEB");assert(writes==before&&cat_inspect_required&&feed_stage==FeedStage::FAULT);
 confirmClosed();
 // millis wrap works with full strokes; no fine-adjust stroke is available.
 assert(manualServoMove(true,open_ms,UINT32_MAX-100));
 diagTick(998);assert(pwm.moving());diagTick(999);assertStopped();
 cancel("STOP",false); // idle full stop retains estimate, no partial movement.
 assert(manualServoMove(false,close_ms,2000));diagTick(2900);assertStopped();
 // Output failure requires inspection; it cannot silently authorize another stroke.
 assert(manualServoMove(true,open_ms,3000));fail_write=true;cancel("OUTPUT",true);
 assert(!pwm.attached()&&cat_inspect_required&&timed_gate_stop==TimedGateStop::UNKNOWN);
 fail_write=false;confirmClosed();
 dog_running=true;assert(!manualServoMove(true,open_ms,5000));dog_running=false;
 bench_cal=BenchCal::Tare;assert(!manualServoMove(true,open_ms,5000));bench_cal=BenchCal::Idle;
 assert(gpio_reads==0); // No new endstop pin reads or hardware assumptions.
 // Regression of the owner's exact button sequence: OPEN, early CLOSE, OPEN again.
 scale_ready=true;scale_value=0;
 for(uint32_t t=10000;t<76000;t+=2200){
   scale_stamp=t;beginManualFeed(t,"BUTTON_GPIO21");assert(feed_stage==FeedStage::OPENING);
   openingTick(t+1100);assertStopped();assert(feed_stage==FeedStage::WAIT_WEIGHT);
   last_delta_g=0.1f;beginManualFeed(t+1200,"BUTTON_GPIO21");
   assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
   closingTick(t+2100);assertStopped();
   assert(feed_stage==FeedStage::FAULT&&!cat_inspect_required&&timed_gate_stop==TimedGateStop::CLOSED);
 }
 // A 4s manual timeout likewise stays a mass FAULT, but a full timed close is repeatable.
 beginManualFeed(100000,"BUTTON_GPIO21");openingTick(101100);
 scale_value=0.1f;scale_stamp=105100;weightTick(105100);
 assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
 closingTick(106000);assertStopped();assert(feed_stage==FeedStage::FAULT&&!cat_inspect_required);
 beginManualFeed(107000,"BUTTON_GPIO21");assert(pwm.moving());
 cancel("STOP MID-STROKE",false);before=writes;
 beginManualFeed(107100,"BUTTON_GPIO21");
 assert(cat_inspect_required&&timed_gate_stop==TimedGateStop::UNKNOWN&&writes==before);
 puts("PASS:30 consecutive physical-button sequences OPEN/early-CLOSE/next-OPEN;4s no-mass timeout allows retry after full close; interrupted motion still locks");
 puts("PASS:200 alternating cycles, duplicate same-direction rejection, full UNO pulses/timing, immediate STOP and interruption lock, manual feed cannot bypass inspection");
 puts("PASS:normal measured30g close, close timer not restarted, missing scale block, no fabricated physical closure, millis rollover, PWM failure and ownership guards");
}
'''
(root/'servo_test.cpp').write_text(h,encoding='utf-8')
env=os.environ.copy()
env['ZIG_GLOBAL_CACHE_DIR']=r'D:\Agent_Cat\diagnostics\timed_close_20261103\zig-global-cache'
env['ZIG_LOCAL_CACHE_DIR']=str(root/'zig-local-cache')
with (root/'native_build.log').open('w') as log:
    subprocess.run([r'D:\Agent_Cat\for_cat\.tools-zig\zig-x86_64-windows-0.16.0\zig.exe','c++','-std=c++17','-O0','-nostdlib++','-fno-exceptions','-fno-rtti',str(root/'servo_test.cpp'),'-o',str(root/'servo_test.exe')],env=env,check=True,stdout=log,stderr=log)
r=subprocess.run([str(root/'servo_test.exe')],capture_output=True,text=True,check=True)
(root/'native_test_result.txt').write_text(r.stdout,encoding='utf-8')
print(r.stdout)
assert 'servo_fine_' not in code and 'SERVO_FINE_MS' not in code
print('PASS: fine adjustment removed')
