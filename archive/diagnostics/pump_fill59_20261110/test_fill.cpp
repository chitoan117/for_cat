#include "esp32/PumpFill59Gate.h"
#include <stdio.h>
#define CHECK(x) do { if(!(x)){printf("FAIL line%d\n",__LINE__);return 1;} } while(0)
int main(){
 using pump_fill59::Gate;
 Gate g;
 CHECK(!g.start(0,true,5.9f,0));
 CHECK(!g.start(0,true,6.41f,0));
 CHECK(!g.start(1500,true,6.2f,0));
 CHECK(!g.start(0,false,6.2f,0));
 CHECK(!g.start(0,true,NAN,0));
 CHECK(g.start(1000,true,6.2f,1000));
 CHECK(g.step(1500,true,6.1f,1500));
 CHECK(!g.start(1800,true,6.2f,1800));
 CHECK(g.started==1000);
 CHECK(g.step(2100,true,6.0f,2100)); // No forced 1s pulse stop.
 CHECK(!g.step(2200,true,5.9f,2200));
 CHECK(!g.running);
 CHECK(!g.step(2300,true,6.2f,2300)); // Does not restart itself.
 CHECK(g.start(3000,true,6.2f,3000));
 CHECK(!g.step(3010,false,6.2f,3010));
 CHECK(g.start(4000,true,6.2f,4000));
 CHECK(!g.step(5201,true,6.2f,4000));
 CHECK(g.start(6000,true,6.2f,6000));
 CHECK(g.step(15999,true,6.2f,15999));
 CHECK(!g.step(16000,true,6.2f,16000));
 CHECK(g.start(0xffffff00u,true,6.2f,0xffffff00u));
 CHECK(g.step(0x100u,true,6.1f,0x100u));
 CHECK(!g.step(0x200u,true,5.8f,0x200u));
 CHECK(g.start(7000,true,6.2f,7000));
 g.stop(); CHECK(!g.running);
 printf("PASS target cutoff, continuous beyond1s, invalid/stale OFF, native10s limit, no replay, rollover, operator OFF\n");
 return 0;
}
