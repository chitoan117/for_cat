from pathlib import Path
import subprocess
import os

root = Path(__file__).parent
code = (root/'esp32/esp32.ino').read_text(encoding='utf-8')
def block(marker):
    start = code.index(marker)
    begin = code.index('{',start)
    depth = 1
    i = begin + 1
    while depth:
        if code[i] == '{': depth += 1
        elif code[i] == '}': depth -= 1
        i += 1
    return code[start:i]

harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
namespace std { using ::strtol; }
enum class FeedStage { IDLE, FAULT, OPENING, WAIT_WEIGHT, CLOSING, DIAG_OPEN, DIAG_CLOSE, DONE };
constexpr bool USE_CLOSE_LIMIT_SWITCH=false;
constexpr int LOW=0, PIN_CLOSE_LIMIT=47;
constexpr uint16_t SERVO_NEUTRAL_US=1500, SERVO_CLOSE_US=1700;
constexpr uint32_t MAX_SERVO_ACTIVE_MS=5000;
unsigned reads=0;
int digitalRead(int) { ++reads; return LOW; }
struct Serial { template<class... T> void printf(const char*,T...){} void print(const char*){} } serial;
Serial& protocolSerial(){return serial;}
struct Pwm {
  bool on=false; unsigned writes=0,stops=0; uint16_t pulse=0;
  bool attached(){return on;}
  bool start(uint16_t us){on=true; pulse=us; return true;}
  bool write(uint16_t us){++writes; pulse=us; return true;}
  bool off(){++stops;on=false;return true;}
} pwm;
FeedStage feed_stage=FeedStage::IDLE;
bool manual_feed_active=false, close_on_weight=false, limit_closed=true;
bool physical_closed_verified=false,cat_inspect_required=false,servo_armed=false;
bool meal_logged=false,meal_start_locked=false;
float last_delta_g=35,meal_starting_g=0,meal_remaining_g=0,meal_consumed_g=0;
float meal_plateau_ref_g=0,meal_stable_ref_g=0;
const char* meal_preference="NONE";
uint32_t meal_plateau_since=0,meal_closed_at=0,meal_stable_since=0,phase_at=0;
uint16_t open_ms=550,close_ms=4000;
unsigned cat_hits=0;
char current_food='A';
bool busy(){ return feed_stage!=FeedStage::IDLE && feed_stage!=FeedStage::FAULT && feed_stage!=FeedStage::DONE; }
'''
harness += block('void neutralMotor() {')+'\n'+block('void cancel(const char* reason, bool error) {')+'\n'
harness += block('void startClose(uint32_t now, bool by_weight)')+'\n'
harness += 'void closingTick(uint32_t now) {\n'+block('  if (feed_stage == FeedStage::CLOSING) {')+'\n}\n'
harness += 'void diagTick(uint32_t now) {\n'+block('  if (feed_stage == FeedStage::DIAG_OPEN || feed_stage == FeedStage::DIAG_CLOSE) {')+'\n}\n'
harness += block('bool setMotionTime(const char* text, bool opening)')+'\n'
harness += r'''
int main(){
  // LOW/disconnected GPIO47 must have no influence on timed motion.
  startClose(100,true);
  assert(pwm.on && pwm.pulse==1700 && feed_stage==FeedStage::CLOSING);
  closingTick(4099); assert(pwm.on && feed_stage==FeedStage::CLOSING);
  closingTick(4100); assert(!pwm.on && feed_stage==FeedStage::DONE);
  assert(!physical_closed_verified && !cat_inspect_required && reads==0);
  // A close requested after HX failure remains a fault requiring inspection.
  startClose(5000,false); closingTick(9000);
  assert(!pwm.on && feed_stage==FeedStage::FAULT && cat_inspect_required);
  // millis rollover cannot stop early or run past the configured interval.
  startClose(UINT32_MAX-100,true);
  closingTick(3898); assert(pwm.on);
  closingTick(3899); assert(!pwm.on);
  // Stop interrupts motion immediately rather than waiting for its timer.
  startClose(12000,true); cancel("STOP",false);
  assert(!pwm.on && feed_stage==FeedStage::IDLE && cat_inspect_required);
  // Diagnostic motion uses the selected duration in each direction.
  pwm.start(1700); feed_stage=FeedStage::DIAG_CLOSE; phase_at=0;
  diagTick(3999); assert(pwm.on); diagTick(4000); assert(!pwm.on);
  pwm.start(1300); feed_stage=FeedStage::DIAG_OPEN; phase_at=0;
  diagTick(549); assert(pwm.on); diagTick(550); assert(!pwm.on);
  // Timing edits require idle state, valid integer syntax, and bounded values.
  assert(!setMotionTime("99",false)); assert(!setMotionTime("5001",false));
  assert(!setMotionTime("550junk",false)); assert(!setMotionTime("",false));
  assert(setMotionTime("550",false) && close_ms==550);
  startClose(20000,true); assert(!setMotionTime("1000",false));
  cancel("STOP",false); assert(setMotionTime("5000",false));
  assert(reads==0);
  puts("PASS: timed close, GPIO47 isolation, HX failure, rollover, stop, diagnostics, timing bounds");
}
'''
(root/'timed_close_test.cpp').write_text(harness,encoding='utf-8')
env=os.environ.copy()
env['ZIG_GLOBAL_CACHE_DIR']=str(root/'zig-global-cache')
env['ZIG_LOCAL_CACHE_DIR']=str(root/'zig-local-cache')
with (root/'native_build.log').open('w') as log:
    subprocess.run([r'D:\Agent_Cat\for_cat\.tools-zig\zig-x86_64-windows-0.16.0\zig.exe','c++','-std=c++17','-O0','-nostdlib++','-fno-exceptions','-fno-rtti',str(root/'timed_close_test.cpp'),'-o',str(root/'timed_close_test.exe')],env=env,check=True,stdout=log,stderr=log)
result=subprocess.run([str(root/'timed_close_test.exe')],capture_output=True,text=True,check=True)
print(result.stdout)
(root/'native_test_result.txt').write_text(result.stdout,encoding='utf-8')
