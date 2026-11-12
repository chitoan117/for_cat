#pragma once
#include <cstring>
#include "cat_gate.h"
namespace cat_test {
inline bool number(const char* s,uint32_t& v){
    if(!s||!*s)return false;v=0;
    for(;*s;++s){if(*s<'0'||*s>'9'||v>(UINT32_MAX-unsigned(*s-'0'))/10)return false;v=v*10+unsigned(*s-'0');}return true;
}
struct Packet {char* op=nullptr;char* args[5]{};unsigned count=0;uint32_t seq=0,echo=0;};
class Receiver {
    uint32_t last_=0;
 public:
    uint32_t last()const{return last_;}
    bool parse(char* line,uint32_t boot,uint32_t now,Packet& p){
        p={};char* star=std::strchr(line,'*');if(!star||std::strlen(star+1)!=4)return false;
        uint16_t expected=0;for(char* c=star+1;*c;++c){unsigned n;if(*c>='0'&&*c<='9')n=*c-'0';else if(*c>='A'&&*c<='F')n=*c-'A'+10;else return false;expected=uint16_t(expected*16+n);}
        if(crc(line,unsigned(star-line))!=expected)return false;*star=0;
        char* words[10]{};unsigned n=0;char* save=nullptr;
        for(char* s=strtok_r(line," ",&save);s;s=strtok_r(nullptr," ",&save)){if(n==10)return false;words[n++]=s;}
        uint32_t b=0;if(n<5||std::strcmp(words[0],"FC1")||!number(words[1],b)||b!=boot||
            !number(words[2],p.seq)||!p.seq||p.seq<=last_||!number(words[3],p.echo)||uint32_t(now-p.echo)>750)return false;
        p.op=words[4];p.count=n-5;for(unsigned i=0;i<p.count;++i)p.args[i]=words[i+5];last_=p.seq;return true;
    }
};
}
