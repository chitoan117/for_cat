// Actual C++ endpoint/controller, scripted observations and FAKE output/journal.
// stdin/stdout JSON only: never serial, GPIO, camera or service APIs.
#include "feed_link.h"
#include "dog_warning_protocol.h"
#include <json-c/json.h>
#include <iostream>
#include <string>
#include <vector>
struct Output: m4::servo_bench::Output {
    bool attached=false,opened=false,fail=false;unsigned opens=0;
    bool start(uint16_t)override{if(fail)return false;attached=true;return true;}
    bool write(uint16_t us)override{if(fail || !attached)return false;opened=us==1550;if(opened)++opens;return true;}
    bool off()override{if(fail)return false;attached=opened=false;return true;}
};
struct Journal:m4::dispense_bench::Journal {
    bool pending=false,fail=false;uint32_t last=0;unsigned writes=0;
    bool write(bool p,uint32_t id)override{++writes;if(fail)return false;pending=p;last=id;return true;}
};
std::string hex(const uint8_t* p,size_t n){static const char* c="0123456789abcdef";std::string s;for(size_t i=0;i<n;++i){s+=c[p[i]>>4];s+=c[p[i]&15];}return s;}
struct Sink:feed_link::Sink {
    std::vector<std::string> packets;
    void emit(uint32_t id,uint8_t op,const uint8_t* p,uint16_t n)override{uint8_t b[uart_v1::MAX_FRAME];size_t size=0;
        if(!uart_v1::encode(id,op,p,n,b,sizeof(b),size))throw std::runtime_error("encoding");packets.push_back(hex(b,size));}
};
struct Warning:feed_link::Warning {
    unsigned starts=0;bool seen=false;uint32_t last=0;
    bool pulse(uint32_t now)override{if(seen && now-last<60000)return false;seen=true;last=now;++starts;return true;}
};
json_object* field(json_object* o,const char* key){json_object* v=nullptr;json_object_object_get_ex(o,key,&v);return v;}
bool flag(json_object* o,const char* k,bool fallback){auto v=field(o,k);return v?json_object_get_boolean(v)!=0:fallback;}
int main(int argc,char**argv){try{
    Output output;Journal journal;Sink sink;Warning warning;
    const bool enabled=argc==2 && std::string(argv[1])=="--fake-enabled";
    feed_link::Endpoint endpoint(output,journal,sink,warning,enabled);dog_wire::Parser parser;
    uint32_t boot=1001;endpoint.boot(boot,true,false,0,1000);
    std::string line;
    while(std::getline(std::cin,line)){
        if(line.size()>8192)return 2;
        auto input=json_tokener_parse(line.c_str());if(!input)return 2;
        const auto now=static_cast<uint32_t>(json_object_get_int64(field(input,"now")));
        if(flag(input,"reboot",false)){endpoint.boot(++boot,true,journal.pending,journal.last,now);parser.reset();}
        journal.fail=flag(input,"journal_fail",false);output.fail=flag(input,"output_fail",false);
        m4::dispense_bench::Observation o{now,now,flag(input,"healthy",true),flag(input,"calibrated",true),flag(input,"fresh",true),
            static_cast<float>(json_object_get_double(field(input,"grams"))),static_cast<uint16_t>(field(input,"calibration_id")?json_object_get_int(field(input,"calibration_id")):7)};
        if(field(input,"sample_at"))o.sample_at_ms=static_cast<uint32_t>(json_object_get_int64(field(input,"sample_at")));
        feed_link::Closure closure{flag(input,"closure_available",true),flag(input,"closed",true),now};
        if(field(input,"closure_at"))closure.sampled_at_ms=static_cast<uint32_t>(json_object_get_int64(field(input,"closure_at")));
        // RX cancellation is processed before a pending new OPEN is launched.
        endpoint.tick(o,closure,false);
        if(flag(input,"transport_fault",false))endpoint.transportFault();
        auto bytes=field(input,"hex");if(bytes){const std::string h=json_object_get_string(bytes);if(h.size()%2 || h.size()>2048)return 2;
            for(size_t i=0;i<h.size();i+=2){const auto byte=static_cast<uint8_t>(std::stoul(h.substr(i,2),nullptr,16));
                parser.feed(byte,now,[&](uint32_t id,uint8_t op,const uint8_t* p,uint16_t n){endpoint.receive(id,op,p,n);});}}
        endpoint.tick(o,closure,true);
        auto out=json_object_new_object();auto packets=json_object_new_array();
        for(const auto& p:sink.packets)json_object_array_add(packets,json_object_new_string(p.c_str()));sink.packets.clear();
        json_object_object_add(out,"packets",packets);json_object_object_add(out,"opens",json_object_new_int(static_cast<int>(output.opens)));
        json_object_object_add(out,"pwm_attached",json_object_new_boolean(output.attached));json_object_object_add(out,"journal_pending",json_object_new_boolean(journal.pending));
        json_object_object_add(out,"journal_last",json_object_new_int64(journal.last));json_object_object_add(out,"warning_starts",json_object_new_int(static_cast<int>(warning.starts)));
        json_object_object_add(out,"state",json_object_new_int(static_cast<int>(endpoint.state())));
        json_object_object_add(out,"source",json_object_new_string("MOCK"));json_object_object_add(out,"physical_pass",json_object_new_boolean(false));
        std::cout<<json_object_to_json_string_ext(out,JSON_C_TO_STRING_PLAIN)<<std::endl;json_object_put(out);json_object_put(input);
    }
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
