#include <assert.h>
#include <stdio.h>
#include "esp32/FallbackGate.h"
using namespace fallback_policy;
Inputs input(uint32_t n,float cm=20){return Inputs{n,n,true,true,true,true,true,cm};}
int main(){
 Gate g;auto s=input(1000);assert(g.step(s)==Action::NONE);
 for(int i=0;i<30;++i)assert(g.step(s)==Action::NONE); // one frame cannot qualify
 s=input(1100);assert(g.step(s)==Action::NONE);
 s=input(1200);assert(g.step(s)==Action::ATTEMPT);g.consumed(s.now);
 for(uint32_t n=2000;n<400000;n+=1000)assert(g.step(input(n))==Action::NONE);
 s=input(400000,31);s.pir=false;assert(g.step(s)==Action::NONE);
 s=input(405000,31);s.pir=false;assert(g.step(s)==Action::REARM);
 for(int mode=0;mode<6;++mode){
   Gate blocked;
   for(uint32_t n=1000;n<=2000;n+=100){
     s=input(n);if(mode==0)s.offline=false;if(mode==1)s.permitted=false;
     if(mode==2)s.empty_scale=false;if(mode==3)s.pir=false;
     if(mode==4)s.cm=20.01f;if(mode==5)s.distance_stamp=1;
     assert(blocked.step(s)==Action::NONE);
   }
 }
 Gate rollover; s=input(0xffffff00u);assert(rollover.step(s)==Action::NONE);
 s=input(0xffffff80u);assert(rollover.step(s)==Action::NONE);
 s=input(0x00000010u);assert(rollover.step(s)==Action::ATTEMPT);
 Gate stale; stale.consumed(1);s=input(400000,31);s.pir=false;s.distance_valid=false;
 assert(stale.step(s)==Action::NONE);s.now+=6000;assert(stale.step(s)==Action::NONE);
 puts("PASS:20cm boundary,3 distinct frames,PIR,link/scale/stop guards,no repeat,far+5min rearm,stale rejection,millis rollover");
}
