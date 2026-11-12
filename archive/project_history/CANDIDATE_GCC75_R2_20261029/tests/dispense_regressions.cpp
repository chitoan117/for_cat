// C++14/R2: actual portable controller, synthetic observations and fake output.
#include "m4/dispense_bench.h"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
namespace db=m4::dispense_bench;
static_assert(static_cast<int>(db::Reason::PERSISTENCE_FAULT)==19,"existing reason ordinal changed");
static_assert(static_cast<int>(db::Reason::TARGET_OVERSHOOT)==20,"overshoot reason must be appended");
static_assert(std::is_standard_layout<db::Observation>::value,"observation source ABI changed");
unsigned checks=0,cases=0;
#define REQUIRE(x) do {++checks;if(!(x))throw std::runtime_error("R2 check line="+std::to_string(__LINE__));}while(false)
struct FakeOutput: m4::servo_bench::Output {
    bool attached=false;unsigned opens=0;
    bool start(uint16_t)override{attached=true;return true;}
    bool write(uint16_t us)override{if(!attached)return false;if(us==1560)++opens;return true;}
    bool off()override{attached=false;return true;}
};
struct FakeJournal:db::Journal {
    bool pending=false,fail_clear=false;
    bool write(bool next,uint32_t)override{if(!next&&fail_clear)return false;pending=next;return true;}
};
struct Fixture {
    FakeOutput output;FakeJournal journal;db::Controller controller{output,journal};
    db::Observation observation{1000,1000,true,true,true,95.0f,123};
    explicit Fixture(float range=.2f){
        controller.boot(true,false,0);
        REQUIRE(controller.configure({1400,1600,1500,1560,100,40,500,12,5,.2f,range,35,45}));
        REQUIRE(controller.arm(observation)==db::Reason::NONE);
        REQUIRE(controller.start(1,35,observation)==db::Reason::NONE);
        for(unsigned n=0;n<4;++n)step(95);
        REQUIRE(controller.baselineValid()&&controller.pulsePending());
    }
    db::Event step(float grams,bool fresh=true){
        observation.now_ms+=100;
        if(fresh)observation.sample_at_ms=observation.now_ms;
        observation.fresh=fresh;observation.grams=grams;
        return controller.tick(observation);
    }
    void pulse(){REQUIRE(controller.launchPulse(observation)!=db::Event::FAULT);}
    void drain(){
        for(unsigned n=0;n<20&&controller.state()==db::State::FAULT_CLOSING;++n){
            observation.now_ms+=100;controller.tick(observation);
        }
    }
    void finish(float delta){
        pulse();
        for(unsigned n=0;n<700&&controller.state()!=db::State::FAULT&&controller.state()!=db::State::COMPLETE;++n){
            const auto event=step(95+delta);
            if(event==db::Event::NONE&&controller.pulsePending())controller.launchPulse(observation);
        }
        drain();
    }
    void measuredWindow(){
        pulse();
        for(unsigned n=0;n<40;++n){
            step(95);
            if(controller.state()==db::State::MEASURE&&!controller.pulsePending())return;
        }
        throw std::runtime_error("MEASURE not reached");
    }
};
void emit(const char* name,Fixture& f){
    ++cases;
    const bool success=f.controller.state()==db::State::COMPLETE;
    REQUIRE(!f.output.attached);
    std::cout<<std::setprecision(9)<<"R2_FEED_RESULT {\"scenario\":\""<<name<<"\",\"state\":\""<<db::name(f.controller.state())
        <<"\",\"reason\":\""<<db::name(f.controller.reason())<<"\",\"target_grams\":35,\"dispensed_grams\":"<<f.controller.dispensed()
        <<",\"observed_added_grams\":";
    if(std::isfinite(f.observation.grams))std::cout<<(f.observation.grams-95);
    else std::cout<<"null";
    std::cout<<",\"final_status\":\""<<(success?"SUCCESS":"ERROR")<<"\",\"fake_opens\":"<<f.output.opens
        <<",\"source\":\"SIMULATED\",\"physical_pass\":false}\n";
}
void probes(){
    Fixture launch;launch.observation.now_ms+=100;launch.observation.sample_at_ms=launch.observation.now_ms;
    launch.observation.grams=131;launch.controller.launchPulse(launch.observation);launch.drain();
    std::cout<<"DIRECT_LAUNCH_36 state="<<db::name(launch.controller.state())<<" opens="<<launch.output.opens<<'\n';
    Fixture masked(5);masked.measuredWindow();
    masked.step(129.8f);masked.step(129.8f);masked.step(129.8f);masked.step(131);masked.drain();
    std::cout<<"MASKED_WINDOW_36 state="<<db::name(masked.controller.state())<<" reason="<<db::name(masked.controller.reason())<<'\n';
}
int main(int argc,char** argv){try{
    std::cout.imbue(std::locale::classic());
    if(argc==2&&std::string(argv[1])=="--audit-probes"){probes();return 0;}
    for(const auto item:{std::pair<const char*,float>{"nominal",35}, {"lower_bound",34.8f},{"upper_bound",35.2f}}){
        Fixture f;f.finish(item.second);REQUIRE(f.controller.state()==db::State::COMPLETE);
        REQUIRE(std::fabs(f.controller.dispensed()-item.second)<.0001f);REQUIRE(!f.journal.pending);emit(item.first,f);
    }
    for(const auto item:{std::pair<const char*,float>{"over_band",35.21f},{"overshoot_36",36}}){
        Fixture f;f.finish(item.second);REQUIRE(f.controller.state()==db::State::FAULT);
        REQUIRE(std::string(db::name(f.controller.reason()))=="TARGET_OVERSHOOT");REQUIRE(f.journal.pending);emit(item.first,f);
    }
    {Fixture f;f.finish(34.79f);REQUIRE(f.controller.state()!=db::State::COMPLETE);emit("under_band",f);}
    {Fixture f;f.observation.now_ms+=100;f.observation.sample_at_ms=f.observation.now_ms;f.observation.grams=131;
     REQUIRE(f.controller.launchPulse(f.observation)==db::Event::FAULT);f.drain();REQUIRE(f.output.opens==0);
     REQUIRE(std::string(db::name(f.controller.reason()))=="TARGET_OVERSHOOT");emit("direct_launch_36",f);}
    {Fixture f(5);f.measuredWindow();f.step(129.8f);f.step(129.8f);f.step(129.8f);f.step(131);f.drain();
     REQUIRE(f.controller.state()==db::State::FAULT&&std::string(db::name(f.controller.reason()))=="TARGET_OVERSHOOT");emit("masked_window_36",f);}
    {Fixture f;f.pulse();f.observation.now_ms+=60000;f.controller.tick(f.observation);f.drain();
     REQUIRE(f.controller.reason()==db::Reason::MAX_TIME_REACHED);emit("timeout",f);}
    {Fixture f;f.pulse();f.observation.now_ms+=1600;f.controller.tick(f.observation);f.drain();
     REQUIRE(f.controller.reason()==db::Reason::HX711_NOT_READY);emit("stale_hx",f);}
    {Fixture f;f.pulse();f.observation.healthy=false;f.step(95);f.drain();
     REQUIRE(f.controller.reason()==db::Reason::HX711_NOT_READY);emit("invalid_hx",f);}
    {Fixture f;f.pulse();f.step(std::numeric_limits<float>::quiet_NaN());f.drain();
     REQUIRE(f.controller.reason()==db::Reason::HX711_NOT_READY);emit("nonfinite_hx",f);}
    {Fixture f;f.pulse();f.controller.abort(f.observation.now_ms);f.drain();
     REQUIRE(f.controller.reason()==db::Reason::ABORTED);emit("disconnect",f);}
    {Fixture f;const auto opens=f.output.opens;REQUIRE(f.controller.start(1,35,f.observation)==db::Reason::DUPLICATE);
     REQUIRE(f.output.opens==opens);f.finish(35);REQUIRE(f.controller.state()==db::State::COMPLETE);
     REQUIRE(f.controller.start(1,35,f.observation)==db::Reason::DUPLICATE);emit("duplicate",f);}
    {Fixture f;f.measuredWindow();for(unsigned n=0;n<20&&f.controller.state()!=db::State::FAULT;++n)f.step(130,false);
     f.drain();REQUIRE(f.controller.state()!=db::State::COMPLETE);emit("duplicate_samples",f);}
    {Fixture f;f.journal.fail_clear=true;f.finish(35);
     REQUIRE(f.controller.state()==db::State::FAULT&&f.controller.reason()==db::Reason::PERSISTENCE_FAULT);emit("journal_failure",f);}
    std::cout<<"R2_DISPENSE_PASS cases="<<cases<<" checks="<<checks<<" source=SIMULATED physical_pass=false\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
