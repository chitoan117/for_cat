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
#define FORCAT_MANUAL_STATION 1
#define FORCAT_DUAL_STATION 1
#define MANUAL_STATION_HOST_TEST 1
#include "../firmware/src/dual_station.cpp"
#include <fstream>
#include <iostream>
#include <string>
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("dual check="+std::to_string(checks));}
void runLoops(unsigned n){while(n--)loop();}
void send(const std::string& text){Serial0.input(text+"\n");runLoops(128);}
uint32_t sequence=0;
void commandPacket(const std::string& text){send("@"+std::to_string(station.bootNonce())+" "+std::to_string(station.session())+" "+std::to_string(++sequence)+" "+text);}
void session(){send("session begin");check(station.session()!=0);sequence=0;}
void configure(){commandPacket("servo configure 1450 1550 1500 1550 CONFIRM");check(station.servo.configured());}
void advance(unsigned ms){const auto end=host_board::now_us+uint64_t(ms)*1000;while(host_board::now_us<end)loop();}
void frame(uint32_t id,uint8_t op,const uint8_t* p,uint16_t n,bool bad=false){
    uint8_t b[268]{};size_t count=0;check(uart_v1::encode(id,op,p,n,b,sizeof(b),count));if(bad)b[count-1]^=1;
    Serial0.input(std::string(reinterpret_cast<char*>(b),count));runLoops(128);
}
int main(int argc,char** argv){try{
    if(argc!=3)return 2;const std::string which=argv[1];setup();runLoops(128);
    check(!host_board::ledc_attached && host_board::touches[7]==0 && host_board::touches[2]==0 && host_board::nvs_writes==0);
    if(which=="boot"){
        check(dual_servo_bus.owner()==ExclusiveServoBus::IdleRole);
        for(int pin:{12,13,14,15,16,17,18,10})check(host_board::touches[pin]==0);
    }else if(which=="manual_with_binary_hello"){
        session();configure();commandPacket("servo arm YES");commandPacket("servo open");
        check(host_board::ledc_attached && dual_servo_bus.owner()==ExclusiveServoBus::ManualRole);
        uint8_t p[5]{1};feed_link::put32(p+1,123);frame(123,feed_link::HELLO,p,5);
        check(!station.fault() && station.servo.moves()==1);advance(700);
        check(!host_board::ledc_attached && dual_servo_bus.owner()==ExclusiveServoBus::IdleRole);
    }else if(which=="binary_cannot_arm"){
        uint8_t hello[5]{1};feed_link::put32(hello+1,123);frame(123,feed_link::HELLO,hello,5);
        uint32_t boot=0,link=0;dog_wire::Parser p;
        for(const auto c:Serial0.tx)p.feed(static_cast<uint8_t>(c),millis(),[&](uint32_t,uint8_t op,const uint8_t* payload,uint16_t n){
            if(op==feed_link::CAPABILITIES&&n==23){boot=feed_link::get32(payload+1);link=feed_link::get32(payload+5);check(!(payload[13]&1u) && !(payload[13]&4u));}});
        check(boot && link);uint8_t header[13]{1};feed_link::put32(header+1,boot);feed_link::put32(header+5,link);feed_link::put32(header+9,1);
        frame(0,feed_link::ARM,header,13);check(!host_board::ledc_attached && station.servo.arms()==0);
    }else if(which=="malformed_binary_manual_deadline"){
        session();configure();commandPacket("servo arm YES");
        uint8_t p[5]{1};feed_link::put32(p+1,123);frame(123,feed_link::HELLO,p,5,true);
        check(station.servo.moves()==0);advance(2400);check(!host_board::ledc_attached);
    }else if(which=="stop_latches_both_domains"){
        session();configure();commandPacket("servo arm YES");commandPacket("servo open");send("stop");
        check(station.fault() && !host_board::ledc_attached);send("session begin");check(station.session()==0);
        check(!dual_servo_bus.feed().start(1500));check(!host_board::ledc_attached);
    }else if(which=="bus_peer_cannot_detach_or_start"){
        session();configure();commandPacket("servo arm YES");
        check(!dual_servo_bus.feed().off());check(host_board::ledc_attached);
        check(!dual_servo_bus.feed().start(1500));check(dual_servo_bus.owner()==ExclusiveServoBus::ManualRole);
        send("stop");check(dual_servo_bus.owner()==ExclusiveServoBus::IdleRole);
    }else if(which=="nonblocking_deadline"){
        session();configure();commandPacket("servo arm YES");commandPacket("servo open");Serial0.tx_capacity=0;
        advance(700);check(!host_board::ledc_attached);Serial0.tx_capacity=64;
    }else if(which=="telemetry_identity_and_no_nvs"){
        session();commandPacket("hx import -698000 -1064.4473 CONFIRM");check(scale.calibration.valid());
        commandPacket("save YES");check(host_board::nvs_writes==0);
    }else return 2;
    for(unsigned n=0;n<128;++n)protocolSerial().drain();
    Serial0.tx.clear();snapshot.sampled_at_ms=millis();report();for(unsigned n=0;n<128;++n)protocolSerial().drain();
    check(Serial0.tx.find("\"mode\":\"diag_dual_station\"")!=std::string::npos);
    check(Serial0.tx.find("\"physical_enable\":false")!=std::string::npos);
    check(host_board::touches[7]==0 && host_board::touches[2]==0 && host_board::nvs_writes==0);
    std::ofstream(argv[2])<<Serial0.tx;
    std::cout<<"DUAL_PASS case="<<which<<" checks="<<checks<<" MOCK_GPIO_ONLY physical_pass=false\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
