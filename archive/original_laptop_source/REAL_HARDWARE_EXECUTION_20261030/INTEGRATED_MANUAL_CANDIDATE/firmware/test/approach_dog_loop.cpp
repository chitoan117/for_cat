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
#define M4_DOG_WARNING 1
#define DOG_TEST_BOOT_NONCE 123
#include "../src/diagnostics.cpp"
#include <iostream>
#include <fstream>
#include <sstream>
unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){std::cerr<<"FAIL line"<<__LINE__<<": "<<#x<<"\n";return 1;}}while(0)
void run(unsigned ms){
  const auto end=host_board::now_us+ms*1000ULL;auto adc_at=host_board::now_us;
  while(host_board::now_us<end){
    if(host_board::now_us>=adc_at){host_board::queue_adc(-670000);adc_at+=100000;}
    const auto before=host_board::now_us;loop();if(host_board::now_us==before)++host_board::now_us;
  }
}
void frame(uint32_t id,uint8_t cmd,const uint8_t* payload,uint16_t size){
  uint8_t bytes[uart_v1::MAX_FRAME];size_t n=0;uart_v1::encode(id,cmd,payload,size,bytes,sizeof(bytes),n);
  Serial0.input(std::string(reinterpret_cast<char*>(bytes),n));
}
int main(int argc,char** argv){
 host_board::levels[21]=true;host_board::oled_connected=true;host_board::food_echo.distance_cm=19;
 setup();CHECK(host_board::levels[2] && host_board::pin_modes[2]==OUTPUT);
 host_board::sensitive_acquisition=[](){return dual.busy();};
 for(unsigned i=0;i<4;++i)CHECK(dual.enabled(i));
 uint8_t hello[9]{1};dog_wire::put(hello+1,123);dog_wire::put(hello+5,456);frame(1,dog_wire::HELLO,hello,9);
 run(2500);CHECK(approach_gate.state()==m4::approach_dog::State::NOT_ARMED && dog_buzzer.completed()==0 && host_board::levels[2]);
 host_board::food_echo.distance_cm=40;run(3000);CHECK(approach_gate.state()==m4::approach_dog::State::ARMED);
 host_board::food_echo.distance_cm=19;run(1800);CHECK(approach_gate.state()==m4::approach_dog::State::CONFIRMED);
 uint8_t warning[21]{1};dog_wire::put(warning+1,123);dog_wire::put(warning+5,456);dog_wire::put(warning+9,approach_gate.event());
 dog_wire::put(warning+13,approach_gate.eventAt());dog_wire::put(warning+17,approach_gate.eventAt()+1500);
 const auto raw_at=scale.raw.sampled_at_ms,pulses=host_board::food_echo.pulses,oled_packets=host_board::oled_packets;
 frame(2,dog_wire::WARNING,warning,21);run(80);CHECK(dog_buzzer.active());
 Serial0.tx_capacity=0;host_board::levels[21]=false;run(650); // TX pressure must not block acoustic/HX/button/buzzer ticks
 CHECK(dog_buzzer.completed()==1 && host_board::levels[2]);
 CHECK(scale.raw.sampled_at_ms>raw_at && host_board::food_echo.pulses>pulses && button.press_count==1);
 Serial0.tx_capacity=64;run(1500);CHECK(host_board::oled_packets>oled_packets);
 CHECK(!protocolSerial().overflowed());CHECK(host_board::overlaps==0 && host_board::other_work_during_echo==0);
 CHECK(host_board::touches[6]==0 && host_board::touches[7]==0 && !host_board::ledc_attached);
 CHECK(host_board::critical_depth==0 && host_board::critical_errors==0);
 frame(2,dog_wire::WARNING,warning,21);run(700);CHECK(dog_buzzer.completed()==1);
 CHECK(Serial0.tx.find("APPROACH {")!=std::string::npos && Serial0.tx.find("\"ultrasonic\":{")!=std::string::npos);
 std::istringstream recorded(Serial0.tx);std::string line;bool saved=false;
 while(std::getline(recorded,line))if(!line.empty() && line[0]=='{'){
   CHECK(line.size()<=4096);
   if(!saved && argc==2){std::ofstream output(argv[1]);output<<line; saved=true;}
 }
 if(argc==2)CHECK(saved);
 std::cout<<"APPROACH_DOG_LOOP_PASS assertions="<<checks<<" fake_io_only=true\n";
}
