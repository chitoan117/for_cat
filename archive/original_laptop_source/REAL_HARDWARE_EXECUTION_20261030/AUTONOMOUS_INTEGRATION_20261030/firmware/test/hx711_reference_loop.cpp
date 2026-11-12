#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define M4_SENSOR_BRINGUP 1
#define M4_DIAGNOSTIC_MODE 1
#define M4_HX711_INSTALLED 1
#define M4_HX711_REFERENCE_DIAG 1
#define SERVO_DIAGNOSTIC_ENABLED 0
#define PUMP_DIAGNOSTIC_ENABLED 0
#include "../src/hx711_reference_diag.cpp"
#include <iostream>
static unsigned checks=0;
#define CHECK(x) do { ++checks; if (!(x)) { std::cerr<<"FAIL line "<<__LINE__<<": "<<#x<<"\n"; return 1; } } while (0)
int main() {
  using namespace hx_reference_diag;
  setup();
  CHECK(std::strcmp(m4::NvsCalibration::key(),"sensors-v2")==0);
  CHECK(!scale.calibration.valid() && !scale.display_grams.valid && host_board::nvs_writes==0);
  CHECK(Serial0.tx.find("SOURCE=NONE")!=std::string::npos);
  command("t"); CHECK(!tare_pending);
  command("reference CONFIRM extra"); CHECK(!scale.calibration.valid());
  command("reference CONFIRM"); CHECK(scale.calibration.valid() && std::strcmp(calibration_source,"ARDUINO_REFERENCE_RAM_ONLY")==0);
  auto sample=[](int32_t raw) { host_board::queue_adc(raw); host_board::now_us+=100000; loop(); };
  Serial0.tx.clear(); sample(-673805); sample(-673805); sample(-673805);
  CHECK(scale.signed_grams.valid && std::fabs(scale.signed_grams.value-5)<0.001);
  CHECK(Serial0.tx.find("KHOI LUONG = 5.00 g")!=std::string::npos);
  CHECK(Serial0.tx.size()<350); // one compact triplet, fits 80SPS/3 at 115200
  // Explicit tare completes only after all 15 conversions and does not alter slope.
  const auto slope=scale.calibration.grams_per_count;
  command("t"); CHECK(tare_pending);
  for (int i=0;i<14;++i) sample(-669000);
  CHECK(tare_pending && scale.calibration.tare_counts==-668483);
  sample(-669000);
  CHECK(!tare_pending && scale.calibration.tare_counts==-669000 && scale.calibration.grams_per_count==slope);
  CHECK(!scale.display_grams.valid && host_board::nvs_writes==0);
  command("t"); sample(-669000); sample(-1);
  CHECK(!tare_pending && scale.calibration.tare_counts==-669000);
  Serial0.tx.clear(); host_board::now_us+=501000; loop();
  CHECK(!scale.raw.valid && !scale.display_grams.valid);
  CHECK(Serial0.tx.find("\"display_grams\":null")!=std::string::npos);
  CHECK(Serial0.tx.find("KHOI LUONG = INVALID")!=std::string::npos);
  // Frozen pre-existing ESP32 record survives all reference/tare operations.
  m4::CalibrationRecord nvs;
  nvs.hx711={true,true,-600000,1.0/-1000}; nvs.water={true,12,38};
  uint8_t bytes[m4::calibration_record::SIZE]; CHECK(m4::calibration_record::encode(nvs,bytes));
  host_board::nvs["m4-calibration/sensors-v2"]=std::vector<uint8_t>(bytes,bytes+sizeof(bytes));
  const auto original_nvs=host_board::nvs;
  command("load"); CHECK(scale.calibration.tare_counts==-600000 && scale.calibration.grams_per_count==-0.001);
  CHECK(std::strcmp(calibration_source,"ESP32_NVS")==0);
  for (int i=0;i<3;++i) sample(-605000);
  CHECK(scale.display_grams.valid && std::fabs(scale.display_grams.value-5)<0.001);
  CHECK(stored.water.empty_cm==38);
  command("reference CONFIRM"); command("t"); for (int i=0;i<15;++i) sample(-668500);
  CHECK(host_board::nvs==original_nvs && host_board::nvs_writes==0);
  setup(); // simulated reboot: loads original ESP32 factor, never last RAM reference/tare
  CHECK(scale.calibration.tare_counts==-600000 && scale.calibration.grams_per_count==-0.001);
  CHECK(!scale.display_grams.valid && std::strcmp(calibration_source,"ESP32_NVS")==0);
  command("esp32-cal -610000 -1050 CONFIRM"); CHECK(scale.calibration.tare_counts==-610000);
  command("esp32-cal -1 0 CONFIRM"); CHECK(scale.calibration.tare_counts==-610000);
  command("esp32-cal -1 nan CONFIRM"); CHECK(scale.calibration.tare_counts==-610000);
  command("esp32-cal -1 -1000 CONFIRM extra"); CHECK(scale.calibration.tare_counts==-610000);
  command("load");
  // Exercise the actual newline parser, its length bound and rejected commands.
  Serial0.input(std::string(120,'X')+"\nt\n");
  for (int i=0;i<6;++i) loop();
  CHECK(tare_pending); // only final intact 't' was accepted
  command("load"); command("save YES"); command("cal 38 15"); command("SERVO OPEN"); command("PUMP ON");
  command("FEED_REQUEST");
  CHECK(host_board::nvs==original_nvs && host_board::nvs_writes==0);
  host_board::nvs["m4-calibration/sensors-v2"][13]^=1; command("load");
  CHECK(!scale.calibration.valid() && !scale.display_grams.valid);
  for (int pin=0;pin<64;++pin) if (pin!=4 && pin!=5) CHECK(host_board::touches[pin]==0);
  CHECK(!host_board::ledc_attached && host_board::ledc_attaches==0 && host_board::ledc_writes==0);
  CHECK(host_board::critical_depth==0 && host_board::critical_errors==0);
  Serial0.tx.clear(); report(millis()); std::cout<<Serial0.tx;
  std::cout<<"HX711_REFERENCE_LOOP_SOFTWARE_PASS assertions="<<checks<<" physical=NOT_TESTED\n";
}
