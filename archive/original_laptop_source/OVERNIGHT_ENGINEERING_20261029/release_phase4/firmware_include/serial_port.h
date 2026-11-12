#pragma once
#include <Arduino.h>
#include "board_config.h"
#if defined(M4_DOG_WARNING) && M4_DOG_WARNING
#include <cstdarg>
#include <cstdio>
#include <cstring>
// Profile-local TX queue keeps full telemetry from blocking buzzer/acoustic timing.
class DogNonblockingSerial {
  uint8_t bytes_[8192]{};size_t head_=0,count_=0;bool overflow_=false;
 public:
  void begin(unsigned long baud){Serial0.begin(baud);}
  int available(){return Serial0.available();}int read(){return Serial0.read();}
  size_t write(const uint8_t* bytes,size_t n){
    if(n>sizeof(bytes_)-count_){overflow_=true;return 0;}
    for(size_t i=0;i<n;++i)bytes_[(head_+count_++)%sizeof(bytes_)]=bytes[i];
    return n;
  }
  void print(const char* text){write(reinterpret_cast<const uint8_t*>(text),std::strlen(text));}
  void println(const char* text){print(text);print("\r\n");}
  void printf(const char* format,...){char text[2048];va_list args;va_start(args,format);
    const int n=std::vsnprintf(text,sizeof(text),format,args);va_end(args);
    if(n<0 || static_cast<size_t>(n)>=sizeof(text)){overflow_=true;return;}
    write(reinterpret_cast<const uint8_t*>(text),static_cast<size_t>(n));
  }
  void drain(){
    const int room=Serial0.availableForWrite();size_t n=room>0?static_cast<size_t>(room):0;
    if(n>64)n=64;
    if(n>count_)n=count_;
    if(n>sizeof(bytes_)-head_)n=sizeof(bytes_)-head_;
    if(n){const size_t done=Serial0.write(bytes_+head_,n);head_=(head_+done)%sizeof(bytes_);count_-=done;}
  }
  bool overflowed()const{return overflow_;}
};
#endif

// Bridge profile: explicit UART0. S3 native profile: Serial aliases HW CDC
// with official manifest ARDUINO_USB_MODE=1 / CDC_ON_BOOT=1. No pin remapping.
inline auto& protocolSerial() {
#if defined(M4_DOG_WARNING) && M4_DOG_WARNING
  static DogNonblockingSerial port;return port;
#elif defined(FORR_NATIVE_USB) && FORR_NATIVE_USB
  return Serial;
#else
  return Serial0;
#endif
}
