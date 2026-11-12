#include "m4/dispense_bench.h"
#include <cmath>
#include <iostream>
#include <iomanip>
#include <limits>
#include <stdexcept>
namespace db=m4::dispense_bench;
unsigned checks=0,cases=0;
#define CHECK(x) do{++checks;if(!(x))throw std::runtime_error("mass policy line="+std::to_string(__LINE__));}while(false)
struct Output:m4::servo_bench::Output {bool attached=false;unsigned opens=0;bool start(uint16_t)override{attached=true;return true;}bool write(uint16_t us)override{if(us==1560)++opens;return attached;}bool off()override{attached=false;return true;}};
struct Journal:db::Journal {bool pending=false;bool write(bool p,uint32_t)override{pending=p;return true;}};
struct Rig {
    Output o;Journal j;db::Controller c{o,j};db::Observation s{1000,1000,true,true,true,0,1};
    Rig(){c.boot(true,false,0);CHECK(c.configure({1400,1600,1500,1560,100,40,500,12,5,5,.2f,35,45}));CHECK(c.arm(s)==db::Reason::NONE);CHECK(c.start(1,35,s)==db::Reason::NONE);for(unsigned i=0;i<4;++i)step(0);}
    db::Event step(float grams){s.now_ms+=100;s.sample_at_ms=s.now_ms;s.grams=grams;s.fresh=true;return c.tick(s);}
    void finish(float final_mass,bool reached_aim=true){
        c.launchPulse(s);
        if(reached_aim)step(35);
        for(unsigned n=0;n<700&&c.state()!=db::State::COMPLETE&&c.state()!=db::State::FAULT;++n){
            auto e=step(final_mass);if(e==db::Event::NONE&&c.pulsePending())c.launchPulse(s);
        }
    }
};
void emit(float requested, Rig& f){
    ++cases;std::cout<<std::setprecision(9)<<"MASS_RESULT {\"source\":\"SIMULATED\",\"target_grams\":35,\"tolerance_grams\":5,\"requested_fixture_final\":"<<requested
        <<",\"actual_dispensed_grams\":"<<f.c.dispensed()<<",\"state\":\""<<db::name(f.c.state())<<"\",\"reason\":\""<<db::name(f.c.reason())<<"\",\"physical_pass\":false}\n";
}
int main(){try{
    for(float mass:{29.f,30.f,35.f,36.f,38.f,40.f,41.f}){
        Rig f;f.finish(mass);CHECK(!f.o.attached);
        if(mass>=30&&mass<=40){CHECK(f.c.state()==db::State::COMPLETE);CHECK(f.c.dispensed()==mass);}
        else CHECK(f.c.state()==db::State::FAULT);
        emit(mass,f);
    }
    {Rig f;f.finish(30,false);CHECK(f.c.state()!=db::State::COMPLETE);CHECK(f.o.opens>1);++cases;}
    {Rig f;f.s.now_ms+=100;f.s.sample_at_ms=f.s.now_ms;f.s.grams=40;f.c.launchPulse(f.s);CHECK(f.o.opens==0);for(unsigned n=0;n<40&&f.c.state()!=db::State::COMPLETE;++n)f.step(40);CHECK(f.c.state()==db::State::COMPLETE);++cases;}
    {Rig f;f.s.now_ms+=100;f.s.sample_at_ms=f.s.now_ms;f.s.grams=std::nextafter(40.f,std::numeric_limits<float>::infinity());f.c.launchPulse(f.s);CHECK(f.o.opens==0&&f.c.reason()==db::Reason::TARGET_OVERSHOOT);++cases;}
    {Rig f;f.finish(std::nextafter(30.f,0.f));CHECK(f.c.state()!=db::State::COMPLETE);++cases;}
    std::cout<<"MASS_POLICY_PASS cases="<<cases<<" checks="<<checks<<" target=35 tolerance=5 physical_pass=false\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
