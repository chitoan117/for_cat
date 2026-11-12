#include <assert.h>
#include <stdio.h>
#include <math.h>
#include "esp32/FallbackGate.h"
using namespace fallback_policy;
Inputs input(uint32_t n,float cm=20){return Inputs{n,n,true,true,true,true,cm};}
int main(){
 Gate g;auto s=input(1000);assert(g.step(s)==Action::NONE);
 for(int i=0;i<30;++i)assert(g.step(s)==Action::NONE);
 assert(g.step(input(1100))==Action::NONE);
 assert(g.step(input(1200))==Action::ATTEMPT);g.consumed(1200);
 for(uint32_t n=2000;n<400000;n+=1000)assert(g.step(input(n))==Action::NONE);
 assert(g.step(input(400000,31))==Action::NONE);
 assert(g.step(input(405000,31))==Action::REARM);
 for(int mode=0;mode<10;++mode){
   Gate blocked;
   for(uint32_t n=1000;n<=2000;n+=100){
     s=input(n);if(mode==0)s.offline=false;if(mode==1)s.permitted=false;
     if(mode==2)s.empty_scale=false;if(mode==3)s.distance_valid=false;
     if(mode==4)s.cm=20.01f;if(mode==5)s.distance_stamp=1;
     if(mode==6)s.cm=1.99f;if(mode==7)s.cm=NAN;
     if(mode==8)s.cm=INFINITY;if(mode==9)s.distance_stamp=0;
     assert(blocked.step(s)==Action::NONE);
   }
 }
 Gate lower;assert(lower.step(input(1000,2))==Action::NONE);
 assert(lower.step(input(1100,2))==Action::NONE);
 assert(lower.step(input(1200,2))==Action::ATTEMPT);
 Gate rollover;assert(rollover.step(input(0xffffff00u))==Action::NONE);
 assert(rollover.step(input(0xffffff80u))==Action::NONE);
 assert(rollover.step(input(0x10u))==Action::ATTEMPT);
 Gate rearm;rearm.consumed(1000);
 assert(rearm.step(input(2000,31))==Action::NONE);
 assert(rearm.step(input(8000,31))==Action::NONE); // cooldown not elapsed
 s=input(300000,31);s.distance_valid=false;assert(rearm.step(s)==Action::NONE);
 assert(rearm.step(input(301000,31))==Action::NONE); // fresh clear must restart
 assert(rearm.step(input(305999,31))==Action::NONE);
 assert(rearm.step(input(306000,31))==Action::REARM);
 puts("PASS: PIR-free E1 2..20cm x3, duplicate/stale/invalid rejection, host/scale/pause guards, cooldown/departure rearm, rollover");
}
