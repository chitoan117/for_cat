#include "m4/quad_level_sampler.h"
#include <array>
#include <cstdio>
#include <stdexcept>
#include <vector>
struct Fake final:m4::PinIO {
  uint64_t now=0;
  std::array<bool,64> levels{};
  std::array<uint64_t,4> rise{},fall{};
  std::array<unsigned,4> pulses{};
  std::array<bool,4> missing{};
  std::vector<uint64_t> starts;
  unsigned overlap=0,forbidden=0;
  int trig[4]{12,14,16,18},echo[4]{13,15,17,10};
  bool inputAllowed(int pin) const override{return pin>=4 && pin<=21 && pin!=6 && pin!=7;}
  bool outputAllowed(int pin) const override{return inputAllowed(pin) && pin!=10;}
  void input(int pin,m4::Pull) override{if(pin==6||pin==7)++forbidden;}
  void output(int pin) override{if(pin==6||pin==7||pin==10)++forbidden;}
  bool read(int pin) override{
    for(unsigned i=0;i<4;++i)if(pin==echo[i])return !missing[i] && rise[i] && now>=rise[i] && now<fall[i];
    return levels[pin];
  }
  void write(int pin,bool high) override{
    if(pin==6||pin==7||pin==10)++forbidden;
    for(unsigned i=0;i<4;++i)if(pin==trig[i] && levels[pin] && !high){
      for(unsigned j=0;j<4;++j)if(fall[j]>now)++overlap;
      ++pulses[i];starts.push_back(now);rise[i]=now+200;fall[i]=rise[i]+1750+i*200;
    }
    levels[pin]=high;
  }
  void pauseMicros(uint32_t) override{}
  void enterCritical() override{}
  void exitCritical() override{}
};
unsigned assertions=0;
void check(bool ok){++assertions;if(!ok)throw std::runtime_error("quad assertion failed");}
void guard_case(unsigned guard){
 Fake io;m4::LevelSensor a(io),b(io),c(io),d(io);m4::QuadLevelSampler q(a,b,c,d);
 check(q.guardMs()==80);
 for(unsigned bad:{0u,59u,61u,79u,81u,99u,101u,10000u})check(!q.setGuardMs(bad));
 check(q.setGuardMs(guard));check(q.guardMs()==guard);
 for(unsigned i=0;i<4;++i)check(q.selectOnly(i,{{io.trig[i],true},{io.echo[i],true},1,400,30000,.0343f}));
 check(q.selectAllReviewed());bool busy_guard_checked=false;
 for(;io.now<2500000;io.now+=5){
   q.poll(uint32_t(io.now),uint32_t(io.now/1000));q.start(uint32_t(io.now),uint32_t(io.now/1000));
   if(q.busy() && !busy_guard_checked){check(!q.setGuardMs(80));check(q.guardMs()==guard);busy_guard_checked=true;}
 }
 check(busy_guard_checked && io.overlap==0 && io.forbidden==0);
 bool near_requested_guard=false;
 for(size_t i=1;i<io.starts.size();++i){
  const auto gap=io.starts[i]-io.starts[i-1];check(gap>=guard*1000);
  if(gap<(guard+5)*1000)near_requested_guard=true;
 }
 check(near_requested_guard);
 for(auto count:io.pulses)check(count>=3);
}
int main(){
 Fake io;m4::LevelSensor a(io),b(io),c(io),d(io);m4::QuadLevelSampler q(a,b,c,d);
 auto config=[&](unsigned i){return m4::UltrasonicConfig{{io.trig[i],true},{io.echo[i],true},1,400,30000,.0343f};};
 auto run=[&](unsigned ms){const auto end=io.now+uint64_t(ms)*1000;for(;io.now<end;io.now+=5){q.poll(uint32_t(io.now),uint32_t(io.now/1000));q.start(uint32_t(io.now),uint32_t(io.now/1000));}};
 run(700);for(unsigned i=0;i<4;++i)check(io.pulses[i]==0);
 check(!q.selectAllReviewed());check(!q.selectOnly(4,config(0)));
 check(q.selectOnly(0,config(0)));run(1300);check(io.pulses[0]>=2);
 for(unsigned i=1;i<4;++i)check(io.pulses[i]==0);
 while(q.busy())run(1);
 for(unsigned i=1;i<4;++i){check(q.selectOnly(i,config(i)));for(unsigned j=0;j<4;++j)check(q.enabled(j)==(i==j));}
 check(q.selectAllReviewed());run(2500);
 for(unsigned i=0;i<4;++i)check(io.pulses[i]>=3);
 check(io.overlap==0 && io.forbidden==0);
 for(size_t i=1;i<io.starts.size();++i)check(io.starts[i]-io.starts[i-1]>=80000);
 io.missing[2]=true;run(1800);check(!c.distance.filtered.valid && c.distance.timeoutCount()>0);
 check(q.hasUpdate(2) && q.lastValid(2).valid && q.lastValid(2).value>0);
 check(a.distance.filtered.valid && b.distance.filtered.valid && d.distance.filtered.valid);
 while(q.busy())run(1);
 check(q.disableAll());auto total=io.starts.size();run(1000);check(io.starts.size()==total);
 check(!a.distance.filtered.valid && !b.distance.filtered.valid && !c.distance.filtered.valid && !d.distance.filtered.valid);
 check(!q.selectOnly(1,{{6,true},{15,true},1,400,30000,.0343f}));check(!q.enabled(1));
 check(!q.selectAllReviewed());
 // Wrap-safe unsigned scheduling after millis/micros rollover.
 check(q.selectOnly(0,config(0)));io.now=(uint64_t(1)<<32)*1000-150000;run(900);check(a.distance.filtered.valid);
 check(io.forbidden==0 && io.overlap==0);
 for(unsigned guard:{60u,80u,100u})guard_case(guard);
 std::printf("QUAD_SCHEDULER_SOFTWARE_READY assertions=%u\n",assertions);
}
