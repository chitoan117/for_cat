#pragma once
#include <stdint.h>
#include <math.h>
namespace portion_settle {
enum class Result { WAITING, VERIFIED, UNDER, OVER, INVALID, TIMEOUT };
struct Gate {
 Result result=Result::WAITING;
 uint32_t started=0,stable_since=0,last_stamp=0;
 unsigned samples=0;
 bool have_sample=false;
 float ref=NAN,sum=0,measured=NAN;
 static constexpr uint32_t MAX_MS=6000,STABLE_MS=1500,FRESH_MS=1200;
 void begin(uint32_t now){*this=Gate{};started=now;}
 const char* reason()const{
  switch(result){case Result::WAITING:return "SETTLING";case Result::VERIFIED:return "STABLE_PORTION_VERIFIED";
   case Result::UNDER:return "STABLE_PORTION_LOW";case Result::OVER:return "STABLE_PORTION_HIGH";
   case Result::INVALID:return "SCALE_INVALID";default:return "NO_STABLE_FINAL_WEIGHT";}
 }
 Result step(uint32_t now,bool valid,float net,uint32_t stamp){
  if(result!=Result::WAITING)return result;
  if(uint32_t(now-started)>=MAX_MS){result=Result::TIMEOUT;return result;}
  if(!valid||!isfinite(net)||uint32_t(now-stamp)>FRESH_MS){ref=NAN;samples=0;sum=0;return result;}
  if(net < -2 || net>500){result=Result::INVALID;return result;}
  if(have_sample&&last_stamp==stamp)return result;
  have_sample=true;last_stamp=stamp;
  if(!isfinite(ref)||fabsf(net-ref)>.4f){ref=net;stable_since=now;samples=1;sum=net;return result;}
  ++samples;sum+=net;
  if(samples<5||uint32_t(now-stable_since)<STABLE_MS)return result;
  measured=sum/float(samples);
  result=measured<35?Result::UNDER:measured>40?Result::OVER:Result::VERIFIED;
  return result;
 }
};
}
