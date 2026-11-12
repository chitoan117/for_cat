// Actual isolated servo-bench setup/loop and parser with host PWM, never a board.
#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define SERVO_DIAGNOSTIC_ENABLED 0
#define PUMP_DIAGNOSTIC_ENABLED 0
#define SERVO_BENCH_MODE 1
#define SERVO_BENCH_PHYSICAL_ENABLE 1
#include "../src/servo_bench.cpp"
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace hw = host_board;
namespace {
unsigned assertions=0;
void expect(bool ok,const char* text) { ++assertions; if (!ok) throw std::runtime_error(text); }
void run(uint32_t ms) {
  const auto until=hw::now_us+static_cast<uint64_t>(ms)*1000u;
  unsigned count=0;
  while (hw::now_us<until || !Serial0.rx.empty()) {
    if (++count>2000000) throw std::runtime_error("host tick budget");
    loop();
  }
}
void send(const std::string& text) { Serial0.input(text+"\n"); run(2); }
void checks() {
  expect(hw::touches[7]==0 && hw::touches[4]==0 && hw::touches[5]==0,"pump/HX GPIO accessed");
  for (int pin: {8,9,10,11,12,13,14,15,16,17,18})
    expect(hw::touches[static_cast<size_t>(pin)]==0,"other sensor GPIO accessed");
  expect(!hw::ledc_attached && hw::ledc_duty==0,"PWM still attached after test");
  expect(!hw::levels[6],"servo signal did not settle LOW");
  expect(Serial0.tx.find("pump_enabled=0 auto_feed_enabled=0")!=std::string::npos,"status lacks safety distinction");
}
void cold_and_limits() {
  setup();
  expect(bench.state()==m4::servo_bench::State::DISARMED && hw::ledc_attaches==0,"boot attached PWM");
  send("servo status"); send("servo open"); send("servo set 1530"); send("servo close");
  send("servo arm YES");
  expect(hw::ledc_attaches==0 && Serial0.tx.find("REJECTED_NOT_ARMED")!=std::string::npos,
         "disarmed attempt moved servo");
  send("servo configure 1000 1200 1100 1150 CONFIRM");
  send("servo configure 1450 1550 1500 1500 CONFIRM");
  send("servo configure 1450 1550 1500 1530 UNKNOWN");
  send("servo configure 1450 1550 1500 1530 CONFIRM x");
  expect(!bench.configured() && hw::ledc_attaches==0,"invalid config enabled motion");
  send("servo configure 1450 1550 1500 1530 CONFIRM");
  expect(bench.configured() && hw::ledc_attaches==0,"configure generated PWM");
  send("servo configure 1450 1550 1500 1530 CONFIRM");
  expect(Serial0.tx.find("REJECTED_BUSY")!=std::string::npos,"configuration replay not rejected");
  send("servo arm YES");
  expect(hw::ledc_attaches==1 && hw::ledc_attached && bench.state()==m4::servo_bench::State::ARMED,
         "explicit arm did not attach at candidate close");
  expect(hw::ledc_duty==(1500u*65536u+10000u)/20000u,"incorrect 50Hz duty");
  send("servo set 1551"); send("servo set 1000"); send("servo set 1500");
  expect(bench.moves()==0 && hw::ledc_attached,"out-of-window set moved servo");
  send("servo open"); send("servo open");
  expect(bench.moves()==1 && bench.state()==m4::servo_bench::State::MOVING,"multiple moves per arm");
  run(255);
  expect(bench.state()==m4::servo_bench::State::CLOSING && hw::ledc_attached,
         "open did not auto return to candidate close");
  send("servo open");
  run(355);
  expect(bench.state()==m4::servo_bench::State::DISARMED && !hw::ledc_attached,"close hold not detached");
  send("servo disarm"); send("servo open");
  checks();
}
void arm_expiry_and_budget() {
  setup(); send("servo configure 1460 1540 1500 1520 CONFIRM");
  send("servo arm YES"); run(2100);
  expect(bench.state()==m4::servo_bench::State::CLOSING,"arm timeout did not return to reference");
  run(360); expect(bench.state()==m4::servo_bench::State::DISARMED,"arm timeout failed to detach");
  send("servo arm YES"); send("servo set 1490"); send("servo close");
  expect(bench.state()==m4::servo_bench::State::CLOSING,"manual close not bounded");
  run(360);
  send("servo arm YES"); send("servo disarm"); run(360);
  expect(bench.arms()==3 && bench.moves()==1,"wrong arm budget");
  send("servo arm YES");
  expect(bench.state()==m4::servo_bench::State::DISARMED && hw::ledc_attaches==3 &&
         Serial0.tx.find("REJECTED_LIMIT")!=std::string::npos,"fourth arm allowed");
  checks();
}
void output_faults() {
  setup(); send("servo configure 1470 1530 1500 1520 CONFIRM");
  hw::ledc_fail_attach=true; send("servo arm YES");
  expect(bench.state()==m4::servo_bench::State::FAULT && !hw::ledc_attached,"failed attach not latched");
  send("servo arm YES"); expect(hw::ledc_attaches==1,"fault allowed rearm");
  checks();
}
void write_fault_and_hard_deadline() {
  setup(); send("servo configure 1470 1530 1500 1520 CONFIRM");
  send("servo arm YES"); hw::ledc_fail_write=true;
  send("servo open");
  expect(bench.state()==m4::servo_bench::State::FAULT && !hw::ledc_attached,"PWM write fault still active");
  checks();
}
void hard_deadline() {
  setup(); send("servo configure 1470 1530 1500 1520 CONFIRM"); send("servo arm YES");
  send("servo open");
  hw::now_us+=3100000; loop();
  expect(bench.state()==m4::servo_bench::State::FAULT && !hw::ledc_attached,
         "stalled loop failed closed after deadline");
  expect(Serial0.tx.find("HARD_DEADLINE_PWM_OFF_CLOSE_UNVERIFIED")!=std::string::npos,"unlogged deadline");
  checks();
}
void detach_fault() {
  setup(); send("servo configure 1470 1530 1500 1520 CONFIRM"); send("servo arm YES");
  send("servo open"); run(260);
  hw::ledc_fail_detach=true; run(355);
  expect(bench.state()==m4::servo_bench::State::FAULT && hw::ledc_attached,
         "failed detach did not latch fault and report uncertainty");
  expect(Serial0.tx.find("PWM_OFF_FAILED_FAULT_REMOVE_SERVO_POWER")!=std::string::npos,
         "failed PWM off was not logged");
  send("servo arm YES");
  expect(bench.state()==m4::servo_bench::State::FAULT && hw::ledc_attaches==1,
         "fault rearmed without power removal");
  hw::ledc_fail_detach=false; send("servo disarm");
  expect(!hw::ledc_attached && bench.state()==m4::servo_bench::State::FAULT,
         "fault recovery incorrectly rearmed");
  checks();
}
void wrap_and_parser() {
  hw::now_us=(static_cast<uint64_t>(UINT32_MAX)-200u)*1000u;
  setup(); send("servo configure 1470 1530 1500 1520 CONFIRM");
  send(std::string(200,'X')); send("servo status");
  expect(!discard_line && used==0 && hw::ledc_attaches==0,"oversized UART line changed PWM");
  send("servo arm YES"); send("servo open"); run(260);
  expect(bench.state()==m4::servo_bench::State::CLOSING,"auto-close failed across u32 millis wrap");
  run(360);
  expect(bench.state()==m4::servo_bench::State::DISARMED,"disarm failed across u32 wrap");
  checks();
}
void reboot_disarms_without_claiming_closure() {
  setup(); send("servo configure 1470 1530 1500 1520 CONFIRM");
  send("servo arm YES"); send("servo open");
  expect(hw::ledc_attached && bench.state()==m4::servo_bench::State::MOVING,
         "reboot fixture did not start bounded movement");
  setup(); // simulated fresh MCU setup; NOT a physical brownout/closure test
  expect(!hw::ledc_attached && bench.state()==m4::servo_bench::State::DISARMED &&
         !bench.configured() && bench.arms()==0,"reboot retained PWM/config/arm");
  send("servo open"); send("servo arm YES");
  expect(Serial0.tx.find("MECHANICAL_CLOSE_UNVERIFIED")!=std::string::npos &&
         hw::ledc_attaches==1,"reset incorrectly moved servo without new config/arm");
  checks();
}
} // namespace
int main(int argc,char** argv) {
  try {
    if (argc!=3) throw std::invalid_argument("servo_bench_loop CASE NEW_LOG");
    const std::string name=argv[1];
    if (name=="cold_limits") cold_and_limits();
    else if (name=="expiry_budget") arm_expiry_and_budget();
    else if (name=="attach_fault") output_faults();
    else if (name=="write_fault") write_fault_and_hard_deadline();
    else if (name=="hard_deadline") hard_deadline();
    else if (name=="detach_fault") detach_fault();
    else if (name=="wrap_and_parser") wrap_and_parser();
    else if (name=="reboot_disarms") reboot_disarms_without_claiming_closure();
    else throw std::invalid_argument("unknown bench fixture");
    std::ofstream log(argv[2],std::ios::binary); log<<Serial0.tx;
    if (!log) throw std::runtime_error("log write failed");
    std::cout<<"{\"case\":\""<<name<<"\",\"assertions\":"<<assertions
             <<",\"scope\":\"HOST_FAKE_LEDC_REAL_BENCH_LOOP\",\"physical_hardware\":false,\"result\":\"PASS\"}\n";
    return 0;
  } catch (const std::exception& error) { std::cerr<<"FAIL servo bench: "<<error.what()<<'\n'; return 1; }
}
