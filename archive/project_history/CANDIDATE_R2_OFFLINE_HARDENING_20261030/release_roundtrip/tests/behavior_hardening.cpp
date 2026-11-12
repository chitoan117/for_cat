#include "owner_behavior.h"
#include <iostream>
#include <stdexcept>
namespace ob=forcat::owner_behavior;
unsigned checks=0;
#define CHECK(v) do{++checks;if(!(v))throw std::runtime_error("behavior line="+std::to_string(__LINE__));}while(false)
const auto roi=forcat::food_roi::parseConfig("{\"enabled\":true,\"calibrated\":true,\"review_id\":\"SYNTHETIC_ONLY\",\"x1\":0.25,\"y1\":0.25,\"x2\":0.75,\"y2\":0.75}");
ob::Input input(unsigned n){ob::Input i;i.now=i.captured=1000+n*500;i.sequence=n+1;i.identity=ob::Identity::OWNER_CAT;i.identity_source="SYNTHETIC_OWNER_FIXTURE";i.simulation=true;i.confidence=.95;i.distance_valid=true;i.distance=15;return i;}
int main(){try{
    {ob::Policy p(roi);for(unsigned n=0;n<4;++n){auto i=input(n);i.sequence=4-n;CHECK(!p.update(i).would_request_35g);}}
    for(unsigned fault=0;fault<7;++fault){ob::Policy p(roi);for(unsigned n=0;n<10;++n){auto i=input(n);if(fault==0)i.identity=ob::Identity::DOG;if(fault==1)i.identity=ob::Identity::OTHER_CAT;if(fault==2)i.identity=ob::Identity::UNKNOWN;if(fault==3)i.public_dataset=true;if(fault==4)i.simulation=false;if(fault==5)i.distance_valid=false;if(fault==6)i.captured=0;CHECK(!p.update(i).would_request_35g);}}
    {ob::Policy p(roi);CHECK(!p.update(input(0)).would_request_35g);CHECK(!p.update(input(1)).would_request_35g);auto i=input(2);i.identity_token="SYNTHETIC_OTHER_TRACK";CHECK(!p.update(i).would_request_35g);i=input(3);i.identity_token="SYNTHETIC_OTHER_TRACK";CHECK(!p.update(i).would_request_35g);}
    {ob::Policy p(roi);for(unsigned n=0;n<8;++n){auto i=input(n);i.distance=n%2?20:5;CHECK(!p.update(i).would_request_35g);}}
    {ob::Policy p(roi);for(unsigned n=0;n<4;++n)p.update(input(n));auto dog=input(4);dog.identity=ob::Identity::DOG;dog.feeding_active=true;auto d=p.update(dog);CHECK(d.cancel_active_feed&&!d.would_request_35g);auto stale=input(5);stale.captured=0;stale.feeding_active=true;CHECK(p.update(stale).cancel_active_feed);}
    {ob::Policy p(roi);ob::Decision d;for(unsigned n=0;n<4;++n)d=p.update(input(n));CHECK(d.would_request_35g);for(unsigned n=4;n<12;++n)d=p.update(input(n));CHECK(d.state=="SNIFFING"&&!d.would_request_35g);auto eat=input(12);eat.consumption_valid=true;eat.consumed=8;d=p.update(eat);CHECK(d.state=="EATING"&&!d.would_request_35g);auto old=input(2);CHECK(!p.update(old).would_request_35g);}
    {auto invalid=forcat::food_roi::parseConfig("{\"enabled\":true}");ob::Policy p(invalid);for(unsigned n=0;n<5;++n)CHECK(!p.update(input(n)).would_request_35g);}
    {ob::Policy p(roi);for(unsigned n=0;n<4;++n)p.update(input(n));for(unsigned n=4;n<40;++n){auto i=input(n);if(n%3==0)i.identity=ob::Identity::UNKNOWN;CHECK(!p.update(i).would_request_35g);}}
    CHECK(!ob::Decision::actuator_execution);
    std::cout<<"BEHAVIOR_HARDENING_PASS checks="<<checks<<" source=SIMULATED real_owner_model=BLOCKED\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
