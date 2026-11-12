// Reuse the existing portable ESP32 policy, ONLY with in-memory fake output/HX.
// Not linked into the serial bridge, backend, AI or any physical firmware image.
#include "m4/dispense_bench.h"
#include <iostream>
#include <stdexcept>
namespace db=m4::dispense_bench;
struct FakeOutput: m4::servo_bench::Output {
    bool attached=false;unsigned opens=0,starts=0,offs=0;
    bool start(uint16_t)override{++starts;attached=true;return true;}
    bool write(uint16_t us)override{if(!attached)return false;if(us==1560)++opens;return true;}
    bool off()override{attached=false;++offs;return true;}
};
struct FakeJournal:db::Journal {bool pending=false;bool write(bool next,uint32_t)override{pending=next;return true;}};
int main(){
    unsigned checks=0;auto check=[&](bool ok){++checks;if(!ok)throw std::runtime_error("35g fake-HX check "+std::to_string(checks));};
    try{
        FakeOutput output;FakeJournal journal;db::Controller controller(output,journal);
        controller.boot(true,false,0);
        db::Settings config{1400,1600,1500,1560,100,40,500,5,5.0f,0.2f,0.2f,35.0f,45.0f};
        check(controller.configure(config));
        db::Observation observation{0,0,true,false,true,10.0f,123};
        check(controller.arm(observation)==db::Reason::HX711_NOT_CALIBRATED);
        check(output.starts==0 && output.opens==0);
        observation.calibrated=true;
        check(controller.arm(observation)==db::Reason::NONE);
        check(controller.start(1,35.0f,observation)==db::Reason::NONE);
        unsigned measured_pulses=0;
        for(unsigned i=0;i<500 && controller.state()!=db::State::COMPLETE;++i){
            observation.now_ms+=100;observation.sample_at_ms=observation.now_ms;observation.fresh=true;
            auto event=controller.tick(observation);
            if(event==db::Event::NONE && controller.pulsePending())event=controller.launchPulse(observation);
            if(event==db::Event::CLOSE){++measured_pulses;observation.grams+=(measured_pulses<3?15.0f:5.0f);}
        }
        check(controller.state()==db::State::COMPLETE);
        check(controller.dispensed()==35.0f); // baseline10 -> after45 => ADDED35
        check(observation.grams==45.0f && measured_pulses==3);
        check(!output.attached && !journal.pending);
        std::cout<<"35g actual-added-delta preparation: "<<checks<<" checks PASS; FAKE HX/output only, PHYSICAL NOT TESTED\n";
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
