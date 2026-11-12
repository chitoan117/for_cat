// Actual pump bench setup/loop with fake GPIO7; both polarities & inert profile.
#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define SERVO_DIAGNOSTIC_ENABLED 0
#define PUMP_DIAGNOSTIC_ENABLED 0
#define PUMP_BENCH_MODE 1
#ifndef HOST_ACTIVE
#define HOST_ACTIVE 1
#endif
#ifndef HOST_OFF
#define HOST_OFF 0
#endif
#define PUMP_BENCH_PHYSICAL_ENABLE HOST_ACTIVE
#define PUMP_BENCH_OFF_LEVEL HOST_OFF
#include "../src/pump_bench.cpp"
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace hw=host_board;
namespace {
unsigned assertions=0;
void expect(bool ok,const char* message) {++assertions;if(!ok) throw std::runtime_error(message);}
void run(uint32_t ms) {
  const auto until=hw::now_us+static_cast<uint64_t>(ms)*1000;
  while(hw::now_us<until) loop();
}
void send(const std::string& text) {
  Serial0.input(text+"\n");
  for(unsigned n=0;n<100 && !Serial0.rx.empty();++n) run(2);
  expect(Serial0.rx.empty(),"serial command stalled");
}
void noOtherGpio() {
  for(int pin : {4,5,6,8,9,10,11,12,13,14,15,16,17,18})
    expect(hw::touches[static_cast<size_t>(pin)]==0,"unrelated hardware toggled");
}
void inert() {
  setup();send("pump status");send("pump arm YES");send("pump on 50");run(100);
  expect(hw::touches[7]==0 && controller.state()==m4::pump_bench::State::DISARMED,
         "unknown-polarity profile touched GPIO7");
  expect(Serial0.tx.find("mode=INERT_UNKNOWN_POLARITY")!=std::string::npos,
         "inert profile mislabeled active");
  noOtherGpio();
}
void boundedPulse() {
  setup();
  expect(hw::touches[7]>0 && hw::levels[7]==(HOST_OFF!=0),"boot did not command reviewed OFF level");
  send("pump on 80");expect(!output.commandedOn(),"disarmed pump moved");
  send("pump arm YES");send("pump on 800");
  expect(!output.commandedOn(),"out-of-range request started pump");
  send("pump on 80");
  expect(output.commandedOn() && hw::levels[7]!=(HOST_OFF!=0),"wrong GPIO polarity/ON");
  run(100);
  expect(!output.commandedOn() && hw::levels[7]==(HOST_OFF!=0) &&
         controller.state()==m4::pump_bench::State::DISARMED,"timer did not command OFF");
  send("pump arm YES");expect(controller.state()==m4::pump_bench::State::DISARMED,"cooldown bypassed");
  run(1000);send("pump arm YES");send("pump on 40");send("pump off");
  expect(!output.commandedOn() && hw::levels[7]==(HOST_OFF!=0),"manual off failed");
  run(1000);send("pump arm YES");send("pump on 20");send("pump disarm");
  expect(controller.pulses()==3 && !output.commandedOn(),"third pulse not bounded");
  send("pump arm YES");
  expect(Serial0.tx.find("REJECTED_LIMIT")!=std::string::npos && hw::levels[7]==(HOST_OFF!=0),
         "unbounded arm after 3 pulses");
  noOtherGpio();
}
void resetWhileOn() {
  setup();send("pump arm YES");send("pump on 100");
  expect(output.commandedOn(),"reset fixture not ON");
  setup();
  expect(!output.commandedOn() && controller.state()==m4::pump_bench::State::DISARMED &&
         hw::levels[7]==(HOST_OFF!=0),"setup did not command OFF on simulated reset");
  send("pump on 100");expect(!output.commandedOn(),"reset resumed motor without manual arm");
  noOtherGpio();
}
} // namespace
int main(int argc,char** argv) {
  try {
    if(argc!=3) throw std::invalid_argument("CASE LOG required");
    const std::string name=argv[1];
    if(name=="inert") inert();
    else if(name=="bounded") boundedPulse();
    else if(name=="reset") resetWhileOn();
    else throw std::invalid_argument("unknown case");
    std::ofstream log(argv[2],std::ios::binary);log<<Serial0.tx;
    if(!log) throw std::runtime_error("serial log failure");
    std::cout<<"{\"case\":\""<<name<<"\",\"assertions\":"<<assertions
             <<",\"host_off_level\":"<<HOST_OFF<<",\"host_active\":"<<HOST_ACTIVE
             <<",\"physical_hardware\":false,\"result\":\"PASS\"}\n";
    return 0;
  } catch(const std::exception& error) {std::cerr<<"PUMP_BENCH_HOST_FAIL "<<error.what()<<'\n';return 1;}
}
