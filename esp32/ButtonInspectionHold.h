#pragma once
#include <stdint.h>
namespace button_inspection {
struct Hold {
 bool previous=true,released=false,armed=false;
 uint32_t at=0;
 bool step(uint32_t now,bool down,bool locked){
  if(!down){previous=false;released=true;armed=false;return false;}
  if(!previous){previous=true;armed=released&&locked;at=now;}
  if(!locked)armed=false;
  if(armed&&uint32_t(now-at)>=5000){armed=false;released=false;return true;}
  return false;
 }
};
}
