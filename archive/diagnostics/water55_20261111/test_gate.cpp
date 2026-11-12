#include "esp32/D1PumpGate.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
using d1_pump::Gate;
uint32_t trigger(Gate& g,uint32_t t,float cm=5.7f) {
 assert(!g.step(t,true,cm,t));assert(!g.step(t,true,cm,t));
 assert(!g.step(t+540,true,cm,t+540));assert(g.step(t+1080,true,cm,t+1080));return t+1080;
}
int main(){
 Gate g;assert(!g.enabled&&!g.running);assert(!g.arm());g.driver_verified=true;assert(g.arm());
 assert(!g.step(10,true,5.699f,10));assert(!g.running);
 auto t=trigger(g,100);assert(g.running);
 assert(g.step(t+1,true,5.5001f,t+1));
 assert(!g.step(t+2,true,5.5f,t+2));assert(!g.running&&!strcmp(g.reason,"TARGET_55CM"));
 assert(!g.step(t+540,true,5.6f,t+540));assert(!g.step(t+1080,true,5.69f,t+1080));
 t=trigger(g,t+2000,5.8f);g.disable();assert(!g.enabled&&!g.running);assert(!g.step(t+1,true,6.3f,t+1));
 g.reset();assert(g.arm());t=trigger(g,20000);assert(!g.step(t+1,false,5.9f,t+1));assert(g.fault&&!g.running);assert(!g.arm());
 g.reset();assert(g.arm());t=trigger(g,40000);assert(!g.step(t+1201,true,5.9f,t));assert(g.fault&&!g.running);
 g.reset();assert(g.arm());t=trigger(g,60000);assert(g.step(t+9999,true,5.6f,t+9999));
 assert(!g.step(t+10000,true,5.6f,t+10000));assert(g.fault&&!strcmp(g.reason,"TIME_LIMIT_OFF"));
 g.reset();assert(g.arm());t=trigger(g,80000);assert(!g.step(t+1,true,5.2f,t+1));assert(!g.fault&&!g.running);
 assert(!g.step(t+2,true,NAN,t+2));assert(!g.step(t+3,true,0,t+3));assert(!g.step(t+4,true,401,t+4));
 g.reset();assert(g.arm());t=trigger(g,0xfffffff0u-1080u);assert(t==0xfffffff0u);
 assert(g.step(t+9999u,true,5.6f,t+9999u));assert(!g.step(t+10000u,true,5.6f,t+10000u));
 assert(isnan(Gate::percent(5.7f)));
 puts("PASS: default OFF, verified enable, 5.7 start, 5.5 first-sample stop, hysteresis, repeat sample, disable, invalid/stale OFF, 10s timeout, rollover.");
}
