#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define DOG_BUZZER_DIAGNOSTIC 1
#include "../firmware/src/dog_buzzer_diagnostic.cpp"
#include <iostream>
unsigned checks=0;
void check(bool v){++checks;if(!v)throw std::runtime_error("kit buzzer assertion");}
int main(){try{
 setup();check(host_board::levels[2] && buzzer.phase()==0 && !driver_confirmed);
 kitCommand("test CONFIRM");check(tests_started==0 && host_board::levels[2]);
 kitCommand("buzzer-driver ACTIVE_HIGH CONFIRM");check(!driver_confirmed);
 kitCommand("buzzer-driver ACTIVE_LOW CONFIRM");check(driver_confirmed && buzzer.phase()==0);
 kitCommand("test CONFIRM");check(tests_started==1 && buzzer.phase()==1 && !host_board::levels[2]);
 host_board::now_us=199000;loop();check(buzzer.phase()==1);
 host_board::now_us=200000;loop();check(buzzer.phase()==2 && host_board::levels[2]);
 host_board::now_us=400000;loop();check(buzzer.phase()==3 && !host_board::levels[2]);
 host_board::now_us=600000;loop();check(buzzer.phase()==0 && buzzer.completed()==1 && host_board::levels[2]);
 kitCommand("test CONFIRM");check(tests_started==1);
 host_board::now_us=61000000;kitCommand("test CONFIRM");check(tests_started==2);
 kitCommand("stop");check(buzzer.phase()==0 && host_board::levels[2]);
 host_board::now_us=122000000;kitCommand("test CONFIRM");kitCommand("stop");check(tests_started==3);
 host_board::now_us=183000000;kitCommand("test CONFIRM");check(tests_started==3 && buzzer.phase()==0);
 for(unsigned pin=0;pin<64;++pin)if(pin!=2)check(host_board::touches[pin]==0);
 check(host_board::nvs_writes==0);
 std::cout<<"KIT_BUZZER_PASS checks="<<checks<<" FAKE_GPIO2_ONLY physical_pass=false\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
