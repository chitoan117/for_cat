// Execute the real combined diagnostics setup()/loop() against host-only adapters.
// Each named case runs in a fresh process. Never link these stubs into MCU firmware.
#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define M4_SENSOR_BRINGUP 1
#define M4_DIAGNOSTIC_MODE 7
#define M4_HX711_INSTALLED 1 // explicit future-installed SOFTWARE fixture only
#include "../src/diagnostics.cpp"
#include <fstream>
#include <iostream>

namespace hw=host_board;
namespace {
unsigned assertions=0;
void expect(bool value,const char* message) {
  ++assertions; if (!value) throw std::runtime_error(message);
}
void run_for_ms(std::uint32_t duration) {
  const auto end=hw::now_us+static_cast<std::uint64_t>(duration)*1000;
  unsigned iterations=0;
  while (hw::now_us<end) {
    if (++iterations>2000000) throw std::runtime_error("test loop execution budget exhausted");
    const auto before=hw::now_us; loop();
    if (hw::now_us==before) ++hw::now_us;
  }
}
void send(const std::string& text) {
  Serial0.input(text+"\n"); const auto deadline=hw::now_us+250000;
  while (!Serial0.rx.empty() && hw::now_us<deadline) loop();
  expect(Serial0.rx.empty(),"actual serial command parser failed to consume input within budget");
}
void good_boot() { hw::oled_connected=true; setup(); }
void sample_scale(std::int32_t raw) { hw::queue_adc(raw); run_for_ms(2); }
void calibrate_scale() {
  send("tare 2"); sample_scale(100); sample_scale(100);
  expect(scale.calibration.tared && !scale.calibration.valid(),"tare must not invent a factor");
  send("cal 50 2"); sample_scale(1100); sample_scale(1100);
  expect(scale.calibration.valid(),"known-mass synthetic reference did not calibrate");
  sample_scale(600);
  expect(snapshot.grams.valid && std::fabs(snapshot.grams.value-25)<0.001,"raw-to-grams path through actual loop");
}
void boot_missing() {
  hw::rtc.connected=false; setup(); run_for_ms(1200);
  expect(!snapshot.rtc_time.valid && snapshot.rtc.health==m4::Health::NOT_CONNECTED,"missing RTC not reflected");
  expect(!snapshot.grams.valid && snapshot.load_cell.health==m4::Health::NOT_CONNECTED,"missing ADC must time out");
  expect(!snapshot.food_percent.valid && !snapshot.water_percent.valid,"missing geometry must be null");
  expect(hw::touches[12]==0 && hw::touches[13]==0 && hw::touches[14]==0 && hw::touches[15]==0,"echo GPIO touched before review command");
  expect(hw::touches[11]>0 && pir_configured,"PIR input not configured independently");
  expect(hw::nvs_writes==0,"boot wrote calibration");
  expect(oled.status.health==m4::Health::NOT_CONNECTED,"missing display status");
  expect(Serial0.tx.find("\"grams\":null")!=std::string::npos,"no null-weight report");
  for (const auto& transaction:hw::rtc.history) expect(transaction.command==0xbf,"boot/poll modified RTC registers");
}
void calibration_flow() {
  m4::CalibrationRecord old;
  old.hx711.tared=true; old.hx711.calibrated=true; old.hx711.tare_counts=100; old.hx711.grams_per_count=0.05;
  old.food.set(5,50); old.water.set(10,100);
  uint8_t bytes[m4::calibration_record::SIZE]{};
  expect(m4::calibration_record::encode(old,bytes),"legacy fixture encode");
  hw::nvs["m4-calibration/sensors-v1"]={bytes,bytes+sizeof(bytes)};
  good_boot(); sample_scale(100);
  expect(!scale.calibration.valid() && !calibration.water.valid(),"new role mapping inherited legacy geometry/factor");
  expect(snapshot.raw_weight.valid && !snapshot.grams.valid,"uncalibrated raw reading turned into grams");
  calibrate_scale(); send("status");
  expect(hw::nvs_writes==0,"calibration implicitly persisted");
  send("food-geometry 5 50"); send("water-geometry 10 100");
  expect(scale.calibration.valid() && calibration.hx711.valid(),"level geometry erased unsaved HX711 factor");
  expect(!snapshot.food_percent.valid && !snapshot.water_percent.valid,"geometry config fabricated an echo");
  send("save YES");
  expect(hw::nvs_writes==1 && hw::nvs.count("m4-calibration/sensors-v2")==1,"wrong role-scoped NVS key");
  expect(hw::nvs.size()==2 && hw::nvs["m4-calibration/sensors-v1"]==std::vector<uint8_t>(bytes,bytes+sizeof(bytes)),"save overwrote legacy calibration or safety counters");
  scale.calibration={}; send("load");
  expect(scale.calibration.valid() && !snapshot.grams.valid,"loaded factor reused old grams without a new ADC sample");
  sample_scale(600); send("status");
  expect(snapshot.grams.valid && std::fabs(snapshot.grams.value-25)<0.001,"loaded calibration not applied to next sample");
  hw::nvs_available=false; send("save YES");
  expect(Serial0.tx.find("REJECTED NOT_CALIBRATED_OR_NVS_ERROR")!=std::string::npos,"NVS failure not surfaced");
  run_for_ms(600); send("status");
  expect(!snapshot.grams.valid && snapshot.load_cell.health==m4::Health::NOT_CONNECTED,"ADC timeout retained grams");
  sample_scale(600);
  expect(snapshot.grams.valid,"ADC failed to recover after timeout");
  send("tare 2"); sample_scale(200); sample_scale(200);
  send("water-geometry 6 50");
  expect(!scale.calibration.valid() && !calibration.hx711.valid(),"geometry revived a stale pre-tare factor");
  run_for_ms(100); expect(oled.status.health==m4::Health::HEALTHY,"OLED transfer did not complete");
}
void independent_echoes() {
  good_boot(); hw::food_echo.distance_cm=30; hw::water_echo.distance_cm=60;
  send("echo-approach-3v3 CONFIRM"); run_for_ms(650);
  expect(hw::food_echo.pulses>0 && hw::water_echo.pulses==0 && hw::touches[10]==0,"food acknowledgment enabled water");
  expect(snapshot.approach_distance_cm.valid && !snapshot.food_percent.valid,"approach turned into inventory");
  send("echo-water-3v3 CONFIRM"); send("food-geometry 5 50"); send("water-geometry 10 100");
  run_for_ms(1800); send("status");
  expect(hw::food_echo.pulses>=3 && hw::water_echo.pulses>=2,"both channels not scheduled");
  expect(snapshot.approach_distance_cm.valid && std::fabs(snapshot.approach_distance_cm.value-30)<0.2,"approach distance wrong");
  expect(snapshot.water_distance_cm.valid && std::fabs(snapshot.water_distance_cm.value-60)<0.2,"water distance wrong");
  expect(!snapshot.food_percent.valid && !snapshot.food_distance_cm.valid && snapshot.water_percent.valid,"TBD inventory acquired data or operational water lost geometry");
  expect(hw::overlaps==0,"ultrasonic acquisitions overlap");
  expect(hw::other_work_during_echo==0,"slow IO work ran while echo pending");
}
void faults_and_recovery() {
  good_boot(); calibrate_scale(); send("status");
  hw::water_echo.missing=true;
  send("echo-approach-3v3 CONFIRM"); send("echo-water-3v3 CONFIRM");
  run_for_ms(1800); send("status");
  expect(snapshot.approach_distance_cm.valid,"water failure stopped approach acquisition");
  expect(!snapshot.water_distance_cm.valid && snapshot.water.health==m4::Health::NOT_CONNECTED,"water timeout not invalidated");
  expect(snapshot.rtc_time.valid,"RTC starved by missing echo");
  expect(!snapshot.grams.valid,"ADC stopped producing but old grams survived");
  hw::water_echo.missing=false; run_for_ms(700); send("status");
  expect(snapshot.water_distance_cm.valid && !snapshot.water_percent.valid,"water did not recover as uncalibrated distance");
  hw::water_echo.stuck_high=true; run_for_ms(700); send("status");
  expect(snapshot.water.health==m4::Health::FAULT && !snapshot.water_distance_cm.valid,"stuck-high echo not rejected");
  hw::oled_connected=false; run_for_ms(1100); // allow the next 1Hz display refresh
  expect(oled.status.health==m4::Health::FAULT,"OLED fault not exposed");
  const auto pulses=hw::food_echo.pulses; run_for_ms(700);
  expect(hw::food_echo.pulses>pulses,"OLED failure blocked independent sensor loop");
  expect(hw::overlaps==0 && hw::other_work_during_echo==0,"fault path broke echo scheduling isolation");
}
void clock_and_parser() {
  good_boot(); hw::rtc.regs[0]|=0x80; run_for_ms(1100); send("status");
  expect(!snapshot.rtc_time.valid && rtc.status.reason==m4::Reason::CLOCK_HALTED,"CH flag accepted as valid time");
  send("set-utc 2100-01-01T00:00:00Z CONFIRM");
  expect(!snapshot.rtc_time.valid,"unsupported century accepted");
  send("set-utc 2026-10-17T12:34:56Z CONFIRM");
  expect(snapshot.rtc_time.valid && snapshot.rtc_time.value.hour==12 && snapshot.rtc_time.value.second==56,"explicit clock set/readback failed");
  expect(hw::rtc.regs[7]==0x80 && hw::rtc.contention==0,"write protection/turnaround lost");
  const auto writes=hw::nvs_writes;
  send(std::string(200,'X')); send("FEED_REQUEST"); send("PUMP ON"); send("SERVO OPEN");
  send("cal nan 2"); send("tare 100"); send("food-range nan 100");
  expect(hw::nvs_writes==writes && !scale.calibration.valid(),"bad commands changed persistent/calibration state");
  Serial0.input(std::string("\xa5\x5a\x01")+"noise\n"); run_for_ms(10); send("status");
  expect(!discard_command && command_size==0,"parser failed to recover from binary/oversized noise");
  expect(Serial0.tx.find("REJECTED UNKNOWN_DIAGNOSTIC_COMMAND")!=std::string::npos,"actuator commands not explicitly rejected");
  for (const auto& transaction:hw::rtc.history) expect(transaction.command!=0x90 && transaction.command!=0x91,"RTC charger register touched");
}
void reserved_pins_and_pir() {
  good_boot();
  hw::levels[11]=true; run_for_ms(80); send("status");
  expect(pir_motion && Serial0.tx.find("\"motion\":true")!=std::string::npos,"PIR transition missing from report");
  hw::levels[11]=false; run_for_ms(80); send("status");
  expect(!pir_motion,"PIR low transition lost");
  send("buzz confirm"); run_for_ms(20);
  expect(hw::touches[12]==0 && hw::touches[13]==0,"removed accessories touched approach GPIO");
  send("buzzer-driver ACTIVE_HIGH CONFIRM"); send("buzz confirm"); run_for_ms(10);
  send("echo-food-3v3 CONFIRM"); send("food-geometry 5 50");
  expect(!buzzer_ack && !food_echo_ack && !calibration.food.valid(),"legacy command enabled reassigned pins or inventory");
  run_for_ms(250);
  expect(hw::touches[12]==0 && hw::touches[13]==0 && !buzzer.state.active(),"legacy button/buzzer still owns approach pins");
  send("status");
}
} // namespace
int main(int argc,char** argv) {
  try {
    if (argc!=3) throw std::invalid_argument("usage: firmware_loop CASE NEW_SERIAL_LOG");
    hw::sensitive_acquisition=[] { return dual.busy(); };
    const std::string name=argv[1];
    if (name=="boot_missing") boot_missing();
    else if (name=="calibration_flow") calibration_flow();
    else if (name=="independent_echoes") independent_echoes();
    else if (name=="faults_and_recovery") faults_and_recovery();
    else if (name=="clock_and_parser") clock_and_parser();
    else if (name=="reserved_pins_and_pir") reserved_pins_and_pir();
    else throw std::invalid_argument("unknown firmware-loop test case");
    expect(hw::touches[6]==0 && hw::touches[7]==0 && hw::touches[10]==0,"ACTUATOR/RESERVED GPIO TOUCHED");
    expect(hw::touches[1]==0 && hw::touches[2]==0 && hw::touches[21]==0 && hw::touches[47]==0,"unapproved inventory candidate used");
    expect(hw::critical_depth==0 && hw::critical_errors==0,"unbalanced HX711 critical section");
    expect(hw::rtc.contention==0,"DS1302 data-bus contention");
    expect(Serial0.tx.find("\"physical_pump_on\":false")!=std::string::npos,"missing disabled physical-output report");
    std::ofstream evidence(argv[2],std::ios::binary); evidence << Serial0.tx; evidence.close();
    if (!evidence) throw std::runtime_error("test evidence write failed");
    std::cout << "{\"case\":\"" << name << "\",\"assertions\":" << assertions
              << ",\"simulated_ms\":" << hw::now_us/1000
              << ",\"scope\":\"SYNTHETIC_FIRMWARE_LOOP\",\"actuator_gpio_touches\":0,\"result\":\"PASS\"}\n";
    return 0;
  } catch (const std::exception& error) { std::cerr << "FAIL firmware loop: " << error.what() << '\n'; return 1; }
}
