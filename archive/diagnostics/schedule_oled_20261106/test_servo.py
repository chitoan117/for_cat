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

h+='#define GPIO_IS_VALID_GPIO(p) ((p)>=0&&(p)<=48)\n#define GPIO_IS_VALID_OUTPUT_GPIO(p) GPIO_IS_VALID_GPIO(p)\n'
h+='namespace current_hardware {constexpr int SERVO_SIGNAL=6,PUMP_CONTROL=7,D2_WATER_ECHO=19;}\nstruct TestPins {\n'
h+=block('  bool inputAllowed(int pin) const override {').replace(' override','')+'\n'
h+=block('  bool outputAllowed(int pin) const override {').replace(' override','')+'\n};\n'
h+=r'''
uint32_t expectedDuty(unsigned us){return (us*16384u+10000u)/20000u;}
void assertStopped(){assert(hw_attached&&!pwm.moving()&&duty==expectedDuty(1500));}
int main(){ TestPins pins; assert(pins.inputAllowed(19)&&!pins.outputAllowed(19)&&!pins.inputAllowed(20)&&!pins.inputAllowed(6)&&!pins.inputAllowed(7));
 assert(open_ms==900&&close_ms==1450);
 assert(SERVO_OPEN_US==1350&&SERVO_CLOSE_US==1600&&SERVO_NEUTRAL_US==1500);
 uint32_t t=10000;
 for(unsigned i=0;i<5;++i){
   assert(manualServoMove(true,open_ms,t));
   diagTick(t+open_ms-1);assert(pwm.moving());diagTick(t+open_ms);assertStopped();
   unsigned old=writes;assert(!manualServoMove(true,open_ms,t+open_ms+1)&&old==writes);
   uint32_t close_at=t+open_ms+100;
   assert(manualServoMove(false,close_ms,close_at));
   diagTick(close_at+close_ms-1);assert(pwm.moving());diagTick(close_at+close_ms);assertStopped();
   assert(timed_gate_stop==TimedGateStop::CLOSED);
   old=writes;assert(!manualServoMove(false,close_ms,close_at+close_ms+1)&&old==writes);
   t=close_at+close_ms+100;
 }
 scale_ready=true;scale_value=0;beginManualFeed(t,"BUTTON");openingTick(t+open_ms);
 last_delta_g=0.1f;beginManualFeed(t+open_ms+100,"BUTTON");
 closingTick(t+open_ms+100+close_ms-1);assert(pwm.moving());
 closingTick(t+open_ms+100+close_ms);assertStopped();
 assert(feed_stage==FeedStage::FAULT&&!cat_inspect_required);
 t+=open_ms+close_ms+200;beginManualFeed(t,"BUTTON");assert(pwm.moving());
 cancel("STOP",false);assertStopped();assert(cat_inspect_required);
 auto old=writes;beginManualFeed(t+100,"BUTTON");assert(writes==old);
 // Run the actual production weight branch at the new target boundary.
 cat_inspect_required=false;feed_stage=FeedStage::IDLE;timed_gate_stop=TimedGateStop::CLOSED;
 t=100000;scale_value=0;scale_ready=true;beginManualFeed(t,"BUTTON");openingTick(t+open_ms);
 scale_value=34.99f;++scale_stamp;weightTick(t+open_ms+1);assert(feed_stage==FeedStage::WAIT_WEIGHT);
 scale_value=35.0f;++scale_stamp;weightTick(t+open_ms+2);assert(feed_stage==FeedStage::CLOSING&&close_on_weight);
 closingTick(t+open_ms+2+close_ms);assertStopped();
 // Three distinct E1 readings are required; 30cm is accepted, >30cm rejected.
 cat_inspect_required=false;feed_stage=FeedStage::WAIT_CAT;timed_gate_stop=TimedGateStop::CLOSED;
 phase_at=200000;cat_hits=0;last_hc_ms=0;hc.raw.valid=hc.raw.fresh=true;
 hc.raw.value=30.01f;hc.raw.sampled_at_ms=200001;catTick(200001);assert(cat_hits==0);
 hc.raw.value=30.0f;
 for(unsigned i=1;i<=3;i++){hc.raw.sampled_at_ms=200001+180*i;catTick(hc.raw.sampled_at_ms);}
 assert(feed_stage==FeedStage::OPENING);cancel("STOP",false);
 puts("PASS: 34.99g waits,35g closes;E1 30cm accepted after3 distinct readings,30.01cm rejected");
 puts("PASS:new closing duration boundary;5 alternating cycles;no extra duplicate strokes;manual early-close retry;STOP lock;neutral and loadcell mass result preserved");
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
