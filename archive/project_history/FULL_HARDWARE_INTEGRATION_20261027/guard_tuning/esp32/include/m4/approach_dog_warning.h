#pragma once
#include <cmath>
#include "io.h"
#include "dog_warning_protocol.h"
namespace m4 { namespace approach_dog {
constexpr float APPROACH_ENTER_CM=20,APPROACH_RELEASE_CM=30,MIN_VALID_APPROACH_CM=5;
constexpr uint32_t ENTER_CONFIRM_WINDOW_MS=1500,RELEASE_CONFIRM_MS=2000,STALE_MS=750;
constexpr unsigned ENTER_CONFIRM_SAMPLES=3,BUZZER_GPIO=2,BUZZER_BEEP_COUNT=2;
constexpr bool BUZZER_ACTIVE_LOW=true;
constexpr uint32_t BUZZER_ON_MS=200,BUZZER_OFF_GAP_MS=200,BUZZER_COOLDOWN_MS=60000;
enum class State {NOT_ARMED,ARMED,CONFIRMED};
inline const char* name(State s){return s==State::NOT_ARMED?"NOT_ARMED":s==State::ARMED?"ARMED":"APPROACH_CONFIRMED";}
class Approach {
 State state_=State::NOT_ARMED;bool far_=false,seen_=false,valid_=false;
 uint32_t far_at_=0,first_=0,last_=0,event_at_=0,event_=0;unsigned near_=0;float cm_=0;
 public:
 void reset(){state_=State::NOT_ARMED;far_=seen_=valid_=false;near_=0;event_at_=0;}
 void tick(uint32_t now){if(seen_ && static_cast<uint32_t>(now-last_)>STALE_MS){valid_=false;far_=false;near_=0;}}
 bool sample(bool valid,float cm,uint32_t at,uint32_t now){
   tick(now);
   if(seen_ && at==last_)return false;
   seen_=true;last_=at;cm_=cm;
   valid_=valid && std::isfinite(cm) && cm>=MIN_VALID_APPROACH_CM && cm<=400 && static_cast<uint32_t>(now-at)<=STALE_MS;
   if(!valid_){far_=false;near_=0;return false;}
   if(cm>APPROACH_RELEASE_CM){
     near_=0;if(!far_){far_=true;far_at_=at;}
     if(static_cast<uint32_t>(at-far_at_)>=RELEASE_CONFIRM_MS){state_=State::ARMED;event_at_=0;}
     return false;
   }
   far_=false;
   if(state_!=State::ARMED || cm>APPROACH_ENTER_CM){near_=0;return false;}
   if(!near_ || static_cast<uint32_t>(at-first_)>ENTER_CONFIRM_WINDOW_MS){near_=0;first_=at;}
   if(++near_>=ENTER_CONFIRM_SAMPLES){
     if(event_==UINT32_MAX){state_=State::NOT_ARMED;return false;}
     ++event_;event_at_=at;state_=State::CONFIRMED;near_=0;return true;
   }
   return false;
 }
 bool currentNear(uint32_t now)const{return seen_ && valid_ && cm_>=5 && cm_<=20 && static_cast<uint32_t>(now-last_)<=STALE_MS;}
 bool actionable(uint32_t now)const{return state_==State::CONFIRMED && currentNear(now) && static_cast<uint32_t>(now-event_at_)<=dog_wire::MAX_AGE_MS;}
 State state()const{return state_;} uint32_t event()const{return event_;}uint32_t eventAt()const{return event_at_;}
 uint32_t sampleAt()const{return last_;} bool valid()const{return valid_;}float distance()const{return cm_;}
};
class Buzzer {
 PinIO& io_;unsigned phase_=0;uint32_t at_=0,last_start_=0;bool have_start_=false;uint32_t completed_=0;
 public:
 explicit Buzzer(PinIO& io):io_(io){}
 void begin(){io_.write(BUZZER_GPIO,true);io_.output(BUZZER_GPIO);phase_=0;} // HIGH before OUTPUT
 bool start(uint32_t now){
   if(phase_ || (have_start_ && static_cast<uint32_t>(now-last_start_)<BUZZER_COOLDOWN_MS))return false;
   have_start_=true;last_start_=at_=now;phase_=1;io_.write(BUZZER_GPIO,false);return true;
 }
 void tick(uint32_t now){
   if(!phase_ || static_cast<uint32_t>(now-at_)<200)return;
   // At most one edge/tick. A delayed loop never compresses two audible pulses.
   at_=now;
   if(phase_==1){io_.write(BUZZER_GPIO,true);phase_=2;}
   else if(phase_==2){io_.write(BUZZER_GPIO,false);phase_=3;}
   else{io_.write(BUZZER_GPIO,true);phase_=0;++completed_;}
 }
 bool active()const{return phase_!=0;} unsigned phase()const{return phase_;}uint32_t completed()const{return completed_;}
};
enum Result:uint8_t{ACCEPTED=0,BAD_COMMAND=1,OLD_SESSION=2,STALE=3,DUPLICATE=4,NOT_NEAR=5,COOLDOWN=6};
class Receiver {
 Approach& gate_;Buzzer& buzzer_;uint32_t boot_,link_=0,used_event_=0,last_id_=0;
 public:
 Receiver(Approach& gate,Buzzer& buzzer,uint32_t boot):gate_(gate),buzzer_(buzzer),boot_(boot){}
 void begin(uint32_t boot){boot_=boot;link_=used_event_=last_id_=0;gate_.reset();}
 Result receive(uint32_t id,uint8_t cmd,const uint8_t* p,uint16_t n,uint32_t now){
   if(!id || !p || !n || p[0]!=dog_wire::SCHEMA)return BAD_COMMAND;
   if(cmd==dog_wire::HELLO && n==9){
     if(dog_wire::get(p+1)!=boot_ || !dog_wire::get(p+5))return OLD_SESSION;
     const auto link=dog_wire::get(p+5);
     if(link!=link_){link_=link;gate_.reset();used_event_=gate_.event();last_id_=0;}
     return ACCEPTED;
   }
   if(cmd!=dog_wire::WARNING || n!=21)return BAD_COMMAND;
   if(dog_wire::get(p+1)!=boot_ || !link_ || dog_wire::get(p+5)!=link_)return OLD_SESSION;
   const auto event=dog_wire::get(p+9),at=dog_wire::get(p+13),deadline=dog_wire::get(p+17);
   if(id<=last_id_ || event<=used_event_)return DUPLICATE;
   if(event!=gate_.event() || at!=gate_.eventAt() || deadline!=at+1500 || static_cast<uint32_t>(now-at)>1500)return STALE;
   if(!gate_.actionable(now))return NOT_NEAR;
   last_id_=id;used_event_=event; // cooldown/busy rejection consumes this approach too
   return buzzer_.start(now)?ACCEPTED:COOLDOWN;
 }
 uint32_t link()const{return link_;}uint32_t boot()const{return boot_;}
};
} } // namespace m4::approach_dog
