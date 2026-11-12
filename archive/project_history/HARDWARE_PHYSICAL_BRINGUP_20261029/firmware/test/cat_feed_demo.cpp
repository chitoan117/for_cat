#include <cstdio>
#include <cstdlib>
#include <limits>
#include "m4/cat_feed_demo.h"
namespace cf=m4::cat_feed_demo;
unsigned checks=0;
#define CHECK(x) do { ++checks; if (!(x)) { std::fprintf(stderr,"FAIL line%d: %s\n",__LINE__,#x); std::exit(1); } } while(0)
struct Out: m4::servo_bench::Output {
  bool attached=false,fail=false;
  unsigned opens=0,closes=0,offs=0;
  bool start(uint16_t us) override { CHECK(us==1500); if(fail)return false; attached=true;++closes;return true; }
  bool write(uint16_t us) override { CHECK(us==1000 || us==1500); if(fail || !attached)return false; if(us==1000)++opens;else++closes;return true; }
  bool off() override { attached=false;++offs;return !fail; }
};
struct Journal:cf::Journal {
  bool pending=false,fail=false; unsigned writes=0;uint32_t id=0;
  bool write(bool p,uint32_t n) override {++writes;if(fail)return false;pending=p;id=n;return true;}
};
struct F {
  Out out;Journal j;cf::Controller c{out,j};cf::Sample s{0,0,true,true,-1.3f,123};
  bool lease=true;
  F(){c.boot(true,false,0);}
  void step(uint32_t ms=100){s.now+=ms;s.stamp=s.now;s.fresh=true;if(lease)c.catLease(1,s.now);c.tick(s);}
  void start(){CHECK(c.start(1,s));CHECK(j.pending && j.id==1);}
  void open(){start();for(int i=0;i<4;++i)step();CHECK(c.state()==cf::State::OPEN && out.opens==1);}
  void settle(){for(int i=0;i<30 && c.active();++i)step();}
};
int main(){
  {F f;for(int i=0;i<100;++i)f.step();CHECK(f.out.opens==0 && f.out.closes==0);}
  {F f;f.s.valid=false;CHECK(!f.c.start(1,f.s));CHECK(f.out.opens==0 && f.j.writes==0);}
  {F f;f.c.boot(false,false,0);CHECK(!f.c.start(1,f.s));CHECK(f.c.initializeJournal());CHECK(f.c.start(1,f.s));}
  {F f;f.c.boot(false,true,0);CHECK(!f.c.initializeJournal());CHECK(!f.c.start(1,f.s));}
  {F f;f.open();CHECK(f.c.baselineValid() && f.c.baseline()<-1.29f);f.s.grams=33.8f;f.step();
   CHECK(f.c.state()==cf::State::CLOSING && f.c.reason()==cf::Reason::TARGET);CHECK(f.out.closes==2);
   f.settle();CHECK(f.c.state()==cf::State::COMPLETE && !f.j.pending && !f.out.attached);
   CHECK(f.c.delta()>35.09f && f.c.delta()<35.11f);CHECK(!f.c.start(1,f.s));CHECK(f.out.opens==1);}
  {F f;f.open();f.c.abort(f.s.now,cf::Reason::DOG_OR_CAT_LOST);CHECK(f.c.state()==cf::State::CLOSING);
   const auto now=f.s.now;f.c.abort(now+300);f.step(350);CHECK(f.c.state()==cf::State::FAULT && !f.out.attached);
   CHECK(f.c.reason()==cf::Reason::DOG_OR_CAT_LOST && f.j.pending && f.out.opens==1);}
  {F f;f.open();f.lease=false;f.step(1000);CHECK(f.c.reason()==cf::Reason::LINK_TIMEOUT);f.step(350);CHECK(!f.out.attached);}
  {F f;f.open();f.s.valid=false;f.step();CHECK(f.c.reason()==cf::Reason::SCALE_INVALID);f.settle();CHECK(!f.out.attached);}
  {F f;f.open();f.s.calibration_id=456;f.step();CHECK(f.c.reason()==cf::Reason::CALIBRATION_CHANGED);f.settle();CHECK(!f.out.attached);}
  {F f;f.open();f.s.grams=9;f.step();f.s.grams=7;f.step();CHECK(f.c.reason()==cf::Reason::WEIGHT_DROP);f.settle();CHECK(!f.out.attached);}
  {F f;f.open();f.s.grams=41;f.step();CHECK(f.c.reason()==cf::Reason::OVERSHOOT);f.settle();CHECK(!f.out.attached);}
  {F f;f.open();for(int i=0;i<32 && f.c.state()==cf::State::OPEN;++i)f.step();CHECK(f.c.reason()==cf::Reason::NO_PROGRESS);}
  {F f;f.open();for(int i=0;i<80 && f.c.state()==cf::State::OPEN;++i){f.s.grams+=0.3f;f.step(200);}CHECK(f.c.reason()==cf::Reason::MAX_OPEN);}
  {F f;f.start();for(int i=0;i<62 && f.c.state()==cf::State::BASELINE;++i){f.s.grams=(i%2)?3:0;f.step();}
   CHECK(f.c.reason()==cf::Reason::BASELINE_UNSTABLE && f.out.opens==0);}
  {F f;f.open();f.s.grams=33.8f;f.step();f.s.grams=25;f.settle();CHECK(f.c.state()==cf::State::FAULT && f.c.reason()==cf::Reason::FINAL_UNDER_TARGET);CHECK(f.out.opens==1);}
  {F f;f.j.fail=true;CHECK(!f.c.start(1,f.s));CHECK(f.c.reason()==cf::Reason::JOURNAL_ERROR && f.out.opens==0);}
  {F f;f.open();f.c.boot(true,true,1);CHECK(!f.out.attached && f.c.pending());CHECK(!f.c.start(1,f.s) && !f.c.start(2,f.s));CHECK(f.out.opens==1);}
  {F f;f.start();f.lease=false;f.step(1000);CHECK(f.c.state()==cf::State::FAULT && f.out.opens==0);}
  {F f;f.open();f.s.grams=std::numeric_limits<float>::quiet_NaN();f.step();CHECK(f.c.reason()==cf::Reason::SCALE_INVALID);}
  {F f;f.start();for(int i=0;i<10;++i){f.s.now+=10;f.s.fresh=false;f.c.catLease(1,f.s.now);f.c.tick(f.s);}CHECK(f.out.opens==0);}
  std::printf("CAT_FEED_POLICY_PASS assertions=%u fake_io_only=true\n",checks);
}
