#include "esp32/MealPreferenceGate.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){printf("FAIL line%d\n",__LINE__);return 1;}}while(0)
using meal_behavior::Tracker;using meal_behavior::Phase;
void settle(Tracker& t,uint32_t a,uint32_t b,float g){for(uint32_t n=a;n<=b;n+=100)t.sample(n,true,g,n);}
int main(){
 Tracker t;
 CHECK(!t.finish(10000));
 t.begin(100,'A');settle(t,100,4200,35);CHECK(t.phase==Phase::OBSERVING);
 settle(t,4300,8000,32);CHECK(!strcmp(t.preference(),"WAITING")); // Early 3g pause never DISLIKE.
 CHECK(!t.finish(8000));
 settle(t,8100,20000,2);CHECK(t.finish(20000));CHECK(!strcmp(t.preference(),"LIKE"));
 CHECK(t.food=='A'&&t.consumed==33);CHECK(!t.finish(20001));
 settle(t,20100,21000,35);CHECK(t.consumed==33); // Final is immutable.
 Tracker b;b.begin(100,'B');settle(b,100,4200,35);settle(b,4300,125000,35);
 CHECK(b.phase==Phase::FINAL&&!strcmp(b.preference(),"DISLIKE")&&b.consumed==0);
 Tracker unlike;unlike.begin(100,'A');settle(unlike,100,4200,35);settle(unlike,4300,125000,31);
 CHECK(!strcmp(unlike.preference(),"DISLIKE")); // A is not preset LIKE.
 Tracker blike;blike.begin(100,'B');settle(blike,100,4200,35);settle(blike,4300,125000,10);
 CHECK(!strcmp(blike.preference(),"LIKE")); // B is not preset DISLIKE.
 Tracker bad;bad.begin(100,'A');settle(bad,100,4200,35);bad.sample(4300,true,-10,4300);
 CHECK(bad.phase==Phase::INVALID&&!bad.finish(20000));
 Tracker no_start;no_start.begin(100,'A');settle(no_start,100,31000,3);
 CHECK(no_start.phase==Phase::INVALID&&!no_start.finish(40000));
 Tracker missing;missing.begin(100,'A');settle(missing,100,4200,35);missing.sample(15000,false,NAN,0);
 CHECK(missing.phase==Phase::INVALID);
 Tracker pressure;pressure.begin(100,'A');settle(pressure,100,4200,35);settle(pressure,4300,125000,500);
 CHECK(pressure.phase!=Phase::FINAL);CHECK(!pressure.finish(125000));
 Tracker rollover;rollover.begin(0xfffff000u,'A');
 for(unsigned i=0;i<130000;i+=100){uint32_t n=0xfffff000u+i;rollover.sample(n,true,i<4500?35:2,n);}
 CHECK(rollover.phase==Phase::FINAL&&!strcmp(rollover.preference(),"LIKE"));
 puts("PASS delayed final, zero-eaten meal, A/B symmetry, measured baseline, stable weight, invalid/stale, dedup, immutable result, rollover");
}
