from pathlib import Path
import os,subprocess
r=Path(__file__).parent
s=(r/'esp32/esp32.ino').read_text();a=s.index('namespace pump_bench {');b=s.index('// D1=bowl, D2=reservoir.',a)
h='''#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
namespace std {using ::strcmp;using ::strncmp;using ::sscanf;}
namespace current_hardware {constexpr int PUMP_CONTROL=7;}
constexpr int LOW=0,HIGH=1,OUTPUT=1;
int pin=0; void digitalWrite(int p,int v){assert(p==7);pin=v;} void pinMode(int,int){}
struct Serial {void print(const char*){} template<typename... T> void printf(const char*,T...){}} serial;
Serial& protocolSerial(){return serial;}
struct Pwm {bool active=false;bool moving(){return active;}} pwm;
enum class BenchCal {Idle,Busy}; BenchCal bench_cal=BenchCal::Idle;
'''+s[a:b]+'''
int main(){using namespace pump_bench;
begin();assert(pin==0&&!running);
command("pump_test",100);assert(pin==1&&running);
command("pump_test",800);tick(10099);assert(pin==1&&running);tick(10100);assert(pin==0&&!running);
command("pump_test",2000);command("pump_off",2001);assert(pin==0&&!running);
command("pump_test",0xfffffff0u);tick(9983);assert(running);tick(9984);assert(!running&&pin==0);
pwm.active=true;command("pump_test",3000);assert(!running&&pin==0);pwm.active=false;
command("pump_test 2000",4000);assert(running);tick(5999);assert(running);tick(6000);assert(!running);
command("pump_test 4000",7000);command("pump_test 9000",8000);tick(10999);assert(running);tick(11000);assert(!running);
command("pump_test 99",12000);assert(!running);command("pump_test 10001",12000);assert(!running);
command("pump_test -1",12000);assert(!running);command("pump_test 2000 extra",12000);assert(!running);
bench_cal=BenchCal::Busy;command("pump_test",3000);assert(!running&&pin==0);
assert(command("pump_test 999999",3000));assert(!running);
puts("PASS: startup OFF, fixed10s stop, duplicates cannot extend, manual stop, rollover, busy/calibration blocks, rejects extended duration.");
}
'''
(r/'test_bench.cpp').write_text(h)
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']='D:/Agent_Cat/diagnostics/timed_close_20261103/zig-global-cache';env['ZIG_LOCAL_CACHE_DIR']=str(r/'zig-cache')
subprocess.run(['D:/Agent_Cat/for_cat/.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++17','-nostdlib++','-fno-exceptions','-fno-rtti',str(r/'test_bench.cpp'),'-o',str(r/'test_bench.exe')],env=env,check=True)
result=subprocess.run([str(r/'test_bench.exe')],capture_output=True,text=True,check=True)
(r/'test_result.txt').write_text(result.stdout);print(result.stdout)
