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
#include "../firmware/src/diagnostics.cpp"
#include <iostream>
unsigned checks=0;
void check(bool v){++checks;if(!v)throw std::runtime_error("kit sensor assertion");}
void advance(unsigned ms){const auto end=host_board::now_us+uint64_t(ms)*1000;
  while(host_board::now_us<end){auto before=host_board::now_us;loop();if(before==host_board::now_us)++host_board::now_us;}}
int main(){try{
 setup();check(M4_RTC_CLK==-1 && M4_RTC_DAT==-1 && M4_RTC_CE==-1);
 check(M4_DIAGNOSTIC_MODE==7 && M4_QUAD_ULTRASONIC==1 && M4_CURRENT_HARDWARE_PROFILE==1);
 for(int pin:{2,6,7,10,12,13,14,15,16,17,18})check(host_board::touches[pin]==0);
 command("tare 15");command("save YES");command("buzzer-driver ACTIVE_HIGH CONFIRM");
 check(host_board::nvs_writes==0 && host_board::touches[2]==0);
 Serial0.tx.clear();report();check(Serial0.tx.find("WARMING_UP")!=std::string::npos);
 command("ultra-select hc1 CONFIRM");command("ultra-select jsn1 CONFIRM");command("ultra-select hc2 CONFIRM");command("ultra-select jsn2 CONFIRM");
 command("ultra-multiplex CONFIRM");advance(2000);
 check(host_board::overlaps==0 && dual.guardMs()==80);
 for(unsigned i=0;i<4;++i)check(dual.lastValid(i).valid);
 host_board::water_echo.missing=true;advance(1500);Serial0.tx.clear();report();
 check(Serial0.tx.find("\"measurement_state\":\"NO_ECHO\"")!=std::string::npos);
 check(!water.distance.raw.valid && approach.distance.raw.valid);
 host_board::water_echo.missing=false;host_board::water_echo.distance_cm=450;advance(1500);Serial0.tx.clear();report();
 check(Serial0.tx.find("\"measurement_state\":\"OUT_OF_RANGE\"")!=std::string::npos);
 check(!water.distance.raw.valid && host_board::overlaps==0);
 while(dual.busy())advance(1);
 host_board::now_us=61000000;advance(200);check(pir_telemetry.valid());
 host_board::levels[11]=true;advance(50);check(!pir_telemetry.valid());advance(200);check(pir_telemetry.valid() && pir_telemetry.motion());
 check(host_board::touches[6]==0 && host_board::touches[7]==0 && host_board::touches[2]==0 && host_board::nvs_writes==0);
 std::cout<<"KIT_SENSOR_PASS checks="<<checks<<" FAKE_GPIO_ONLY physical_pass=false\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
