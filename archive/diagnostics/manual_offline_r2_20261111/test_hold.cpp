#include "esp32/ButtonInspectionHold.h"
#include <assert.h>
#include <stdio.h>
int main(){
 button_inspection::Hold h;
 assert(!h.step(0,true,true));assert(!h.step(60000,true,true));
 assert(!h.step(60001,false,true));assert(!h.step(61000,true,true));
 assert(!h.step(65999,true,true));assert(h.step(66000,true,true));assert(!h.step(80000,true,true));
 h={};assert(!h.step(0,false,false));assert(!h.step(1,true,false));assert(!h.step(10000,true,true));
 assert(!h.step(10001,false,true));assert(!h.step(10002,true,true));assert(!h.step(12000,false,true));
 assert(!h.step(13000,true,true));assert(!h.step(17999,true,true));assert(h.step(18000,true,true));
 h={};h.step(0,false,true);h.step(1,true,true);assert(!h.step(5001,true,false));assert(!h.step(10001,true,true));
 h={};h.step(0xffffffe0u,false,true);h.step(0xfffffff0u,true,true);assert(!h.step(4983,true,true));assert(h.step(4984,true,true));
 puts("PASS: boot-held/stuck button cannot acknowledge; fresh press+continuous5s needed, bounce/release resets, one-shot until release, no arming when lock appears mid-press, unlocking cancels hold, rollover.");
}
