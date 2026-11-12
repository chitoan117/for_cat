// Execute CURRENT sensor-only firmware with fake ADC/RTC/OLED/PIR/echo, no actuator IO.
#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define M4_SENSOR_BRINGUP 1
#define M4_DIAGNOSTIC_MODE 7
#define M4_HX711_INSTALLED 1
#define M4_CURRENT_HARDWARE_PROFILE 1
#include "../src/diagnostics.cpp"
#include <fstream>
#include <iostream>

namespace hw=host_board;
namespace {
unsigned assertions=0;
void require(bool condition,const char* message) {
  ++assertions;if(!condition) throw std::runtime_error(message);
}
void run(uint32_t ms) {
  const auto until=hw::now_us+static_cast<uint64_t>(ms)*1000;
  unsigned count=0;
  while(hw::now_us<until) { if(++count>2000000) throw std::runtime_error("loop budget");loop(); }
}
void send(const std::string& text) {
  Serial0.input(text+"\n");
  for(unsigned i=0;i<300 && !Serial0.rx.empty();++i) run(2);
  require(Serial0.rx.empty(),"serial parser stuck");
}
void prepareScaleFixture() {
  m4::CalibrationRecord record;
  require(record.hx711.tare(100)&&record.hx711.reference(1100,10),"invalid fixture reference");
  uint8_t bytes[m4::calibration_record::SIZE]{};
  require(m4::calibration_record::encode(record,bytes),"failed to encode fixture");
  hw::nvs["m4-calibration/sensors-v2"]={bytes,bytes+sizeof(bytes)};
}
void adc(int raw) { hw::queue_adc(raw);run(8); }
void runWithAdc(uint32_t ms,int raw) {
  for(uint32_t i=0;i<ms;i+=100) {hw::queue_adc(raw);run(100);}
}
void baselineMissing() {
  hw::rtc.connected=false;setup();run(1250);send("status");
  require(Serial0.tx.find("\"mode\":\"diag_current_hardware\"")!=std::string::npos,"wrong mode");
  require(Serial0.tx.find("\"hx711_installed\":true")!=std::string::npos,"wired scale skipped");
  require(Serial0.tx.find("\"food_reservoir_sensor\":\"NOT_WIRED\"")!=std::string::npos,"food inventory reported fault");
  require(Serial0.tx.find("\"water_reservoir_sensor\":\"NOT_WIRED\"")!=std::string::npos,"water inventory reported fault");
  require(Serial0.tx.find("\"pump_armed\":false")!=std::string::npos &&
          Serial0.tx.find("\"servo_armed\":false")!=std::string::npos,"actuator armed in sensor image");
  require(Serial0.tx.find("\"rtc_detected\":false")!=std::string::npos,"missing RTC treated as working");
  require(Serial0.tx.find("\"grams\":null")!=std::string::npos,"missing scale fabricated grams");
}
void functionalSynthetic() {
  prepareScaleFixture();hw::oled_connected=true;setup();
  send("weight-stability 0.5 CONFIRM");
  for(unsigned i=0;i<5;++i) adc(100);
  send("echo-approach-3v3 CONFIRM");send("echo-water-3v3 CONFIRM");
  hw::food_echo.distance_cm=30;hw::water_echo.distance_cm=60;
  runWithAdc(1400,100);hw::levels[11]=true;runWithAdc(100,100);send("status");
  require(pir_transitions==1 && pir_motion && pir_transition_seen,"PIR transition not observed");
  require(snapshot.approach_distance_cm.valid && snapshot.water_distance_cm.valid,"two current channels missing");
  require(!snapshot.food_percent.valid && !snapshot.food_distance_cm.valid,"missing reservoir fabricated");
  require(Serial0.tx.find("\"weight_window_samples\":4")!=std::string::npos,"missing HX stability sample window");
  require(Serial0.tx.find("\"weight_stable\":true")!=std::string::npos,"stable fixture misreported");
  require(Serial0.tx.find("\"oled_initialized\":true")!=std::string::npos,"OLED fake ACK not in report");
  send("FEED_REQUEST");send("PUMP ON");send("SERVO OPEN");
  require(Serial0.tx.find("REJECTED UNKNOWN_DIAGNOSTIC_COMMAND")!=std::string::npos,"actuator command accepted");
}
void faults() {
  prepareScaleFixture();hw::oled_connected=true;setup();
  send("echo-approach-3v3 CONFIRM");send("echo-water-3v3 CONFIRM");
  hw::water_echo.missing=true;run(1600);send("status");
  require(water.distance.timeoutCount()>0,"missing echo has no timeout counter");
  require(snapshot.approach_distance_cm.valid && !snapshot.water_distance_cm.valid,"water loss corrupted approach");
  require(Serial0.tx.find("\"operational_water_timeout_count\":0")==std::string::npos,
          "missing echo reported no timeout");
  send("weight-stability 0 CONFIRM");
  require(Serial0.tx.find("REJECTED WEIGHT_STABILITY_INVALID")!=std::string::npos,"zero noise threshold accepted");
  send("weight-stability 0.01 CONFIRM");
  adc(100);adc(120);adc(100);adc(120);send("status");
  require(Serial0.tx.find("\"weight_stable\":false")!=std::string::npos,"noisy scale claimed stable");
  hw::levels[11]=true;run(40);hw::levels[11]=false;run(40);
  require(pir_transitions==2 && !pir_motion,"PIR return transition absent");
}
void buttons() {
  hw::oled_connected=true;prepareScaleFixture();setup();run(100);
  require(hw::pin_modes[21]==INPUT_PULLUP,"button not INPUT_PULLUP");
  require(button.raw_level && button.debounced_level && !button.button_pressed && button.press_count==0,
          "released button or startup count wrong");
  // Start a press near millis rollover, then exercise short contact bounce.
  hw::now_us=(static_cast<uint64_t>(UINT32_MAX)-20)*1000;
  for(unsigned i=0;i<8;++i) { hw::levels[21]=i%2!=0;run(5); }
  require(button.press_count==0,"contact bounce generated request");
  hw::levels[21]=false;run(100);
  require(button.button_pressed && !button.debounced_level && !button.raw_level && button.press_count==1,
          "debounced active LOW edge missing");
  const auto first_stamp=button.last_press_ms;
  run(5000);require(button.press_count==1 && button.last_press_ms==first_stamp,"hold repeated request");
  for(unsigned i=0;i<8;++i) { hw::levels[21]=i%2==0;run(5); }
  hw::levels[21]=true;run(100);
  require(button.press_count==1 && !button.button_pressed && button.debounced_level,"release generated request");
  hw::levels[21]=false;run(100);
  require(button.press_count==2,"second press did not increment exactly once");
  hw::levels[21]=true;run(100);
  // Button polling must remain usable while both approved ultrasonic channels run.
  send("echo-approach-3v3 CONFIRM");send("echo-water-3v3 CONFIRM");
  hw::levels[21]=false;runWithAdc(1500,100);
  require(button.press_count==3 && snapshot.approach_distance_cm.valid && snapshot.water_distance_cm.valid,
          "button or ranging regressed under combined acquisition");
  send("status");
  require(Serial0.tx.find("MANUAL_BUTTON_FEED_REQUEST count=3")!=std::string::npos &&
          Serial0.tx.find("actuator_blocked=true")!=std::string::npos,"diagnostic event absent");
  require(Serial0.tx.find("\"manual_button_request_count\":3")!=std::string::npos,"request telemetry absent");
  require(Serial0.tx.find("\"button_health\":\"HEALTHY\"")!=std::string::npos,"button health absent");
}
void heldAtBoot() {
  hw::levels[21]=false;setup();run(5000);
  require(button.button_pressed && button.press_count==0,"held-at-boot generated request");
  hw::levels[21]=true;run(100);
  require(button.press_count==0,"initial held release generated request");
  hw::levels[21]=false;run(100);
  require(button.press_count==1,"release then press did not arm diagnostic edge");
}
} // namespace
int main(int argc,char** argv) {
  try {
    if(argc!=3) throw std::invalid_argument("CASE NEW_LOG required");
    const std::string name=argv[1];
    hw::levels[21]=true; // external fixture simulates the pull-up/released switch
    if(name=="missing") baselineMissing();
    else if(name=="functional") functionalSynthetic();
    else if(name=="faults") faults();
    else if(name=="buttons") buttons();
    else if(name=="held_at_boot") heldAtBoot();
    else throw std::invalid_argument("unknown case");
    require(hw::touches[6]==0 && hw::touches[7]==0 && hw::touches[10]==0,
            "GPIO6/7 or optional GPIO10 touched by sensor image");
    require(hw::touches[1]==0 && hw::touches[2]==0 && hw::touches[47]==0,
             "unapproved inventory pins touched");
    require(hw::pin_modes[21]==INPUT_PULLUP && hw::high_writes[21]==0,"button pin driven as output");
    require(hw::ledc_attaches==0 && hw::ledc_writes==0 && hw::nvs_writes==0,
            "button diagnostic attached PWM, drove servo or wrote NVS");
    std::ofstream log(argv[2],std::ios::binary);log<<Serial0.tx;
    if(!log) throw std::runtime_error("serial log failure");
    std::cout<<"{\"case\":\""<<name<<"\",\"assertions\":"<<assertions
             <<",\"physical_hardware\":false,\"result\":\"PASS\"}\n";
    return 0;
  } catch(const std::exception& error) {std::cerr<<"CURRENT_HW_HOST_FAIL "<<error.what()<<'\n';return 1;}
}
