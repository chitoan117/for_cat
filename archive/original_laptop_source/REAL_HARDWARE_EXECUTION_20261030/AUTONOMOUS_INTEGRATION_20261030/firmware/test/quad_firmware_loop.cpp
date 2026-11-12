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
#include "../src/diagnostics.cpp"
#include <iostream>
unsigned assertions=0;
void check(bool ok){++assertions;if(!ok)throw std::runtime_error("quad loop assertion failed");}
int main(){
 setup();
 check(M4_RTC_CLK==-1 && M4_RTC_DAT==-1 && M4_RTC_CE==-1);
 for(int pin:{6,7,10,12,13,14,15,16,17,18})check(host_board::touches[pin]==0);
 check(pins_io.inputAllowed(10) && !pins_io.outputAllowed(10));
 check(!pins_io.inputAllowed(6) && !pins_io.inputAllowed(7));
 command("ultra-multiplex CONFIRM");for(unsigned i=0;i<4;++i)check(!dual.enabled(i));
 command("set-utc 2026-10-27T00:00:00Z CONFIRM");
 check(host_board::rtc.history.empty());
 command("SERVO OPEN");command("PUMP ON");command("FEED_REQUEST");
 check(host_board::touches[6]==0 && host_board::touches[7]==0 && host_board::nvs_writes==0);
 command("ultra-select hc2 CONFIRM");check(dual.enabled(2));
 check(host_board::pin_modes[16]==OUTPUT && host_board::pin_modes[17]==INPUT);
 command("ultra-off CONFIRM");check(!dual.enabled(2));
 command("ultra-select jsn2 CONFIRM");check(dual.enabled(3));
 check(host_board::pin_modes[18]==OUTPUT && host_board::pin_modes[10]==INPUT);
 command("ultra-off CONFIRM");
 check(dual.guardMs()==80);
 command("ultra-guard 100 CONFIRM");check(dual.guardMs()==100);
 command("ultra-guard 61 CONFIRM");check(dual.guardMs()==100);
 command("ultra-guard 60 CONFIRM extra");check(dual.guardMs()==100);
 command("ultra-guard 80 CONFIRM");check(dual.guardMs()==80);
 Serial0.tx.clear();report();std::cout<<Serial0.tx;
 check(Serial0.tx.find("\"ultrasonic\":{")!=std::string::npos);
 check(Serial0.tx.find("\"rtc_type\":\"NONE\"")!=std::string::npos);
 check(Serial0.tx.find("\"ultrasonic_guard_ms\":80")!=std::string::npos);
 check(host_board::touches[6]==0 && host_board::touches[7]==0 && !host_board::ledc_attached);
 // Synthetic echo success must retain the legacy bridge's valid=>ACK invariant.
 command("ultra-select hc1 CONFIRM");
 host_board::food_echo.distance_cm=35;
 const auto end=host_board::now_us+1300000;
 while(host_board::now_us<end){const auto before=host_board::now_us;loop();if(host_board::now_us==before)++host_board::now_us;}
 Serial0.tx.clear();report();std::cout<<Serial0.tx;
 check(food_echo_ack && !water_echo_ack && snapshot.approach_distance_cm.valid);
 std::cout<<"QUAD_FIRMWARE_LOOP_SOFTWARE_READY assertions="<<assertions<<"\n";
}
