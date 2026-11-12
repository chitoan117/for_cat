#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
namespace std {using ::strcmp;}
namespace current_hardware {constexpr int PUMP_CONTROL=7;}
constexpr int LOW=0,HIGH=1,OUTPUT=1;
int pin=0; void digitalWrite(int p,int v){assert(p==7);pin=v;} void pinMode(int,int){}
struct Serial {void print(const char*){}} serial;
Serial& protocolSerial(){return serial;}
struct Pwm {bool active=false;bool moving(){return active;}} pwm;
enum class BenchCal {Idle,Busy}; BenchCal bench_cal=BenchCal::Idle;
namespace pump_bench {
bool running=false;
uint32_t started=0;
constexpr uint32_t TEST_MS=1000;
void off() {
  digitalWrite(current_hardware::PUMP_CONTROL,LOW);
  running=false;
}
void begin() {
  // PCB PC817 LED -> PMOS: HIGH=ON, LOW=OFF. No pump run on startup.
  digitalWrite(current_hardware::PUMP_CONTROL,LOW);
  pinMode(current_hardware::PUMP_CONTROL,OUTPUT);
  off();
}
void tick(uint32_t now) {
  if(running && uint32_t(now-started)>=TEST_MS) {
    off(); protocolSerial().print("PUMP TEST DONE: GPIO7 LOW/OFF after1000ms.\n");
  }
}
bool command(const char* line,uint32_t now) {
  if(!std::strcmp(line,"pump_off")) { off(); protocolSerial().print("PUMP OFF GPIO7 LOW.\n"); return true; }
  if(std::strcmp(line,"pump_test")) return false;
  if(running) { protocolSerial().print("PUMP TEST BUSY: timer not extended.\n"); return true; }
  if(pwm.moving() || bench_cal!=BenchCal::Idle) { protocolSerial().print("PUMP TEST BLOCKED: actuator/calibration busy.\n"); return true; }
  started=now; running=true;
  digitalWrite(current_hardware::PUMP_CONTROL,HIGH);
  protocolSerial().print("PUMP TEST START: GPIO7 HIGH/ON max1000ms, supervised test only.\n");
  return true;
}
}


int main(){using namespace pump_bench;
begin();assert(pin==0&&!running);
command("pump_test",100);assert(pin==1&&running);
command("pump_test",800);tick(1099);assert(pin==1&&running);tick(1100);assert(pin==0&&!running);
command("pump_test",2000);command("pump_off",2001);assert(pin==0&&!running);
command("pump_test",0xfffffff0u);tick(983);assert(running);tick(984);assert(!running&&pin==0);
pwm.active=true;command("pump_test",3000);assert(!running&&pin==0);pwm.active=false;
bench_cal=BenchCal::Busy;command("pump_test",3000);assert(!running&&pin==0);
assert(!command("pump_test 999999",3000));
puts("PASS: startup OFF, fixed1s stop, duplicates cannot extend, manual stop, rollover, busy/calibration blocks, rejects extended duration.");
}
