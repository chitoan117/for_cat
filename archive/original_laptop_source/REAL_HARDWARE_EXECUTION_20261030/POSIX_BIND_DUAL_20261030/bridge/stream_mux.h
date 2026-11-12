#pragma once
#include "telemetry.h"
#include "dog_warning_protocol.h"
// One RX path, one fd. ASCII reports and binary packets are queued atomically
// by the dual firmware; no second reader or parser-owned tty is introduced.
class StreamMux {
    forcat::LineFramer text_;dog_wire::Parser binary_;bool line_=false;
 public:
    uint64_t oversized=0;
    void clear(){text_.clear();binary_.reset();line_=false;}
    template<class Text,class Frame> void feed(const char* p,size_t n,uint32_t now,Text onText,Frame onFrame){
        for(size_t i=0;i<n;++i){const auto c=static_cast<uint8_t>(p[i]);
            if(line_){
                const auto before=text_.oversized;text_.feed(p+i,1,onText);oversized+=text_.oversized-before;
                if(c=='\n'||c=='\r')line_=false;
            }else if(binary_.feed(c,now,onFrame)){
                // Full UART frame payload may contain CR/LF/A5: binary parser owns it.
            }else if(c=='\n'||c=='\r'){
                text_.feed(p+i,1,onText);
            }else if(c>=32 && c<=126){line_=true;text_.feed(p+i,1,onText);}
        }
    }
};
