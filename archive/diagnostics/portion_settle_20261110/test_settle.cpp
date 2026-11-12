#include "esp32/PortionSettleGate.h"
#include <stdio.h>
using portion_settle::Gate;using portion_settle::Result;
#define CHECK(x) do{if(!(x)){printf("FAIL line%d\n",__LINE__);return 1;}}while(0)
void feed(Gate&g,unsigned from,unsigned to,float value){for(unsigned n=from;n<=to;n+=100)g.step(n,true,value,n);}
int main(){
 Gate impact;impact.begin(100);feed(impact,100,300,49.4f);feed(impact,400,2000,35.2f);
 CHECK(impact.result==Result::VERIFIED&&fabsf(impact.measured-35.2f)<.01f);
 Gate pressure;pressure.begin(100);feed(pressure,100,400,48);feed(pressure,500,2200,0);
 CHECK(pressure.result==Result::UNDER); // False pressure is not food.
 Gate excess;excess.begin(100);feed(excess,100,2000,49);CHECK(excess.result==Result::OVER);
 Gate low;low.begin(100);feed(low,100,2000,34.9f);CHECK(low.result==Result::UNDER);
 Gate same;same.begin(100);for(unsigned n=100;n<1300;n+=100)same.step(n,true,35,100);
 CHECK(same.result==Result::WAITING);same.step(6100,false,0,100);CHECK(same.result==Result::TIMEOUT);
 Gate unstable;unstable.begin(100);for(unsigned n=100;n<=6100;n+=100)unstable.step(n,true,(n/100)%2?35:37,n);
 CHECK(unstable.result==Result::TIMEOUT);
 Gate missing;missing.begin(100);missing.step(200,false,NAN,200);missing.step(6100,false,NAN,200);CHECK(missing.result==Result::TIMEOUT);
 Gate invalid;invalid.begin(100);invalid.step(200,true,-10,200);CHECK(invalid.result==Result::INVALID);
 Gate wrap;wrap.begin(0xffffff00u);for(unsigned i=0;i<2000;i+=100){uint32_t n=0xffffff00u+i;wrap.step(n,true,35.5f,n);}
 CHECK(wrap.result==Result::VERIFIED);
 puts("PASS food-impact spike then35.2, pressure then0 rejected, real excess rejected, underfill, duplicate/stale, timeout, invalid, rollover");
}
