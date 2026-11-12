#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define DOG_BUZZER_DIAGNOSTIC 1
#include "../src/dog_buzzer_diagnostic.cpp"
#include <iostream>
int main(){
 setup();if(!host_board::levels[2])return 1;
 Serial0.input("test CONFIRM\n");loop();if(host_board::levels[2])return 2;
 host_board::now_us=100000;Serial0.input("test CONFIRM\n");loop();
 host_board::now_us=200000;loop();if(!host_board::levels[2])return 3;
 host_board::now_us=400000;loop();if(host_board::levels[2])return 4;
 host_board::now_us=600000;loop();if(!host_board::levels[2] || buzzer.completed()!=1)return 5;
 for(int p=0;p<64;++p)if(p!=2 && host_board::touches[p])return 6;
 std::cout<<"BUZZER_DIAGNOSTIC_LOOP_PASS GPIO2_only=true mock_only=true\n";
}
