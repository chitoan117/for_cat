#pragma once
#include <cmath>
#include <cstdint>
namespace cat_test {
class Gate {
    uint32_t ai_at_=0,near_at_=0,source_seq_=0;unsigned near_count_=0;
    bool cat_=false,visited_=false;
 public:
    bool ai(uint32_t now,uint32_t seq,uint32_t age,uint32_t transport_age,unsigned confidence,bool cat){
        if(!seq || seq<=source_seq_ || age>750 || transport_age>750 || age+transport_age>750 || confidence>1000)return false;
        source_seq_=seq;ai_at_=now-age-transport_age;cat_=cat&&confidence>=800;
        if(!cat_)near_count_=0;
        return true;
    }
    bool catFresh(uint32_t now)const{return cat_&&uint32_t(now-ai_at_)<=750;}
    void near(uint32_t now,bool valid,float cm){
        if(!catFresh(now)||!valid||!std::isfinite(cm)||cm<2||cm>20){near_count_=0;return;}
        if(near_count_&&uint32_t(now-near_at_)>250)near_count_=0;
        near_at_=now;if(near_count_<3)++near_count_;
    }
    bool ready(uint32_t now)const{return !visited_&&catFresh(now)&&near_count_>=3&&uint32_t(now-near_at_)<=200;}
    void consume(){visited_=true;}
    bool visited()const{return visited_;}
    // Only explicit owner inspection opens another test visit. No timed refeed.
    void inspected(){visited_=false;near_count_=0;cat_=false;}
};
inline uint16_t crc(const char* p,unsigned n){uint16_t c=0xffff;for(unsigned i=0;i<n;++i){c^=uint16_t(uint8_t(p[i]))<<8;for(unsigned j=0;j<8;++j)c=c&0x8000?uint16_t((c<<1)^0x1021):uint16_t(c<<1);}return c;}
}
