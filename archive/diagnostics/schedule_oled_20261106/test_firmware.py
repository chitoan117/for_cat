from pathlib import Path
import subprocess,os
r=Path(__file__).parent
base=Path('D:/Agent_Cat/diagnostics/servo_fast_20261106/balanced/test_servo.py').read_text()
(r/'test_servo.py').write_text(base)
subprocess.run(['python',str(r/'test_servo.py')],check=True)
s=(r/'esp32/esp32.ino').read_text()
def block(marker):
 a=s.index(marker);b=s.index('{',a);n=1;e=b+1
 while n:
  if s[e]=='{':n+=1
  if s[e]=='}':n-=1
  e+=1
 return s[a:e]
h=(r/'servo_test.cpp').read_text().split('int main(){')[0]
old='struct Serial { template<class... T> void printf(const char*,T...){} void print(const char*){} } serial;'
assert old in h
h=h.replace(old,'''#include <string.h>
#include <stdarg.h>
char uart_log[16000];size_t uart_n=0;
struct Serial { void printf(const char* fmt,...){va_list args;va_start(args,fmt);uart_n+=vsnprintf(uart_log+uart_n,sizeof(uart_log)-uart_n,fmt,args);va_end(args);} void print(const char* s){printf("%s",s);} } serial;
''')
h+='''
namespace std {using ::strlen;using ::strcmp;using ::strncmp;using ::strncpy;using ::memchr;}
unsigned char nv[4096];size_t nv_size=0;bool fail_nv=false;
class Preferences {public:bool begin(const char*,bool){return true;}size_t getBytesLength(const char*){return nv_size;}
size_t getBytes(const char*,void* out,size_t n){memcpy(out,nv,n);return n;}
size_t putBytes(const char*,const void* in,size_t n){if(fail_nv)return 0;memcpy(nv,in,n);nv_size=n;return n;}};
namespace bench_v8 {using ::busy;using ::dog_running;using ::demo_exited;using ::cat_inspect_required;using ::timed_gate_stop;using ::TimedGateStop;
using ::benchScaleSample;using ::beginManualFeed;using ::feed_stage;using ::FeedStage;using ::manual_feed_active;using ::last_delta_g;}
'''
h+=(r/'mcu_schedule.inc').read_text()
h+='\nchar ai_species=\'N\';uint32_t ai_species_ms=0;constexpr uint32_t AI_DISPLAY_HOLD_MS=4000;\n'+block('const char* oledAiLineText(uint32_t now) {')
h+='''
void clearLog(){uart_n=0;uart_log[0]=0;}
int main(){
 scale_ready=true;scale_value=0;timed_gate_stop=TimedGateStop::CLOSED;
 clearLog();assert(scheduled_feed_v1::command("feed_once schedule_one",10000));
 assert(feed_stage==FeedStage::OPENING&&!manual_feed_active&&strstr(uart_log,"ACCEPTED")&&nv_size>0);
 unsigned previous=writes;clearLog();scheduled_feed_v1::command("feed_once schedule_one",10001);
 assert(writes==previous&&strstr(uart_log,"DUPLICATE"));
 clearLog();scheduled_feed_v1::command("feed_once schedule_two",10002);assert(writes==previous&&strstr(uart_log,"BUSY"));
 openingTick(10900);scale_stamp=15400;weightTick(15400);assert(feed_stage==FeedStage::WAIT_WEIGHT);
 scale_value=35;scale_stamp=15401;weightTick(15401);assert(feed_stage==FeedStage::CLOSING);
 closingTick(15401+1450);assert(feed_stage==FeedStage::DONE);clearLog();scheduled_feed_v1::tick();assert(strstr(uart_log,"WEIGHT_REACHED"));
 scheduled_feed_v1::loaded=false;scheduled_feed_v1::storage_ok=false;scheduled_feed_v1::history={};feed_stage=FeedStage::IDLE;
 previous=writes;clearLog();scheduled_feed_v1::command("feed_once schedule_one",20000);assert(writes==previous&&strstr(uart_log,"DUPLICATE"));
 scale_ready=false;clearLog();scheduled_feed_v1::command("feed_once schedule_two",20001);assert(writes==previous&&strstr(uart_log,"HX_NOT_READY"));
 scale_ready=true;fail_nv=true;clearLog();scheduled_feed_v1::command("feed_once schedule_two",20002);assert(writes==previous&&strstr(uart_log,"STORAGE_WRITE_FAILED"));fail_nv=false;
 cat_inspect_required=true;clearLog();scheduled_feed_v1::command("feed_once schedule_two",20003);assert(writes==previous&&strstr(uart_log,"INSPECTION_REQUIRED"));cat_inspect_required=false;
 clearLog();scheduled_feed_v1::command("feed_once bad/id",20004);assert(writes==previous&&strstr(uart_log,"INVALID_ID"));
 ai_species='N';feed_stage=FeedStage::OPENING;dog_running=true;assert(!strcmp(oledAiLineText(30000),"FAIL"));
 ai_species='C';ai_species_ms=30000;assert(!strcmp(oledAiLineText(30001),"CAT"));assert(!strcmp(oledAiLineText(34001),"FAIL"));
 ai_species='D';assert(!strcmp(oledAiLineText(30001),"DOG"));ai_species_ms=0xfffffff0u;assert(!strcmp(oledAiLineText(20),"DOG"));
 puts("PASS:scheduled ACK,durable duplicate across reboot,busy,HX,storage,inspection gates,25s weight path;OLED real CAT/DOG/FAIL/expiry/rollover");
}
'''
(r/'scheduled_native.cpp').write_text(h)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']='D:/Agent_Cat/diagnostics/timed_close_20261103/zig-global-cache';env['ZIG_LOCAL_CACHE_DIR']=str(r/'zig-local-cache')
with (r/'scheduled_native_build.log').open('w') as log:
 subprocess.run(['D:/Agent_Cat/for_cat/.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++17','-O0','-nostdlib++','-fno-exceptions','-fno-rtti',str(r/'scheduled_native.cpp'),'-o',str(r/'scheduled_native.exe')],check=True,env=env,stdout=log,stderr=log)
result=subprocess.run([str(r/'scheduled_native.exe')],capture_output=True,text=True,check=True)
(r/'scheduled_native_result.txt').write_text(result.stdout);print(result.stdout)
