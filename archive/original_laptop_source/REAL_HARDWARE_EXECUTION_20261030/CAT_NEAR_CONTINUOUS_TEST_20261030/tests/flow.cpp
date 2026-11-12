#include "continuous_dispense.h"
#include "user_settings.h"
#include "test_wire.h"
#include <iostream>
#include <stdexcept>
#include <string>
using namespace forcat_continuous;
unsigned checks=0;void check(bool b){if(!b)throw std::runtime_error("check "+std::to_string(checks));++checks;}
struct Output:m4::servo_bench::Output {unsigned opens=0,closes=0;bool attached=false;uint16_t pulse=0;
    bool start(uint16_t p)override{attached=true;pulse=p;return true;}bool off()override{attached=false;pulse=0;return true;}
    bool write(uint16_t p)override{pulse=p;if(p==1530)++opens;if(p==1470)++closes;return attached;}};
struct Store:Journal {bool pending=false,fail=false;uint32_t last=0;bool write(bool p,uint32_t id)override{if(fail)return false;pending=p;last=id;return true;}};
Settings fixture(){Settings s;s.pulses={1450,1550,1500,1495,1505,1530,1470,true,true,true};
    s.travel_timing_verified=true;s.opening_ms=300;s.closing_ms=400;s.neutral_hold_ms=100;s.settle_ms=500;s.stable_span_ms=300;
    s.baseline_timeout_ms=3000;s.settle_timeout_ms=3000;s.no_progress_ms=2000;s.total_timeout_ms=10000;s.stable_range_g=.2;
    s.closing_lead_g=10;s.supervised_early_close_trial=true;return s;}
struct Rig {Output o;Store j;Driver d{o};Controller c{d,j};Sample s{1000,1000,1,true,true,true,100};
    Rig(){c.boot(true,false,0);check(c.configure(fixture()));}
    void start(){check(c.arm(s,{},Mode::Supervised,true)==Reason::None);check(!o.attached);check(c.start(1,s)==Reason::None);}
    void tick(float g,bool hb=true){s.now_ms+=100;s.sample_at_ms=s.now_ms;s.grams=g;if(hb)c.heartbeat(s.now_ms);c.tick(s,{});}
    void open(){start();for(int i=0;i<4;++i)tick(100);check(c.state()==State::Opening);}
};
std::string frame(uint32_t seq,uint32_t echo=1000,uint32_t boot=7){auto s="FC1 "+std::to_string(boot)+" "+std::to_string(seq)+" "+std::to_string(echo)+" HB";char b[8];snprintf(b,sizeof(b),"*%04X",cat_test::crc(s.c_str(),unsigned(s.size())));return s+b;}
bool parse(cat_test::Receiver& r,std::string s,uint32_t now=1000){cat_test::Packet p;return r.parse(&s[0],7,now,p);}
int main(){try{
    check(!user_settings::settings().valid());check(!user_settings::hc_sr04_wiring_reviewed);
    {Rig r;check(r.c.closeTriggerGrams()==25);Position p{true,true,true,true,false,1000};check(r.c.arm(r.s,p,Mode::Automatic,true)==Reason::Config);}
    for(float final:{29.f,30.f,35.f,40.f,41.f}){Rig r;r.open();r.tick(124.99f);check(r.o.closes==0);r.tick(125);check(r.c.state()==State::Closing&&r.o.closes==1);
        for(int i=0;i<22;++i)r.tick(100+final);
        check(r.j.pending&&r.o.opens==1);check(r.c.state()==(final>=30&&final<=40?State::AwaitingOwner:State::Fault));
        check(r.c.state()!=State::Complete);check(r.c.arm(r.s,{},Mode::Supervised,true)==Reason::Inspection);}
    {Rig r;r.open();r.c.stop(r.s.now_ms);check(r.o.pulse==1500&&r.o.closes==0);r.tick(110);check(r.c.state()==State::Fault&&r.j.pending);}
    {Rig r;r.open();for(int i=0;i<16;++i)r.tick(110,false);check(r.c.reason()==Reason::Lease&&r.o.pulse==1500);}
    {Rig r;r.open();++r.s.generation;r.tick(120);check(r.c.reason()==Reason::Calibration);}
    {Rig r;r.j.fail=true;check(r.c.arm(r.s,{},Mode::Supervised,true)==Reason::None);check(r.c.start(1,r.s)==Reason::Persistence);check(r.o.opens==0);check(r.c.start(1,r.s)==Reason::Duplicate);}
    {Rig r;r.c.boot(true,true,7);check(!r.c.configure(fixture()));check(r.c.highwater()==7);}
    {cat_test::Gate g;check(!g.ready(1000));check(g.ai(1000,1,0,0,950,true));
        g.near(1000,true,20);g.near(1070,true,20);check(!g.ready(1070));g.near(1140,true,20);check(g.ready(1140));
        g.consume();check(!g.ready(1140));g.inspected();check(!g.ready(1140));check(!g.ai(1140,1,0,0,950,true));}
    {cat_test::Gate g;check(!g.ai(1000,1,500,251,950,true));check(g.ai(1000,1,500,250,950,true));check(!g.catFresh(1001));
        check(g.ai(1100,2,0,0,799,true));check(!g.catFresh(1100));check(g.ai(1200,3,0,0,950,true));
        g.near(1200,true,15);g.near(1270,true,20.01f);g.near(1340,true,15);g.near(1410,true,15);check(!g.ready(1410));
        g.near(1480,true,15);check(g.ready(1480));check(!g.ready(1681));}
    {cat_test::Receiver r;check(frame(1)=="FC1 7 1 1000 HB*0B5E");check(parse(r,frame(1)));check(!parse(r,frame(1)));check(!parse(r,frame(2,249),1000));
        check(!parse(r,frame(2,1001),1000));check(!parse(r,frame(2,1000,8)));auto bad=frame(2);bad[1]='X';check(!parse(r,bad));check(parse(r,frame(2)));}
    std::cout<<"FLOW_PASS checks="<<checks<<"\n";
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
