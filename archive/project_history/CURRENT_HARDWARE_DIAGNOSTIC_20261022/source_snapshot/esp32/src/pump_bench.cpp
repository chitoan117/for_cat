#include <Arduino.h>
#include <cstdio>
#include <cstring>
#include "board_config.h"
#include "current_hardware.h"
#include "serial_port.h"
#include "m4/actuator_interfaces.h"
#include "m4/pump_bench.h"

#if PUMP_BENCH_MODE
static_assert(current_hardware::PUMP_CONTROL==7,"current pump wiring");
namespace {
class PumpOutput final : public m4::PumpInterface {
 public:
  bool initialize(m4::Pin pin) override {
    if (!pin.reviewed || pin.number!=current_hardware::PUMP_CONTROL || initialized_) return false;
#if PUMP_BENCH_PHYSICAL_ENABLE
    // Actual boot/reset OFF depends ALSO on the module's external input bias;
    // firmware cannot control GPIO until setup starts. Verify module physically.
    digitalWrite(pin.number,PUMP_BENCH_OFF_LEVEL?HIGH:LOW);
    pinMode(pin.number,OUTPUT);
    digitalWrite(pin.number,PUMP_BENCH_OFF_LEVEL?HIGH:LOW);
#endif
    initialized_=true;return true;
  }
  bool requestOn(uint32_t,uint32_t) override {
    if (!initialized_ || !PUMP_BENCH_PHYSICAL_ENABLE) return false;
#if PUMP_BENCH_PHYSICAL_ENABLE
    digitalWrite(current_hardware::PUMP_CONTROL,PUMP_BENCH_OFF_LEVEL?LOW:HIGH);
#endif
    commanded_on_=true;return true;
  }
  m4::Status health() const override {
    return initialized_?m4::Status{m4::Health::INITIALIZING,m4::Reason::NONE}:m4::Status{};
  }
  void off() override {
#if PUMP_BENCH_PHYSICAL_ENABLE
    if (initialized_) digitalWrite(current_hardware::PUMP_CONTROL,PUMP_BENCH_OFF_LEVEL?HIGH:LOW);
#endif
    commanded_on_=false; // GPIO command is NOT a measured motor/off feedback
  }
  bool commandedOn() const {return commanded_on_;}
 private:
  bool initialized_=false,commanded_on_=false;
};
PumpOutput output;
class PumpPolicyIO final : public m4::pump_bench::Output {
 public:
  explicit PumpPolicyIO(PumpOutput& driver):driver_(driver) {}
  bool on() override { return driver_.requestOn(0,500); }
  bool off() override { driver_.off();return true; }
 private:
  PumpOutput& driver_;
};
PumpPolicyIO policy_io(output);
m4::pump_bench::Controller controller(policy_io);
char command_line[96]{};
unsigned used=0;
bool discard=false;
uint32_t sequence=0;

void status() {
  protocolSerial().printf("PUMP_BENCH_STATUS mode=%s GPIO7_off_level=%d state=%s armed=%u "
      "commanded_on=%u pulses=%u/3 max_on_ms=500 servo_pwm=OFF auto_water=OFF "
      "water_AI=UNUSED physical_pump_off_verified=false\r\n",
      PUMP_BENCH_PHYSICAL_ENABLE?"POLARITY_SPECIFIC_SUPERVISED":"INERT_UNKNOWN_POLARITY",
      PUMP_BENCH_OFF_LEVEL,m4::pump_bench::name(controller.state()),
      controller.state()==m4::pump_bench::State::ARMED?1u:0u,
      output.commandedOn()?1u:0u,controller.pulses());
}
void result(const char* action,m4::pump_bench::Result code) {
  protocolSerial().printf("PUMP_BENCH seq=%lu action=%s result=%s state=%s "
      "commanded_on=%u pulses=%u physical_off_verified=false\r\n",
      static_cast<unsigned long>(++sequence),action,m4::pump_bench::name(code),
      m4::pump_bench::name(controller.state()),output.commandedOn()?1u:0u,controller.pulses());
}
void command(const char* text) {
  if (strcmp(text,"pump status")==0) {status();return;}
  if (strcmp(text,"help")==0) {
    protocolSerial().println("PUMP BENCH ONLY: pump status; pump arm YES; pump on MS; "
      "pump off; pump disarm. Initial max500ms, 3 pulses per boot, 1s cooldown. "
      "Active variant requires physically VERIFIED F5305S polarity and boot OFF bias.");return;
  }
  if (strcmp(text,"pump arm YES")==0) {
    result("ARM",PUMP_BENCH_PHYSICAL_ENABLE?
        controller.arm(millis()):m4::pump_bench::Result::REJECTED_DISARMED);return;
  }
  if (strncmp(text,"pump on",7)==0) {
    unsigned duration=0;char extra=0;
    if (sscanf(text,"pump on %u %c",&duration,&extra)!=1 || duration>500) {
      result("ON",m4::pump_bench::Result::REJECTED_DURATION);return;
    }
    result("ON",PUMP_BENCH_PHYSICAL_ENABLE?
        controller.pulse(millis(),duration):m4::pump_bench::Result::REJECTED_DISARMED);return;
  }
  if (strcmp(text,"pump off")==0) {result("OFF",controller.stop(millis()));return;}
  if (strcmp(text,"pump disarm")==0) {result("DISARM",controller.stop(millis()));return;}
  result("UNKNOWN",m4::pump_bench::Result::REJECTED_DURATION);
}
void commands() {
  unsigned processed=0;
  while (processed++<32 && protocolSerial().available()>0) {
    const int byte=protocolSerial().read();
    if (byte=='\r' || byte=='\n') {
      if (!discard && used) {command_line[used]=0;command(command_line);}
      used=0;discard=false;
    } else if (byte>=32 && byte<=126 && !discard) {
      if (used+1<sizeof(command_line)) command_line[used++]=static_cast<char>(byte);
      else {used=0;discard=true;}
    } else {used=0;discard=true;}
  }
}
} // namespace
void setup() {
  output.initialize({current_hardware::PUMP_CONTROL,true});
  controller.boot();
  protocolSerial().begin(115200);
  protocolSerial().println("PUMP BENCH ONLY. SERVO6 UNTOUCHED NO CAT/AUTO_WATER. "
    "NO PHYSICAL OFF PROOF. DISCONNECT PUMP 5V UNTIL F5305S IN POLARITY/IDLE BIAS VERIFIED.");
  status();
}
void loop() {
  if (controller.tick(millis()))
    result("AUTO_TIMEOUT_OFF",m4::pump_bench::Result::ACCEPTED);
  commands();
  delay(1);
}
#endif
