#include <Arduino.h>
#include <cmath>
#include <cstring>
#include "board_config.h"
#include "current_hardware.h"
#include "serial_port.h"
#include "manual_station_policy.h"
#include "m4/ledc_servo.h"
#include "m4/arduino_io.h"
#include "m4/approach_dog_warning.h"
#if !defined(FORCAT_MANUAL_STATION) || FORCAT_MANUAL_STATION!=1 || !M4_SENSOR_BRINGUP || \
    M4_DIAGNOSTIC_MODE!=7 || !M4_QUAD_ULTRASONIC || !M4_CURRENT_HARDWARE_PROFILE || \
    ACTUATOR_OUTPUTS_ENABLED!=0 || SERVO_BENCH_MODE || PUMP_BENCH_MODE || DISPENSE_BENCH_MODE
#error "Dedicated manual station only; no normal/AI/isolated-main mixing"
#endif
#ifndef MANUAL_PUMP_OFF_LEVEL
#define MANUAL_PUMP_OFF_LEVEL -1
#endif
static_assert(MANUAL_PUMP_OFF_LEVEL>=-1 && MANUAL_PUMP_OFF_LEVEL<=1,"Measured OFF0/1 or INERT-1 only");
static_assert(current_hardware::SERVO_SIGNAL==6 && current_hardware::PUMP_CONTROL==7 && current_hardware::DOG_WARNING_BUZZER==2,"No GPIO reassignment");
#if !defined(MANUAL_STATION_HOST_TEST)
#include <esp_system.h>
#endif
#if defined(ESP_PLATFORM) && defined(MANUAL_STATION_HOST_TEST)
#error "Host test nonce cannot be built into real ESP firmware"
#endif

namespace {
class PumpOutput final:public m4::pump_bench::Output {
 public:
  bool on()override{
#if MANUAL_PUMP_OFF_LEVEL>=0
    digitalWrite(7,MANUAL_PUMP_OFF_LEVEL?LOW:HIGH);commanded_=true;return true;
#else
    return false;
#endif
  }
  bool off()override{
#if MANUAL_PUMP_OFF_LEVEL>=0
    digitalWrite(7,MANUAL_PUMP_OFF_LEVEL?HIGH:LOW);pinMode(7,OUTPUT);
    digitalWrite(7,MANUAL_PUMP_OFF_LEVEL?HIGH:LOW);
#endif
    commanded_=false;return true;
  }
  bool commanded()const{return commanded_;}
 private:bool commanded_=false;
};
class BuzzerOutput final:public manual_station::BuzzerOutput {
  m4::ArduinoPins pins_;
  m4::approach_dog::Buzzer buzzer_{pins_};
  bool enabled_=false;
 public:
  bool enable()override{if(!enabled_)buzzer_.begin();enabled_=true;return true;}
  bool start(uint32_t now)override{return enabled_ && buzzer_.start(now);}
  void tick(uint32_t now)override{if(enabled_)buzzer_.tick(now);}
  void stop()override{if(enabled_)buzzer_.begin();}
  bool active()const override{return enabled_ && buzzer_.active();}
};
auto& servo_output=dual_servo_bus.manual();
PumpOutput pump_output;
BuzzerOutput buzzer_output;
manual_station::Station station(servo_output,pump_output,buzzer_output,MANUAL_PUMP_OFF_LEVEL>=0);
bool manualServoActive(){return station.servoActive();}
bool manualPumpActive(){return station.pumpActive();}
const char* manualServoState(){return m4::servo_bench::name(station.servo.state());}
const char* manualPumpState(){return m4::pump_bench::name(station.pump.state());}
void manualTelemetry(){
  const auto positions=station.servo.positions();
  protocolSerial().printf("\"manual_station\":{\"schema_version\":1,\"boot_nonce\":%lu,\"session\":%lu,\"last_sequence\":%lu,"
    "\"fault_latched\":%s,\"servo_gpio\":6,\"servo_state\":\"%s\",\"servo_pulse_us\":%u,\"servo_arms\":%u,"
    "\"servo_close_us\":%u,\"servo_open_us\":%u,\"pump_gpio\":7,\"pump_supported\":%s,\"pump_off_level\":%d,"
    "\"pump_state\":\"%s\",\"pump_commanded_on\":%s,\"pump_pulses\":%u,\"buzzer_gpio\":2,\"buzzer_enabled\":%s,"
    "\"buzzer_active\":%s,\"automatic_execution\":false,\"mechanical_close_verified\":false,\"physical_pass\":false},",
    static_cast<unsigned long>(station.bootNonce()),static_cast<unsigned long>(station.session()),static_cast<unsigned long>(station.sequence()),
    station.fault()?"true":"false",manualServoState(),station.servo.pulse(),station.servo.arms(),positions.close_us,positions.open_us,
    station.pumpEnabled()?"true":"false",MANUAL_PUMP_OFF_LEVEL,manualPumpState(),pump_output.commanded()?"true":"false",station.pump.pulses(),
    station.buzzerEnabled()?"true":"false",buzzer_output.active()?"true":"false");
}
} // namespace

// Reuses complete existing HX711/quad-ultrasound/PIR/OLED/button driver station.
// This candidate copy has distinct mode/identity and no calibration save path.
#include "diagnostics.cpp"

namespace {
char manual_line[192]{};
unsigned manual_used=0;
bool manual_discard=false;
void reply(const char* result){protocolSerial().printf("MANUAL_RESULT boot=%lu session=%lu seq=%lu result=%s\r\n",
  static_cast<unsigned long>(station.bootNonce()),static_cast<unsigned long>(station.session()),
  static_cast<unsigned long>(station.sequence()),result);}
bool stopSensors(){return !dual.busy() && dual.disableAll();}
void handleAscii(const char* line){
  const auto now=millis();station.tick(now);
  if(std::strcmp(line,"stop")==0 || std::strcmp(line,"servo stop")==0){hybridAbort();station.emergency();stopSensors();reply("STOP_LATCHED_PWM_OFF_PUMP_OFF_COMMAND_NOT_PHYSICAL_PROOF");return;}
  if(std::strcmp(line,"status")==0 || std::strcmp(line,"servo status")==0 || std::strcmp(line,"pump status")==0){
    snapshot.sampled_at_ms=now;report();return;
  }
  if(std::strcmp(line,"session begin")==0){
    if(!stopSensors()){reply("REJECTED_ACQUISITION_BUSY");return;}
    station.beginSession(now);reply(station.session()?"SESSION_NO_OUTPUT_ACTIVATION":"SESSION_REJECTED");return;
  }
  uint32_t boot=0,session=0,sequence=0;const char* p=line;
  if(*p++!='@' || !manual_station::integer(p,boot) || !manual_station::nextInteger(p,session) ||
     !manual_station::nextInteger(p,sequence) || *p++!=' ' || !*p || !station.authorize(boot,session,sequence,now)){
    if(station.busy())station.emergency();reply("REJECTED_SESSION_SEQUENCE_OR_SYNTAX");return;
  }
  if(std::strcmp(p,"servo arm YES")==0 || std::strcmp(p,"pump arm YES")==0 || std::strcmp(p,"buzzer test CONFIRM")==0){
    if(!stopSensors()){reply("REJECTED_ACQUISITION_BUSY");return;}
  }
  if(std::strncmp(p,"ultra-",6)==0 || std::strncmp(p,"weight-stability ",17)==0){
    if(station.busy() || station.fault()){reply("REJECTED_OUTPUT_ACTIVE_OR_FAULT");return;}
    command(p);return; // existing bounded sensor commands; ECHO electrical review is still external
  }
  if(std::strncmp(p,"hx import ",10)==0){
    if(station.busy() || station.fault()){reply("REJECTED_OUTPUT_ACTIVE_OR_FAULT");return;}
    double offset=0,factor=0;char confirm[8]{},extra=0;
    if(std::sscanf(p,"hx import %lf %lf %7s %c",&offset,&factor,confirm,&extra)==3 &&
       !std::strcmp(confirm,"CONFIRM") && std::isfinite(offset) && std::isfinite(factor) && factor!=0){
      m4::ScaleCalibration exact{true,true,offset,1.0/factor};
      if(exact.valid()){calibration.hx711=exact;copyCalibration();reply("EXACT_OWNER_COEFFICIENTS_RAM_ONLY_NO_TARE_NO_REFIT_NO_NVS_WRITE");return;}
    }
    reply("REJECTED_INVALID_CALIBRATION");return;
  }
  reply(station.command(p,now));station.tick(now);
}
void manualRx(){
  for(unsigned n=0;n<32 && protocolSerial().available()>0;++n){
    const int byte=protocolSerial().read();
    if(hybridFeedByte(static_cast<uint8_t>(byte),millis())){manual_used=0;manual_discard=false;continue;}
    if(byte=='\r'||byte=='\n'){
      if(!manual_discard && manual_used){manual_line[manual_used]=0;handleAscii(manual_line);}
      manual_used=0;manual_discard=false;
    }else if(byte>=32 && byte<=126 && !manual_discard){
      if(manual_used+1<sizeof(manual_line))manual_line[manual_used++]=static_cast<char>(byte);
      else{manual_discard=true;manual_used=0;station.emergency();}
    }else{manual_discard=true;manual_used=0;if(station.busy())station.emergency();}
  }
}
} // namespace

void manualSetup(){
#if defined(MANUAL_STATION_HOST_TEST)
  station.boot(1234567,millis());
#else
  const auto nonce=esp_random();station.boot(nonce?nonce:1,millis());
#endif
  sensorSetup();
  protocolSerial().println("MANUAL_STATION_V1: NO AI/FEED/AUTO. BOOT DISARMED. PUMP POLARITY GATED. BUZZER DISABLED. SESSION ENVELOPE REQUIRED. stop=LATCHED OFF. RAM CALIBRATION DOES NOT SURVIVE RESET.");
}
void manualLoop(){
  station.tick(millis());
  if(protocolSerial().overflowed())station.emergency();
  // Avoid blocking I2C/HX/report work while any output is ARMED/moving/ON.
  if(!station.busy())sensorLoop();
  if(!dual.busy()){manualRx();protocolSerial().drain();}
  station.tick(millis());yield();
}
