#pragma once
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include "m4/servo_bench.h"
#include "m4/pump_bench.h"

namespace manual_station {
// Strict unsigned wire numbers: no signs, wraparound, suffixes or overflow.
inline bool integer(const char*& p,uint32_t& value) {
  if (*p<'0' || *p>'9') return false;
  errno=0;char* end=nullptr;const auto n=std::strtoull(p,&end,10);
  if(errno || n>UINT32_MAX || (*end && *end!=' '))return false;
  value=static_cast<uint32_t>(n);p=end;return true;
}
inline bool nextInteger(const char*& p,uint32_t& value) {
  if(*p!=' ')return false;
  ++p;return integer(p,value);
}
class BuzzerOutput {
 public:
  virtual ~BuzzerOutput()=default;
  virtual bool enable()=0;
  virtual bool start(uint32_t now)=0;
  virtual void tick(uint32_t now)=0;
  virtual void stop()=0;
  virtual bool active()const=0;
};

// Reuses qualified bounded servo/pump controllers; adds single-owner arbitration,
// per-boot/session/sequence fencing and a latched station-wide emergency stop.
class Station {
 public:
  m4::servo_bench::Controller servo;
  m4::pump_bench::Controller pump;
  static constexpr uint32_t lease_ms=5000;
  Station(m4::servo_bench::Output& s,m4::pump_bench::Output& p,BuzzerOutput& b,bool pump_enabled)
      :servo(s),pump(p),servo_io_(s),pump_io_(p),buzzer_(b),pump_enabled_(pump_enabled) {}
  void boot(uint32_t nonce,uint32_t now) {
    boot_=nonce;link_=sequence_=generation_=0;fault_=!nonce;
    clock_=true;last_now_=last_command_=now;buzzer_enabled_=false;buzzer_tests_=0;
    servo.boot();pump.boot();buzzer_.stop();
    if(servo.state()==m4::servo_bench::State::FAULT || pump.state()==m4::pump_bench::State::FAULT)emergency();
  }
  bool servoActive()const {
    return servo.state()!=m4::servo_bench::State::DISARMED && servo.state()!=m4::servo_bench::State::FAULT;
  }
  bool pumpActive()const {
    return pump.state()==m4::pump_bench::State::ARMED || pump.state()==m4::pump_bench::State::ON;
  }
  bool busy()const{return servoActive() || pumpActive() || buzzer_.active();}
  bool fault()const{return fault_;}
  bool pumpEnabled()const{return pump_enabled_;}
  bool buzzerEnabled()const{return buzzer_enabled_;}
  uint32_t bootNonce()const{return boot_;}
  uint32_t session()const{return link_;}
  uint32_t sequence()const{return sequence_;}
  void emergency() {
    fault_=true;link_=0;
    servo.emergencyStop();servo_io_.off();pump.stop(last_now_);
    // Retry the raw OFF once even if the pump controller already latched FAULT.
    pump_io_.off();buzzer_.stop();
  }
  void tick(uint32_t now) {
    if(fault_)return;
    if(clock_ && static_cast<uint32_t>(now-last_now_)>=0x80000000u){emergency();return;}
    clock_=true;last_now_=now;
    servo.tick(now);pump.tick(now);buzzer_.tick(now);
    if(servo.state()==m4::servo_bench::State::FAULT || pump.state()==m4::pump_bench::State::FAULT){emergency();return;}
    if(link_ && static_cast<uint32_t>(now-last_command_)>=lease_ms){
      if(busy())emergency();
      link_=0;
    }
  }
  uint32_t beginSession(uint32_t now) {
    tick(now);
    if(fault_)return 0;
    if(busy()){emergency();return 0;}
    if(generation_==UINT32_MAX){emergency();return 0;}
    // Never boot/reset controllers here: budgets/configuration survive reconnect.
    link_=++generation_;sequence_=0;last_command_=now;return link_;
  }
  bool authorize(uint32_t boot,uint32_t link,uint32_t seq,uint32_t now) {
    tick(now);
    if(fault_ || !boot || boot!=boot_ || !link_ || link!=link_ || !seq || seq<=sequence_){
      if(busy())emergency();
      return false;
    }
    sequence_=seq;last_command_=now;return true;
  }
  const char* command(const char* text,uint32_t now) {
    tick(now);
    if(fault_)return "FAULT_LATCHED_POWER_REVIEW_REQUIRED";
    if(std::strcmp(text,"keepalive")==0)return "OK";
    if(std::strncmp(text,"servo configure ",16)==0){
      if(busy())return "REJECTED_OTHER_OUTPUT_OR_BUSY";
      uint32_t a=0,b=0,c=0,d=0;const char* p=text+16;
      if(!integer(p,a)||!nextInteger(p,b)||!nextInteger(p,c)||!nextInteger(p,d)||
         std::strcmp(p," CONFIRM") || a>65535 || b>65535 || c>65535 || d>65535)return "REJECTED_CONFIG";
      return m4::servo_bench::name(servo.configure({static_cast<uint16_t>(a),static_cast<uint16_t>(b),static_cast<uint16_t>(c),static_cast<uint16_t>(d)}));
    }
    if(std::strcmp(text,"servo arm YES")==0){
      if(pumpActive() || buzzer_.active())return "REJECTED_OTHER_OUTPUT_OR_BUSY";
      return m4::servo_bench::name(servo.arm(now));
    }
    if(std::strcmp(text,"servo open")==0)return m4::servo_bench::name(servo.open(now));
    if(std::strcmp(text,"servo close")==0)return m4::servo_bench::name(servo.close(now));
    if(std::strcmp(text,"servo disarm")==0)return m4::servo_bench::name(servo.disarm(now));
    if(std::strncmp(text,"servo set ",10)==0){
      uint32_t value=0;const char* p=text+10;
      if(!integer(p,value)||*p || value>65535)return "REJECTED_POSITION";
      return m4::servo_bench::name(servo.move(static_cast<uint16_t>(value),now));
    }
    if(std::strcmp(text,"pump arm YES")==0){
      if(!pump_enabled_)return "BLOCKED_PUMP_POLARITY_NOT_MEASURED";
      if(servoActive() || buzzer_.active())return "REJECTED_OTHER_OUTPUT_OR_BUSY";
      return m4::pump_bench::name(pump.arm(now));
    }
    if(std::strncmp(text,"pump on ",8)==0){
      if(!pump_enabled_)return "BLOCKED_PUMP_POLARITY_NOT_MEASURED";
      uint32_t value=0;const char* p=text+8;
      if(!integer(p,value)||*p)return "REJECTED_DURATION";
      return m4::pump_bench::name(pump.pulse(now,value));
    }
    if(std::strcmp(text,"pump off")==0 || std::strcmp(text,"pump disarm")==0)return m4::pump_bench::name(pump.stop(now));
    if(std::strcmp(text,"buzzer-driver ACTIVE_LOW CONFIRM")==0){
      if(busy())return "REJECTED_OTHER_OUTPUT_OR_BUSY";
      buzzer_enabled_=buzzer_.enable();return buzzer_enabled_?"DRIVER_ACK_NOT_ELECTRICAL_PROOF":"OUTPUT_FAULT";
    }
    if(std::strcmp(text,"buzzer test CONFIRM")==0){
      if(servoActive()||pumpActive())return "REJECTED_OTHER_OUTPUT_OR_BUSY";
      if(!buzzer_enabled_||buzzer_tests_>=3||!buzzer_.start(now))return "REJECTED_DRIVER_BUDGET_COOLDOWN";
      ++buzzer_tests_;return "ACCEPTED_MANUAL_ONLY";
    }
    if(busy())emergency();
    return "REJECTED_NO_AI_FEED_CALIBRATION_OR_AUTOMATIC_COMMAND";
  }
 private:
  m4::servo_bench::Output& servo_io_;
  m4::pump_bench::Output& pump_io_;
  BuzzerOutput& buzzer_;
  bool pump_enabled_=false,buzzer_enabled_=false,fault_=false,clock_=false;
  unsigned buzzer_tests_=0;
  uint32_t boot_=0,link_=0,sequence_=0,generation_=0,last_now_=0,last_command_=0;
};
} // namespace manual_station
