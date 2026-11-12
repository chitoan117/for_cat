// Actual isolated firmware setup()/loop(), actual HX711 bits/NVS/parser, fake pins.
#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define SERVO_DIAGNOSTIC_ENABLED 0
#define PUMP_DIAGNOSTIC_ENABLED 0
#define DISPENSE_BENCH_MODE 1
#define DISPENSE_BENCH_PHYSICAL_ENABLE 1
#include "../src/dispense_bench.cpp"
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace hw=host_board;
namespace {
unsigned assertions=0;
float mass=0;
uint64_t last_adc_at=0;
void expect(bool okay,const char* message) { ++assertions; if(!okay) throw std::runtime_error(message); }
void calibratedNvs() {
  m4::CalibrationRecord record;
  expect(record.hx711.tare(100) && record.hx711.reference(1100,10),"fixture calibration");
  uint8_t bytes[m4::calibration_record::SIZE]{};
  expect(m4::calibration_record::encode(record,bytes),"calibration encoding");
  hw::nvs["m4-calibration/sensors-v2"]={bytes,bytes+sizeof(bytes)};
}
void advance(uint32_t milliseconds,bool adc=true) {
  const auto end=hw::now_us+static_cast<uint64_t>(milliseconds)*1000;
  unsigned iterations=0;
  while(hw::now_us<end) {
    if (++iterations>2000000) throw std::runtime_error("bounded loop exhausted");
    if (adc && hw::adc_bits.empty() && hw::now_us-last_adc_at>=100000) {
      last_adc_at=hw::now_us;
      hw::queue_adc(100+static_cast<int32_t>(mass*100));
    }
    loop();
  }
}
void send(const std::string& text) {
  Serial0.input(text+"\n");
  for (unsigned i=0;i<100 && !Serial0.rx.empty();++i) advance(2);
  expect(Serial0.rx.empty(),"UART input parser did not drain");
}
const char* config="dispense configure 1400 1600 1500 1560 100 40 500 5 2.0 0.2 0.2 5.0 8.0 CONFIRM";
void prepare() {
  calibratedNvs(); setup();send("dispense inspect YES");send(config);
  advance(300);
  expect(scale.status.health==m4::Health::HEALTHY,"scale failed to deliver calibrated fresh sample");
}
void assert_no_other_pins() {
  for (int pin : {7,8,9,10,11,12,13,14,15,16,17,18})
    expect(hw::touches[static_cast<size_t>(pin)]==0,"non-food GPIO touched");
  expect(!hw::ledc_attached && !hw::levels[6],"PWM stayed attached/servo pin not LOW");
}
void safe_boot_and_commands() {
  setup();send("dispense status");send("dispense test 3.0 1");send("dispense arm YES");
  expect(!hw::ledc_attached && hw::nvs.empty(),"uncalibrated boot moved/wrote NVS");
  send("dispense inspect YES");send(config);
  mass=0;advance(300);send("dispense arm YES");
  expect(dispenser.state()==m4::dispense_bench::State::DISARMED &&
         Serial0.tx.find("HX711_NOT_CALIBRATED")!=std::string::npos,"missing HX calibration accepted");
  send("PUMP ON");send("FEED_REQUEST");send(std::string(260,'x'));send("dispense status");
  assert_no_other_pins();
}
void normal_closed_loop() {
  prepare();send("dispense arm YES");send("dispense test 3.0 1");
  expect(dispenser.state()==m4::dispense_bench::State::WAIT_BASELINE &&
         hw::nvs.count("dispense-bench/state-v1")==1,"writeahead not persisted before pulses");
  uint8_t supplied=0;uint32_t deadline=0;
  while(dispenser.state()!=m4::dispense_bench::State::COMPLETE && deadline<12000) {
    if (dispenser.state()==m4::dispense_bench::State::CLOSING && supplied<dispenser.pulses() && supplied<3) {
      mass += supplied==0?1.5f:supplied==1?1.1f:0.5f;
      ++supplied;
    }
    advance(10);deadline+=10;
    expect(dispenser.state()!=m4::dispense_bench::State::FAULT,"normal test faulted");
  }
  expect(dispenser.state()==m4::dispense_bench::State::COMPLETE && supplied==3,
         "no bounded three-pulse completion");
  expect(dispenser.pulses()==3 && dispenser.dispensed()>3.0f && !dispenser.locked(),
         "actual stable delta/durable completion wrong");
  expect(Serial0.tx.find("event=COARSE")!=std::string::npos &&
         Serial0.tx.find("event=FINE")!=std::string::npos &&
         Serial0.tx.find("event=COMPLETE")!=std::string::npos,"coarse/fine/complete transcript missing");
  send("dispense status");
  expect(Serial0.tx.find("servo_pwm_attached=0")!=std::string::npos &&
         Serial0.tx.find("pump=OFF cat_auto=OFF web=OFF")!=std::string::npos,
         "final status claimed active PWM/pump/AI");
  assert_no_other_pins();
}
void interrupted_reboot_and_duplicate() {
  prepare();send("dispense arm YES");send("dispense test 3.0 1");
  for(unsigned n=0;n<30 && dispenser.state()!=m4::dispense_bench::State::OPEN;++n) advance(100);
  expect(dispenser.state()==m4::dispense_bench::State::OPEN && hw::ledc_attached,
         "fixture failed to reach servo pulse");
  setup(); // host reset executes actual setup; no physical closure claim
  expect(!hw::ledc_attached && dispenser.locked() &&
         dispenser.state()==m4::dispense_bench::State::DISARMED,"reset replayed incomplete pulse");
  send("dispense arm YES");
  expect(Serial0.tx.find("INSPECTION_REQUIRED")!=std::string::npos,"pending reboot was armed");
  send("dispense inspect YES");send(config);advance(300);send("dispense arm YES");
  send("dispense test 3.0 1");
  expect(Serial0.tx.find("result=DUPLICATE")!=std::string::npos &&
         dispenser.pulses()==0,"replayed request ID reopened after reset");
  send("dispense disarm");advance(400);assert_no_other_pins();
}
void abort_and_sensor_timeout() {
  prepare();send("dispense arm YES");send("dispense test 3.0 1");
  for(unsigned n=0;n<30 && dispenser.state()!=m4::dispense_bench::State::OPEN;++n) advance(100);
  expect(dispenser.state()==m4::dispense_bench::State::OPEN,"abort fixture did not move");
  send("dispense abort");advance(400);
  expect(dispenser.state()==m4::dispense_bench::State::FAULT && dispenser.locked() &&
         dispenser.reason()==m4::dispense_bench::Reason::ABORTED,"abort did not close and latch");
  assert_no_other_pins();
}
void nvs_write_failure_denies_open() {
  prepare();send("dispense arm YES");
  hw::nvs_write_failure=true;
  send("dispense test 3.0 1");
  advance(400);
  expect(dispenser.state()==m4::dispense_bench::State::FAULT &&
         dispenser.reason()==m4::dispense_bench::Reason::PERSISTENCE_FAULT &&
         dispenser.pulses()==0 && hw::ledc_attaches==1 && !hw::ledc_attached,
         "NVS write fault permitted dispensing");
  expect(Serial0.tx.find("result=PERSISTENCE_FAULT")!=std::string::npos,
         "writeahead rejection absent from serial transcript");
  assert_no_other_pins();
}
void hx_timeout_after_pulse() {
  prepare();send("dispense arm YES");send("dispense test 3.0 1");
  for(unsigned n=0;n<30 && dispenser.state()!=m4::dispense_bench::State::OPEN;++n) advance(100);
  expect(dispenser.state()==m4::dispense_bench::State::OPEN,"HX fault fixture did not open");
  advance(1000,false); // no fabricated new ADC conversions
  expect(dispenser.state()==m4::dispense_bench::State::FAULT &&
         dispenser.reason()==m4::dispense_bench::Reason::HX711_NOT_READY &&
         !hw::ledc_attached && dispenser.locked(),"stale HX sample did not shut PWM/lock NVS");
  assert_no_other_pins();
}
} // namespace
int main(int argc,char** argv) {
  try {
    if(argc!=3) throw std::invalid_argument("dispense_bench_loop CASE LOG");
    const std::string name=argv[1];
    if(name=="safe_boot") safe_boot_and_commands();
    else if(name=="closed_loop") normal_closed_loop();
    else if(name=="reboot") interrupted_reboot_and_duplicate();
    else if(name=="abort") abort_and_sensor_timeout();
    else if(name=="nvs_write_fault") nvs_write_failure_denies_open();
    else if(name=="hx_timeout") hx_timeout_after_pulse();
    else throw std::invalid_argument("unknown case");
    std::ofstream log(argv[2],std::ios::binary);log<<Serial0.tx;
    if(!log) throw std::runtime_error("missing transcript");
    std::cout<<"{\"case\":\""<<name<<"\",\"assertions\":"<<assertions
             <<",\"physical_hardware\":false,\"result\":\"PASS\"}\n";
    return 0;
  } catch(const std::exception& error) {std::cerr<<"DISPENSE_LOOP_FAIL "<<error.what()<<'\n';return 1;}
}
