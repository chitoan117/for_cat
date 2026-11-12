#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define M4_SENSOR_BRINGUP 1
#define M4_CURRENT_HARDWARE_PROFILE 1
#define M4_QUAD_ULTRASONIC 1
#define FORCAT_MANUAL_STATION 1
#include <cstdint>
uint32_t esp_random(){return 123456;}
#include "../firmware/src/cat_continuous.cpp"
#include <iostream>
unsigned checks=0;void check(bool b){if(!b)throw std::runtime_error("app check "+std::to_string(checks));++checks;}
namespace hw=host_board;
uint32_t seq=0,ai_seq=0;float mass=0;uint64_t last_adc=0;
void advance(unsigned ms){const auto end=hw::now_us+ms*1000ull;while(hw::now_us<end){
    if(hw::adc_bits.empty()&&hw::now_us-last_adc>=100000){last_adc=hw::now_us;hw::queue_adc(100+int(mass*100));}
    loop();hw::now_us+=20;
}}
std::string wire(const std::string& op){std::string s="FC1 "+std::to_string(boot_id)+" "+std::to_string(++seq)+" "+std::to_string(millis())+" "+op;
    char b[8];snprintf(b,sizeof(b),"*%04X\n",cat_test::crc(s.c_str(),unsigned(s.size())));return s+b;}
void send(const std::string& op){Serial0.input(wire(op));advance(3);}
void step(){send("HB");send("CAT "+std::to_string(++ai_seq)+" 0 950 1");advance(94);}
int main(){try{
    m4::CalibrationRecord rec;check(rec.hx711.tare(100)&&rec.hx711.reference(1100,10));uint8_t bytes[m4::calibration_record::SIZE];check(m4::calibration_record::encode(rec,bytes));
    hw::nvs["m4-calibration/sensors-v2"]={bytes,bytes+sizeof(bytes)};const auto original=hw::nvs["m4-calibration/sensors-v2"];
    setup();advance(450);check(hw::ledc_attaches==0&&hw::nvs_writes==0&&!configured&&!permit);
    Serial0.input("hx\nstatus\n");advance(10);
    check(receiver.last()==0&&!permit&&hw::ledc_attaches==0&&hw::nvs_writes==0&&control.state()==State::Disarmed);
    check(Serial0.tx.find("\"raw_valid\":true")!=std::string::npos&&Serial0.tx.find("\"calibration_load\":\"LOADED\"")!=std::string::npos);
    send("HB");send("INSPECT CLOSED");check(inspected&&!configured);send("ARM A");check(!permit&&hw::ledc_attaches==0);
    // MOCK ONLY: substitute measured configuration, exercise the real setup/loop,
    // parser, journal, HX711 bit pulses and acoustic driver; no production defaults.
    auto cfg=user_settings::settings();cfg.pulses={1450,1550,1500,1495,1505,1530,1470,true,true,true};
    cfg.opening_ms=300;cfg.closing_ms=400;cfg.travel_timing_verified=true;
    configured=control.configure(cfg);check(configured);hc_active=hc.begin({{12,true},{13,true},2,400,30000,.0343f});check(hc_active);
    hw::food_echo.distance_cm=15;send("ARM A");check(permit&&hw::ledc_attaches==0);
    for(int i=0;i<20&&control.state()!=State::Opening;++i)step();check(control.state()==State::Opening&&journal.pending);
    for(float g:{10.f,20.f,24.f}){mass=g;step();}check(control.state()!=State::Closing);
    mass=25;for(int i=0;i<4&&control.state()!=State::Closing;++i)step();check(control.state()==State::Closing);
    mass=35;for(int i=0;i<30&&control.state()!=State::AwaitingOwner;++i)step();check(control.state()==State::AwaitingOwner&&control.actualGrams()==35);
    check(journal.pending&&journal.last==1&&gate.visited()&&!permit&&hw::ledc_attaches==1);
    for(int i=0;i<12;++i)step();check(hw::ledc_attaches==1&&journal.pending);
    check(hw::touches[7]==0&&hw::touches[2]==0);check(hw::nvs["m4-calibration/sensors-v2"]==original);
    PersistentJournal restarted;restarted.load();check(restarted.initialized&&restarted.pending&&restarted.last==1);
    Serial0.input("STOP\n");advance(150);check(control.state()==State::Fault&&journal.pending);
    send("INSPECT CLOSED");check(!journal.pending&&journal.last==1&&control.highwater()==1);
    check(hw::critical_errors==0&&hw::overlaps==0);
    std::cout<<"APP_LOOP_PASS checks="<<checks<<"\n";
}catch(const std::exception& e){std::cerr<<e.what()<<" state="<<name(control.state())<<" reason="<<unsigned(control.reason())<<"\n";return 1;}}
