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
#define M4_HX711_INOX 1
#define INOX_TEST_BOOT_NONCE 123
#define SERVO_DIAGNOSTIC_ENABLED 0
#define PUMP_DIAGNOSTIC_ENABLED 0
#include "../src/hx711_reference_diag.cpp"
#include <iostream>
unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){std::cerr<<"FAIL line"<<__LINE__<<": "<<#x<<"\n";return 1;}}while(0)
int main(){
 using namespace hx_reference_diag;
 setup();CHECK(!scale.calibration.valid()&&current_mount[0]==0&&host_board::nvs_writes==0);
 command("reference CONFIRM");command("t");CHECK(!scale.calibration.valid()&&!tare_pending);
 command("esp32-cal 500000 1000 CONFIRM");CHECK(!scale.calibration.valid());
 command("mount INOX_A CONFIRM");CHECK(!scale.calibration.valid()&&!mount_match);
 command("esp32-cal 500000 1000 CONFIRM");CHECK(scale.calibration.valid()&&fresh_import);
 auto mass=[](double gross){for(int n=0;n<3;++n){host_board::queue_adc(static_cast<int32_t>(500000+gross*1000));host_board::now_us+=100000;loop();}};
 mass(95);CHECK(scale.signed_grams.valid&&std::fabs(scale.signed_grams.value-95)<.001);
 const auto offset=scale.calibration.tare_counts;
 command("t");CHECK(scale.calibration.tare_counts==offset&&!tare_pending);
 mass(130);CHECK(std::fabs(scale.signed_grams.value-130)<.001);
 command("cal-save WRONG CONFIRM");CHECK(host_board::nvs_writes==0);
 command("cal-save INOX_A CONFIRM");CHECK(mount_match&&host_board::nvs_writes==2);
 setup();CHECK(!scale.calibration.valid()&&current_mount[0]==0); // old NVS never auto-authorises a mount
 command("mount INOX_A CONFIRM");CHECK(mount_match&&scale.calibration.valid()&&!fresh_import);
 mass(95);CHECK(std::fabs(scale.signed_grams.value-95)<.001);
 command("mount INOX_NEW_MOUNT CONFIRM");CHECK(!scale.calibration.valid()&&!mount_match);
 const auto writes=host_board::nvs_writes;
 command("cal-save INOX_NEW_MOUNT CONFIRM");CHECK(host_board::nvs_writes==writes);
 command("mount INOX_A CONFIRM");CHECK(scale.calibration.valid());
 host_board::nvs["m4-calibration/hx-mount-v1"][42]^=1;setup();command("mount INOX_A CONFIRM");CHECK(!scale.calibration.valid());
 Serial0.tx.clear();report(millis());CHECK(Serial0.tx.find("\"physical_validated\":false")!=std::string::npos);
 for(int pin=0;pin<64;++pin)if(pin!=4&&pin!=5)CHECK(host_board::touches[pin]==0);
 CHECK(!host_board::ledc_attached&&host_board::ledc_attaches==0);
 std::cout<<"HX711_INOX_LOOP_PASS assertions="<<checks<<" fake_NVS_and_GPIO_only=true\n";
}
