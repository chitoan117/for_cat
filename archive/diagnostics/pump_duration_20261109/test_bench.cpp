#include <stdint.h>
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
namespace pump_bench {
bool running=false;
uint32_t started=0;
constexpr uint32_t MAX_TEST_MS=10000;
uint32_t test_duration=MAX_TEST_MS;
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
  if(running && uint32_t(now-started)>=test_duration) {
    off(); protocolSerial().printf("PUMP TEST DONE: GPIO7 LOW/OFF after%lums.\n",(unsigned long)test_duration);
  }
}
bool command(const char* line,uint32_t now) {
  if(!std::strcmp(line,"pump_off")) { off(); protocolSerial().print("PUMP OFF GPIO7 LOW.\n"); return true; }
  const bool default_test=!std::strcmp(line,"pump_test");
  if(!default_test && std::strncmp(line,"pump_test ",10)) return false;
  unsigned long requested=MAX_TEST_MS;char extra;
  if(!default_test && (std::sscanf(line+10,"%lu %c",&requested,&extra)!=1 || requested<100 || requested>MAX_TEST_MS)) {
    protocolSerial().print("PUMP TEST INVALID:100..10000ms required.\n");return true;
  }
  if(running) { protocolSerial().print("PUMP TEST BUSY: timer not extended.\n"); return true; }
  if(pwm.moving() || bench_cal!=BenchCal::Idle) { protocolSerial().print("PUMP TEST BLOCKED: actuator/calibration busy.\n"); return true; }
  test_duration=(uint32_t)requested;
  started=now; running=true;
  digitalWrite(current_hardware::PUMP_CONTROL,HIGH);
  protocolSerial().printf("PUMP TEST START: GPIO7 HIGH/ON max%lums, supervised test only.\n",requested);
  return true;
}
}


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
