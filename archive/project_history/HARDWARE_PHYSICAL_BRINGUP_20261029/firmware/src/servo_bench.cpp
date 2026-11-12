#include <Arduino.h>
#include <cstdio>
#include <cstring>
#include "board_config.h"
#include "current_hardware.h"
#include "serial_port.h"
#include "m4/servo_bench.h"
#include "m4/ledc_servo.h"
#include "physical_kit_identity.h"

#ifndef SERVO_BENCH_MODE
#define SERVO_BENCH_MODE 0
#endif

#if SERVO_BENCH_MODE
#if SERVO_BENCH_MODE != 1 || !defined(FORR_REAL_S3_NO_PSRAM) || !defined(FORR_HW_SAFE) || \
    !defined(FORR_BOARD_S3) || defined(SIMULATED_SENSORS) || \
    !defined(FORR_NATIVE_USB) || FORR_NATIVE_USB != 0 || \
    !defined(ARDUINO_USB_CDC_ON_BOOT) || ARDUINO_USB_CDC_ON_BOOT != 0 || \
    ACTUATOR_OUTPUTS_ENABLED != 0 || !defined(SERVO_BENCH_PHYSICAL_ENABLE) || SERVO_BENCH_PHYSICAL_ENABLE != 1 || \
    !defined(PUMP_DIAGNOSTIC_ENABLED) || PUMP_DIAGNOSTIC_ENABLED != 0 || \
    !defined(SERVO_DIAGNOSTIC_ENABLED) || SERVO_DIAGNOSTIC_ENABLED != 0 || \
    (defined(M4_SENSOR_BRINGUP) && M4_SENSOR_BRINGUP) || (defined(M4_DIAGNOSTIC_MODE) && M4_DIAGNOSTIC_MODE)
#error "Servo bench requires the isolated explicit S3 UART0 HW_SAFE profile, never sensors/feed/pump"
#endif
namespace {
m4::LedcServoOutput pwm;
m4::servo_bench::Controller bench(pwm);
char line[96]{};
unsigned used = 0;
bool discard_line = false;
uint32_t sequence = 0;

void result(const char* action, m4::servo_bench::Result code) {
  protocolSerial().printf("SERVO_BENCH seq=%lu action=%s result=%s state=%s pulse_us=%u "
                          "arms=%u moves=%u MECHANICAL_CLOSE_UNVERIFIED\r\n",
                          static_cast<unsigned long>(++sequence), action, m4::servo_bench::name(code),
                          m4::servo_bench::name(bench.state()), bench.pulse(),bench.arms(),bench.moves());
}
void status() {
  physicalKitBanner(protocolSerial(),"diag_servo_bench");
  const auto p=bench.positions();
  protocolSerial().printf("SERVO_BENCH_STATUS mode=EXPLICIT_GPIO6_ONLY state=%s configured=%u "
                          "safe_min_us=%u safe_max_us=%u close_candidate_us=%u open_candidate_us=%u "
                          "output_pulse_us=%u arms=%u/%u moves=%u "
                          "pump_enabled=0 auto_feed_enabled=0 physical_validation=false\r\n",
                          m4::servo_bench::name(bench.state()),bench.configured()?1u:0u,
                          p.safe_min_us,p.safe_max_us,p.close_us,p.open_us,bench.pulse(),
                          bench.arms(),m4::servo_bench::maximum_arms_per_boot,bench.moves());
}
void command(const char* text) {
  if (const char* event=bench.tick(millis()))
    protocolSerial().printf("SERVO_BENCH seq=%lu action=AUTO result=%s state=%s "
                            "MECHANICAL_CLOSE_UNVERIFIED\r\n",
                            static_cast<unsigned long>(++sequence),event,
                            m4::servo_bench::name(bench.state()));
  if (strcmp(text,"servo status")==0) { status(); return; }
  if (strcmp(text,"help")==0) {
    protocolSerial().println("SERVO ONLY: servo status; servo configure MIN_US MAX_US CLOSE_US OPEN_US CONFIRM; "
                             "servo arm YES; servo open; servo set PULSE_US; servo close; servo disarm. "
                              "servo stop = immediate PWM OFF latched FAULT; ONE test movement per arm; <=3 arms per boot; NO FEED/PUMP/AI COMMANDS."); return;
  }
  unsigned a=0,b=0,c=0,d=0; char confirm[8]{}; char extra=0;
  if (strncmp(text,"servo configure",15)==0) {
    const int parsed=sscanf(text,"servo configure %u %u %u %u %7s %c",&a,&b,&c,&d,confirm,&extra);
    if (parsed!=5 || strcmp(confirm,"CONFIRM")!=0 ||
        a>65535 || b>65535 || c>65535 || d>65535) {
      result("CONFIGURE",m4::servo_bench::Result::REJECTED_CONFIG); return;
    }
    result("CONFIGURE",bench.configure({static_cast<uint16_t>(a),static_cast<uint16_t>(b),
                                        static_cast<uint16_t>(c),static_cast<uint16_t>(d)})); return;
  }
  if (strcmp(text,"servo arm YES")==0) { result("ARM",bench.arm(millis())); return; }
  if (strcmp(text,"servo open")==0) { result("OPEN",bench.open(millis())); return; }
  if (strncmp(text,"servo set",9)==0) {
    if (sscanf(text,"servo set %u %c",&a,&extra)!=1 || a>65535) {
      result("SET",m4::servo_bench::Result::REJECTED_POSITION); return;
    }
    result("SET",bench.move(static_cast<uint16_t>(a),millis())); return;
  }
  if (strcmp(text,"servo close")==0) { result("CLOSE",bench.close(millis())); return; }
   if (strcmp(text,"servo disarm")==0) { result("DISARM",bench.disarm(millis())); return; }
   if (strcmp(text,"servo stop")==0) { result("STOP_PWM_OFF_LATCHED",bench.emergencyStop()); return; }
  protocolSerial().printf("SERVO_BENCH seq=%lu action=UNKNOWN result=REJECTED_UNKNOWN_COMMAND "
                          "state=%s\r\n",static_cast<unsigned long>(++sequence),
                          m4::servo_bench::name(bench.state()));
}
void commands() {
  unsigned consumed=0;
  while (consumed++<32 && protocolSerial().available()>0) {
    const int incoming=protocolSerial().read();
    if (incoming=='\r' || incoming=='\n') {
      if (!discard_line && used) { line[used]=0; command(line); }
      used=0; discard_line=false;
    } else if (incoming>=32 && incoming<=126 && !discard_line) {
      if (used+1<sizeof(line)) line[used++]=static_cast<char>(incoming);
      else { used=0; discard_line=true; }
    } else { used=0; discard_line=true; }
  }
}
} // namespace

void setup() {
  pwm.off(); // GPIO6 LOW, no PWM before UART/config/manual arm
  bench.boot();
   protocolSerial().begin(115200);
   physicalKitBanner(protocolSerial(),"diag_servo_bench");
  protocolSerial().println("SERVO BENCH ONLY GPIO6 PWM_OFF DISARMED. "
                           "GPIO7 PUMP UNTOUCHED. NO AUTO/CAT/WEB/FOOD. "
                           "Use unloaded mechanism, independent 5V servo and common GND. "
                           "CLOSE/OPEN physical positions NOT CALIBRATED.");
  status();
}
void loop() {
  if (const char* event=bench.tick(millis()))
    protocolSerial().printf("SERVO_BENCH seq=%lu action=AUTO result=%s state=%s "
                            "MECHANICAL_CLOSE_UNVERIFIED\r\n",
                            static_cast<unsigned long>(++sequence),event,
                            m4::servo_bench::name(bench.state()));
  commands();
  delay(1);
}
#endif
