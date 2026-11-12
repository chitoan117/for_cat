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
#define MANUAL_STATION_HOST_TEST 1
#include "../firmware/src/manual_station.cpp"
#include <fstream>
#include <iostream>
#include <stdexcept>

unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("integration check="+std::to_string(checks));}
void advance(unsigned ms){const auto end=host_board::now_us+uint64_t(ms)*1000;
  while(host_board::now_us<end){auto before=host_board::now_us;loop();if(before==host_board::now_us)++host_board::now_us;}}
void send(const std::string& text){Serial0.input(text+"\n");for(unsigned n=0;n<128;++n)loop();}
uint32_t seq=0;
std::string packet(const std::string& text){return "@"+std::to_string(station.bootNonce())+" "+std::to_string(station.session())+" "+std::to_string(++seq)+" "+text;}
void auth(const std::string& text){send(packet(text));}
void session(){send("session begin");check(station.session()!=0);seq=0;}
void configure(){auth("servo configure 1450 1550 1500 1550 CONFIRM");check(station.servo.configured());}
int main(int argc,char** argv){try{
  if(argc!=3)return 2;
  const std::string which=argv[1];setup();for(unsigned n=0;n<128;++n)loop();
  check(!host_board::ledc_attached && !pump_output.commanded() && !station.buzzerEnabled());
  check(host_board::touches[2]==0 && host_board::nvs_writes==0);
#if MANUAL_PUMP_OFF_LEVEL<0
  check(host_board::touches[7]==0);
#else
  check(host_board::levels[7]==bool(MANUAL_PUMP_OFF_LEVEL));
#endif
  if(which=="boot_and_bounds"){
    send("servo arm YES");send("pump arm YES");check(!host_board::ledc_attached && !pump_output.commanded());
    session();auth("servo configure 1000 2000 1500 1800 CONFIRM");check(!station.servo.configured());
    auth("servo configure 4294968746 1550 1500 1550 CONFIRM");check(!station.servo.configured());
    configure();auth("servo arm YES");check(host_board::ledc_attached);
    auth("servo set 1600");check(station.servo.moves()==0);auth("servo open");check(station.servo.moves()==1);
    advance(700);check(!host_board::ledc_attached && !station.busy());
  }else if(which=="mutual_exclusion"){
    session();configure();auth("servo arm YES");auth("pump arm YES");check(!station.pumpActive());
    auth("servo disarm");advance(450);check(!station.servoActive());
    auth("pump arm YES");
#if MANUAL_PUMP_OFF_LEVEL>=0
    check(station.pumpActive());auth("servo arm YES");check(!station.servoActive());
    auth("pump on 100");check(pump_output.commanded());advance(200);check(!pump_output.commanded());
#else
    check(!station.pumpActive() && host_board::touches[7]==0);
#endif
  }else if(which=="pump_timeout_and_limits"){
    session();auth("pump arm YES");auth("pump on 501");check(!pump_output.commanded());
#if MANUAL_PUMP_OFF_LEVEL>=0
    auth("pump on 100");check(pump_output.commanded());Serial0.tx_capacity=0;
    advance(200);check(!pump_output.commanded() && !station.pumpActive());Serial0.tx_capacity=64;
    check(host_board::levels[7]==bool(MANUAL_PUMP_OFF_LEVEL));
    auth("pump arm YES");check(!station.pumpActive());advance(1200);
    for(unsigned n=0;n<2;++n){auth("pump arm YES");auth("pump on 20");advance(1200);}
    auth("pump arm YES");check(!station.pumpActive() && station.pump.pulses()==3);
#else
    check(!pump_output.commanded() && host_board::touches[7]==0);
#endif
  }else if(which=="replay_and_emergency"){
    session();configure();auth("servo arm YES");const auto move=packet("servo open");send(move);check(host_board::ledc_attached);
    send(move);check(station.fault() && !host_board::ledc_attached && !pump_output.commanded());
    send("session begin");check(station.session()==0 && !host_board::ledc_attached);
  }else if(which=="reconnect_budgets"){
    session();configure();
    for(unsigned n=0;n<3;++n){auth("servo arm YES");auth("servo open");advance(700);session();}
    auth("servo arm YES");check(!host_board::ledc_attached && station.servo.arms()==3);
    const auto old_link=station.session();session();check(station.session()!=old_link);
    send("@1234567 "+std::to_string(old_link)+" 4294967295 servo arm YES");check(!host_board::ledc_attached);
  }else if(which=="backpressure_deadline"){
    session();configure();auth("servo arm YES");auth("servo open");Serial0.tx_capacity=0;
    advance(700);check(!host_board::ledc_attached && !station.busy());
    Serial0.tx_capacity=64;
  }else if(which=="clock_and_input_faults"){
    session();configure();auth("servo arm YES");host_board::now_us-=100000;loop();
    check(station.fault() && !host_board::ledc_attached);
    send("stop");check(station.fault());
  }else if(which=="overlong_input"){
    session();configure();auth("servo arm YES");send(std::string(240,'x'));
    check(station.fault() && !host_board::ledc_attached && !pump_output.commanded());
  }else if(which=="sensor_calibration_telemetry"){
    session();auth("hx import -698000 -1064.4473 CONFIRM");check(scale.calibration.valid());
    const auto original=scale.calibration.tare_counts;auth("tare 15");auth("cal 35 15");auth("save YES");
    check(scale.calibration.tare_counts==original && host_board::nvs_writes==0);
    for(const char* channel:{"hc1","jsn1","hc2","jsn2"})auth(std::string("ultra-select ")+channel+" CONFIRM");
    auth("ultra-multiplex CONFIRM");advance(2100);check(host_board::overlaps==0);
    for(unsigned i=0;i<4;++i)check(dual.lastValid(i).valid);
    while(dual.busy())advance(1);
    auth("ultra-off CONFIRM");send("status");
    check(Serial0.tx.find("\"mode\":\"diag_manual_station\"")!=std::string::npos);
    check(Serial0.tx.find("\"mode\":\"diag_current_hardware\"")==std::string::npos);
    check(host_board::touches[2]==0 && host_board::nvs_writes==0);
    check(!protocolSerial().overflowed() && !station.fault());
  }else if(which=="buzzer_manual_only"){
    session();auth("buzzer test CONFIRM");check(host_board::touches[2]==0);
    auth("buzzer-driver ACTIVE_LOW CONFIRM");check(host_board::levels[2]);
    auth("buzzer test CONFIRM");check(buzzer_output.active());auth("servo arm YES");check(!station.servoActive());
    advance(800);check(!buzzer_output.active() && host_board::levels[2]);
    auth("buzzer test CONFIRM");check(!buzzer_output.active());
  }else return 2;
  // Leave the fault/replay branch without accepting another session.
  check(host_board::nvs_writes==0);
  // Capture remaining queued UART bytes without starting new sensor work/reports.
  for(unsigned n=0;n<128;++n)protocolSerial().drain();
  std::ofstream(argv[2])<<Serial0.tx;
  std::cout<<"INTEGRATED_PASS case="<<which<<" checks="<<checks<<" off_level="<<MANUAL_PUMP_OFF_LEVEL<<" source=SIMULATED physical_pass=false\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
