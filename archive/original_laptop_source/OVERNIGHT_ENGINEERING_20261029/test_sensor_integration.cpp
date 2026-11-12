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
#define M4_QUAD_ULTRASONIC 1
#include "../FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32/src/diagnostics.cpp"
#include <iostream>
unsigned checks=0;
void require(bool value) { ++checks;if(!value)throw std::runtime_error("sensor integration assertion failed"); }
void advance(uint32_t ms) {
  const auto end=host_board::now_us+uint64_t(ms)*1000;
  while(host_board::now_us<end) {
    const auto before=host_board::now_us;loop();
    if(host_board::now_us==before)++host_board::now_us;
  }
}
int main() {
  setup();Serial0.tx.clear();report();
  require(Serial0.tx.find("\"motion_quality\":\"WARMING_UP\"")!=std::string::npos);
  require(Serial0.tx.find("\"motion_stable\":null")!=std::string::npos);
  const int triggers[]={12,14,16,18},echoes[]={13,15,17,10};
  for(unsigned i=0;i<4;++i)require(dual.selectOnly(i,{m4::diagnosticPin(triggers[i]),m4::diagnosticPin(echoes[i]),i%2?25.f:5.f,400,30000,0.0343f}));
  require(dual.selectAllReviewed());
  host_board::food_echo.distance_cm=40;host_board::water_echo.distance_cm=100;
  host_board::hc2_echo.distance_cm=60;host_board::jsn2_echo.distance_cm=150;
  for(uint32_t guard:{60u,80u,100u}) {
    while(dual.busy())advance(1);
    require(dual.setGuardMs(guard));advance(2200);
    require(host_board::overlaps==0);
  }
  for(unsigned i=0;i<4;++i)require(dual.lastValid(i).valid);
  require(host_board::food_echo.pulses>=4 && host_board::jsn2_echo.pulses>=4);
  host_board::water_echo.missing=true;advance(1200);
  require(water.distance.timeoutCount()>0 && !water.distance.raw.valid);
  Serial0.tx.clear();report();
  require(Serial0.tx.find("\"state\":\"TIMEOUT\",\"distance_cm\":null")!=std::string::npos);
  require(approach.distance.raw.valid && hc2.distance.raw.valid && jsn2.distance.raw.valid);
  // JSN20cm is not accepted with the explicitly reviewed 25cm lower bound.
  host_board::water_echo.missing=false;host_board::water_echo.distance_cm=20;advance(1200);
  require(!water.distance.raw.valid);
  host_board::water_echo.distance_cm=100;
  // Jump fake time to avoid 60 million loop calls; no physical time/device use.
  while(dual.busy())advance(1);
  host_board::now_us=61000000;advance(200);
  require(pir_telemetry.valid() && !pir_telemetry.motion());
  host_board::levels[11]=true;advance(50);require(!pir_telemetry.valid());
  advance(150);require(pir_telemetry.valid() && pir_telemetry.motion());
  require(host_board::touches[6]==0 && host_board::touches[7]==0 && host_board::touches[2]==0);
  require(host_board::nvs_writes==0 && !host_board::ledc_attached);
  std::cout<<"SENSOR_INTEGRATION_PASS checks="<<checks<<" fake_io_only=true\n";
}
