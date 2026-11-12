#pragma once
#include "m4/servo_bench.h"
// Serialized loop ownership; never two independently-attached GPIO6 drivers.
// OFF from an inactive peer cannot interrupt the other owner's movement.
class ExclusiveServoBus {
 public:
    enum Role {IdleRole,ManualRole,FeedRole};
    class Port:public m4::servo_bench::Output {
        ExclusiveServoBus& bus_;Role role_;
     public:
        Port(ExclusiveServoBus& bus,Role role):bus_(bus),role_(role){}
        bool start(uint16_t us)override{
            if(bus_.stopped_ || bus_.owner_!=IdleRole)return false;
            bus_.owner_=role_;return bus_.driver_.start(us);
        }
        bool write(uint16_t us)override{return !bus_.stopped_ && bus_.owner_==role_ && bus_.driver_.write(us);}
        bool off()override{
            if(bus_.owner_!=IdleRole && bus_.owner_!=role_)return false;
            const bool safe=bus_.driver_.off();if(safe)bus_.owner_=IdleRole;return safe;
        }
    };
 private:
    m4::servo_bench::Output& driver_;Role owner_=IdleRole;bool stopped_=false;
    Port manual_{*this,ManualRole},feed_{*this,FeedRole};
 public:
    explicit ExclusiveServoBus(m4::servo_bench::Output& driver):driver_(driver){}
    Port& manual(){return manual_;}Port& feed(){return feed_;}
    Role owner()const{return owner_;}
    bool emergencyOff(){stopped_=true;const bool ok=driver_.off();if(ok)owner_=IdleRole;return ok;}
    const char* ownerName()const{return owner_==ManualRole?"MANUAL":owner_==FeedRole?"FEED":"NONE";}
};
