#include "sole_owner_feed_link.h"
#include <iostream>
#include <set>
#include <vector>
struct Writer:forcat_feed_bridge::Writer {
    unsigned writes=0;bool partial=false;
    size_t writeOnce(const uint8_t*,size_t n)override{++writes;return partial?n-1:n;}
};
struct Store:forcat_feed_bridge::DurableStore {
    std::set<uint32_t> sent;
    bool consumeReserved(uint32_t id,uint32_t,uint32_t)override{return sent.insert(id).second;}
};
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("Bridge link check="+std::to_string(checks));}
void cap(forcat_feed_bridge::Link& link,uint8_t flags,uint32_t now){
    uint8_t p[23]{1};feed_link::put32(p+1,1001);feed_link::put32(p+5,1);p[13]=flags;
    uint8_t b[268]{};size_t n=0;uart_v1::encode(123,feed_link::CAPABILITIES,p,23,b,sizeof(b),n);
    link.rx(b,n,now,[](uint32_t,uint8_t,const uint8_t*,uint16_t){});
}
int main(){try{
    Writer w;Store store;forcat_feed_bridge::Link link(w,store);
    check(!link.hello(123,1000));check(w.writes==0);
    forcat_feed_bridge::Review review;review.sole_owner=review.maintenance_tx=true;link.reviewed(review);
    check(link.hello(123,1000));cap(link,15,1010);
    check(!link.send(1,feed_link::FEED,nullptr,0,1020));check(w.writes==1);
    review.actuation=review.servo=review.power=review.calibration=review.journal=review.closure=true;link.reviewed(review);
    check(link.send(1,feed_link::FEED,nullptr,0,1030));check(!link.send(1,feed_link::FEED,nullptr,0,1040));
    check(!link.send(2,feed_link::FEED,nullptr,0,3000));
    link.disconnect();check(!link.send(2,feed_link::FEED,nullptr,0,3100));
    check(link.hello(123,3200));cap(link,0,3210);check(!link.send(2,feed_link::FEED,nullptr,0,3220));
    link.disconnect();check(link.hello(123,3300));cap(link,15,3310);
    w.partial=true;check(!link.send(2,feed_link::FEED,nullptr,0,3320));check(link.unknownOutcome());
    w.partial=false;check(!link.send(2,feed_link::FEED,nullptr,0,3330));
    check(!link.hello(123,3400));check(store.sent.size()==2);
    std::cout<<"BRIDGE_LINK_PASS checks="<<checks<<" source=MOCK callbacks_only physical_pass=false\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
