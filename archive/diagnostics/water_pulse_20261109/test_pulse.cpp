#include "esp32/D1PumpGate.h"
#include <assert.h>
#include <stdio.h>
uint32_t trigger(d1_pump::Gate&g,uint32_t t){
 assert(!g.step(t,true,22.7f,t));assert(!g.step(t,true,22.7f,t));
 assert(!g.step(t+540,true,22.8f,t+540));assert(g.step(t+1080,true,22.6f,t+1080));return t+1080;
}
int main(){d1_pump::Gate g;
 assert(!g.arm());g.driver_verified=true;assert(g.arm());
 assert(!g.step(1,true,22.59f,1));assert(!g.step(2,true,22.91f,2));
 uint32_t s=trigger(g,100);
 assert(g.pulses==1);assert(g.step(s+999,true,22.7f,s+999));assert(!g.step(s+1000,true,22.7f,s+1000));
 uint32_t off=s+1000;assert(!g.step(off+4999,true,22.7f,off+4999));
 s=trigger(g,off+5000);assert(g.pulses==2);
 assert(!g.step(s+100,true,22.5f,s+100));off=s+100;
 s=trigger(g,off+5000);assert(g.pulses==3);assert(!g.step(s+1000,true,22.7f,s+1000));off=s+1000;
 assert(!g.step(off+5000,true,22.7f,off+5000));assert(!g.step(off+5540,true,22.7f,off+5540));assert(!g.step(off+6080,true,22.7f,off+6080));assert(g.fault&&g.pulses==3);
 assert(!g.arm());g.reset();assert(g.arm());s=trigger(g,30000);
 assert(!g.step(s+10,false,22.7f,s+10));assert(!g.running&&!g.fault);
 assert(!g.step(s+5009,true,22.7f,s+5009));
 g.reset();assert(g.arm());s=trigger(g,0xfffffff0u-1080u);assert(s==0xfffffff0u);
 assert(g.step(983,true,22.7f,983));assert(!g.step(984,true,22.7f,984));
 g.reset();assert(g.arm());assert(!g.step(10000,true,22.5f,10000));assert(!g.step(10001,true,NAN,10001));assert(!g.step(14000,true,22.7f,10001));
 assert(isnan(d1_pump::Gate::percent(22.7f)));
 puts("PASS:1s pulse,5s settle,22.6..22.9 trigger band,target22.5,3 distinct frames,3-pulse cap,invalid/stale OFF,rollover,percentage unknown.");
}
