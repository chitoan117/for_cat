#pragma once
#include "uart_v1.h"
namespace dog_wire {
constexpr uint8_t HELLO=0x30, WARNING=0x31, SCHEMA=1;
constexpr uint32_t MAX_AGE_MS=1500;
inline uint32_t get(const uint8_t* p){return static_cast<uint32_t>(p[0]) | static_cast<uint32_t>(p[1])<<8 | static_cast<uint32_t>(p[2])<<16 | static_cast<uint32_t>(p[3])<<24;}
inline void put(uint8_t* p,uint32_t x){for(unsigned i=0;i<4;++i)p[i]=static_cast<uint8_t>(x>>(8*i));}
// Frozen UARTv1 envelope/CRC. This parser never dispatches an actuator command.
class Parser {
 uint8_t bytes_[uart_v1::MAX_FRAME]{};size_t used_=0,needed_=0;uint32_t last_=0;
 public:
 void reset(){used_=needed_=0;}
 template<class F> bool feed(uint8_t c,uint32_t now,F emit){
   if(used_ && static_cast<uint32_t>(now-last_)>250)reset();
   if(!used_){if(c!=uart_v1::START_A)return false;bytes_[used_++]=c;last_=now;return true;}
   last_=now;
   if(used_==1 && c!=uart_v1::START_B){reset();if(c==uart_v1::START_A){bytes_[used_++]=c;}return true;}
   bytes_[used_++]=c;
   if(used_==uart_v1::HEADER){
     const size_t n=static_cast<size_t>(bytes_[8])+(static_cast<size_t>(bytes_[9])<<8);
     if(bytes_[2]!=uart_v1::VERSION || n>uart_v1::MAX_PAYLOAD){reset();return true;}
     needed_=uart_v1::HEADER+n+2;
   }
   if(needed_ && used_==needed_){
     const auto n=needed_-uart_v1::HEADER-2;
     if(uart_v1::crc16(bytes_+2,needed_-4)==(static_cast<uint16_t>(bytes_[needed_-2]) | static_cast<uint16_t>(bytes_[needed_-1])<<8))
       emit(get(bytes_+3),bytes_[7],bytes_+uart_v1::HEADER,static_cast<uint16_t>(n));
     reset();
   }
   return true;
 }
};
} // namespace dog_wire
