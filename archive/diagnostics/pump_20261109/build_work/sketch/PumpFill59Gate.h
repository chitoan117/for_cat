#line 1 "D:\\Agent_Cat\\diagnostics\\backup30_20261111\\esp32\\PumpFill59Gate.h"
#pragma once
#include <stdint.h>
#include <math.h>
namespace pump_fill59 {
struct Gate {
 bool running=false;
 uint32_t started=0;
 const char* reason="IDLE";
 static constexpr uint32_t MAX_MS=10000,FRESH_MS=1200;
 static bool fresh(uint32_t now,bool valid,float cm,uint32_t stamp){
  return valid&&isfinite(cm)&&cm>=2&&cm<=400&&uint32_t(now-stamp)<=FRESH_MS;
 }
 bool start(uint32_t now,bool valid,float cm,uint32_t stamp){
  if(running)return false; // A repeated request cannot extend an active run.
  if(!fresh(now,valid,cm,stamp)){reason="D1_INVALID";return false;}
  if(cm<=5.9f){reason="TARGET_59CM";return false;}
  if(cm>6.4f){reason="D1_OUTSIDE_COMMISSIONED_RANGE";return false;}
  started=now;running=true;reason="FILLING_59CM";return true;
 }
 bool step(uint32_t now,bool valid,float cm,uint32_t stamp){
  if(!running)return false;
  if(!fresh(now,valid,cm,stamp))return stop("D1_LOST_OFF");
  if(cm<=5.9f)return stop("TARGET_59CM");
  if(uint32_t(now-started)>=MAX_MS)return stop("TIME_LIMIT_OFF");
  return true;
 }
 bool stop(const char* why="OPERATOR_OFF"){running=false;reason=why;return false;}
};
}
