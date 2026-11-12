#pragma once
// Platform replacement ONLY: actual esp32_bridge.cpp loop/DB/outbox code executes.
// No OS tty function exists in this build. MCU is the real endpoint/controller
// code with independent scripted scale/closure and fake physical outputs.
#include "feed_link.h"
#include "dog_warning_protocol.h"
#include <json-c/json.h>
#include <algorithm>
#include <deque>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace mock_io {
inline json_object* field(json_object* o,const char* k){json_object* v=nullptr;json_object_object_get_ex(o,k,&v);return v;}
inline bool boolean(json_object* o,const char* k,bool fallback){auto v=field(o,k);return v?json_object_get_boolean(v)!=0:fallback;}
struct Output:public m4::servo_bench::Output {
    bool attached=false,fail=false;unsigned opens=0;
    bool start(uint16_t)override{if(fail)return false;attached=true;return true;}
    bool write(uint16_t us)override{if(fail||!attached)return false;if(us==1550)++opens;return true;}
    bool off()override{if(fail)return false;attached=false;return true;}
};
struct Journal:public m4::dispense_bench::Journal {
    bool pending=false,fail=false;uint32_t last=0;
    bool write(bool p,uint32_t id)override{if(fail)return false;pending=p;last=id;return true;}
};
struct Warning:public feed_link::Warning {
    unsigned starts=0;uint32_t last=0;bool seen=false;
    bool pulse(uint32_t now)override{if(starts>=3 || (seen&&now-last<60000))return false;seen=true;last=now;++starts;return true;}
};
struct Sink:public feed_link::Sink {
    std::deque<uint8_t>& rx;bool& cable;
    Sink(std::deque<uint8_t>& r,bool& c):rx(r),cable(c){}
    void emit(uint32_t id,uint8_t op,const uint8_t* p,uint16_t size)override{
        if(!cable)return;
        uint8_t b[uart_v1::MAX_FRAME];size_t n=0;if(!uart_v1::encode(id,op,p,size,b,sizeof(b),n))throw std::runtime_error("mock frame encode");
        rx.insert(rx.end(),b,b+n);
    }
};
struct Device {
    Output output;Journal journal;Warning warning;Sink sink;feed_link::Endpoint endpoint;dog_wire::Parser parser;
    m4::dispense_bench::Observation sample{1000,1000,true,true,true,100,7};
    feed_link::Closure closure{true,true,1000};uint32_t boot=1001;
    Device(std::deque<uint8_t>& rx,bool& cable,bool enabled):sink(rx,cable),endpoint(output,journal,sink,warning,enabled){endpoint.boot(boot,true,false,0,1000);}
};
struct State {
    uint32_t now=1000;bool cable=true,opened=false,stop=false,short_write=false;
    unsigned owner_opens=0,steps=0;std::deque<uint8_t> rx;std::unique_ptr<Device> device;
    void configure(bool enabled){device.reset(new Device(rx,cable,enabled));}
    void advance(){
        std::string line;if(!std::getline(std::cin,line)){stop=true;return;}
        if(line.size()>16384)throw std::runtime_error("mock input bound");
        auto v=json_tokener_parse(line.c_str());if(!v)throw std::runtime_error("mock JSON");
        if(boolean(v,"quit",false)){stop=true;json_object_put(v);return;}
        if(field(v,"now"))now=static_cast<uint32_t>(json_object_get_int64(field(v,"now")));
        cable=boolean(v,"connected",cable);short_write=boolean(v,"short_write",false);
        auto& d=*device;
        if(boolean(v,"reboot",false)){d.endpoint.boot(++d.boot,true,d.journal.pending,d.journal.last,now);d.parser.reset();}
        d.sample.now_ms=now;d.sample.sample_at_ms=field(v,"sample_at")?static_cast<uint32_t>(json_object_get_int64(field(v,"sample_at"))):now;
        if(field(v,"grams"))d.sample.grams=static_cast<float>(json_object_get_double(field(v,"grams")));
        d.sample.healthy=boolean(v,"healthy",true);d.sample.calibrated=boolean(v,"calibrated",true);d.sample.fresh=boolean(v,"fresh",true);
        d.sample.calibration_id=field(v,"calibration_id")?static_cast<uint16_t>(json_object_get_int(field(v,"calibration_id"))):7;
        d.closure={boolean(v,"closure_available",true),boolean(v,"closed",true),now};
        d.journal.fail=boolean(v,"journal_fail",false);d.output.fail=boolean(v,"output_fail",false);
        d.endpoint.tick(d.sample,d.closure,false);
        if(field(v,"ascii")){const std::string text=json_object_get_string(field(v,"ascii"));rx.insert(rx.end(),text.begin(),text.end());}
        json_object_put(v);++steps;
    }
    void finish(){
        device->endpoint.tick(device->sample,device->closure,true);
        auto o=json_object_new_object();
        json_object_object_add(o,"bridge_source",json_object_new_string("esp32_bridge.cpp::bridge"));
        json_object_object_add(o,"source",json_object_new_string("MOCK"));json_object_object_add(o,"physical_pass",json_object_new_boolean(false));
        json_object_object_add(o,"owner_opens",json_object_new_int(static_cast<int>(owner_opens)));
        json_object_object_add(o,"opens",json_object_new_int(static_cast<int>(device->output.opens)));
        json_object_object_add(o,"pwm_attached",json_object_new_boolean(device->output.attached));
        json_object_object_add(o,"journal_pending",json_object_new_boolean(device->journal.pending));
        json_object_object_add(o,"warning_starts",json_object_new_int(static_cast<int>(device->warning.starts)));
        json_object_object_add(o,"now",json_object_new_int64(now));json_object_object_add(o,"stopped",json_object_new_boolean(stop));
        std::cout<<json_object_to_json_string_ext(o,JSON_C_TO_STRING_PLAIN)<<std::endl;json_object_put(o);
    }
    size_t write(const uint8_t* p,size_t n){
        if(!opened || !cable)return 0;
        const size_t actual=short_write&&n?n-1:n;
        auto& d=*device;
        for(size_t i=0;i<actual;++i)d.parser.feed(p[i],now,[&](uint32_t id,uint8_t op,const uint8_t* bytes,uint16_t size){d.endpoint.receive(id,op,bytes,size);});
        return actual;
    }
};
inline State& state(){static State value;return value;}
} // namespace mock_io
