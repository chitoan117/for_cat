#pragma once
#include <stdint.h>
namespace cat_proximity {
struct Window {
  uint8_t hits=0;
  uint32_t last=0;
  void observe(uint32_t now,bool valid,float cm,uint32_t stamp) {
    if(!valid||stamp==0||uint32_t(now-stamp)>400||!(cm>=2&&cm<=30)) {hits=0;return;}
    if(stamp==last)return;
    if(last&&uint32_t(stamp-last)>400)hits=0;
    last=stamp;if(hits<2)++hits;
  }
  bool ready(uint32_t now) const {return hits>=2&&uint32_t(now-last)<=400;}
};
}
