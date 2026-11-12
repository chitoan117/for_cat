#include "owner_behavior.h"
#include "m4/dispense_bench.h"
#include <iostream>
#include <limits>
#include <stdexcept>
namespace ob=forcat::owner_behavior;
namespace db=m4::dispense_bench;
unsigned checks=0,groups=0;
#define CHECK(x) do { ++checks; if(!(x))throw std::runtime_error("check line="+std::to_string(__LINE__)); } while(false)
template<class F>void test(const char* name,F body){body();++groups;std::cout<<"PASS "<<name<<'\n';}
const auto roi=forcat::food_roi::parseConfig("{\"enabled\":true,\"calibrated\":true,\"review_id\":\"SYNTHETIC_ONLY\",\"x1\":0.25,\"y1\":0.25,\"x2\":0.75,\"y2\":0.75}");
ob::Input owner(uint64_t now,unsigned sequence){ob::Input i;i.now=i.captured=now;i.sequence=sequence;i.identity=ob::Identity::OWNER_CAT;i.identity_source="SYNTHETIC_OWNER_FIXTURE";i.simulation=true;i.confidence=.95;i.distance_valid=true;i.distance=15;return i;}
ob::Decision arrival(ob::Policy& policy,uint64_t start=1000){ob::Decision d;for(unsigned n=0;n<4;++n)d=policy.update(owner(start+n*500,n+1));return d;}
struct FakeOutput: m4::servo_bench::Output {
    bool attached=false;unsigned opens=0;
    bool start(uint16_t)override{attached=true;return true;}
    bool write(uint16_t us)override{if(us==1560)++opens;return attached;}
    bool off()override{attached=false;return true;}
};
struct FakeJournal: db::Journal {bool pending=false;bool write(bool value,uint32_t)override{pending=value;return true;}};
struct Run {
    FakeOutput out;FakeJournal journal;db::Controller controller{out,journal};
    db::Observation sample{1000,1000,true,true,true,95,123};
    Run(){controller.boot(true,false,0);CHECK(controller.configure({1400,1600,1500,1560,100,40,500,12,5,.2f,.2f,35,45}));CHECK(controller.arm(sample)==db::Reason::NONE);CHECK(controller.start(1,35,sample)==db::Reason::NONE);}
    void finish(const std::string& fault="",float amount=35){
        unsigned closes=0;
        for(unsigned n=0;n<700&&controller.state()!=db::State::COMPLETE&&controller.state()!=db::State::FAULT;++n){
            sample.now_ms+=100;sample.sample_at_ms=sample.now_ms;sample.fresh=true;
            if(fault=="TIMEOUT"&&controller.baselineValid())sample.now_ms+=60001;
            if(fault=="HX_TIMEOUT"&&controller.baselineValid())sample.sample_at_ms=sample.now_ms-2000;
            if(fault=="INVALID"&&controller.baselineValid())sample.grams=std::numeric_limits<float>::quiet_NaN();
            if(fault=="DISCONNECT"&&controller.baselineValid())controller.abort(sample.now_ms);
            auto event=controller.tick(sample);
            if(event==db::Event::NONE&&controller.pulsePending())event=controller.launchPulse(sample);
            if(event==db::Event::CLOSE){++closes;if(fault!="NO_PROGRESS")sample.grams+=amount==35?(closes<3?15:5):amount;}
        }
    }
};
std::vector<ob::Weight> weights(double grams,uint64_t now,uint32_t generation=1){std::vector<ob::Weight> v;for(unsigned n=0;n<4;++n)v.push_back({grams,now-300+n*100,generation,true});return v;}
int main(int argc,char** argv){try{
    if(argc==2&&std::string(argv[1])=="--overshoot-probe"){
        Run r;r.finish("",36);std::cout<<"OVERSHOOT_PROBE state="<<db::name(r.controller.state())<<" reason="<<db::name(r.controller.reason())<<" physical_pass=false\n";return 0;
    }
    test("identity_public_unknown_other_dog_never_owner",[]{
        for(auto identity:{ob::Identity::UNKNOWN,ob::Identity::OTHER_CAT,ob::Identity::DOG}){ob::Policy p(roi);for(unsigned n=0;n<10;++n){auto i=owner(1000+n*500,n);i.identity=identity;CHECK(!p.update(i).would_request_35g);}}
        ob::Policy p(roi);for(unsigned n=0;n<10;++n){auto i=owner(1000+n*500,n);i.public_dataset=true;CHECK(!p.update(i).would_request_35g);}
    });
    test("no_model_no_real_owner_claim",[]{ob::Policy p(roi);for(unsigned n=0;n<8;++n){auto i=owner(1000+n*500,n);i.simulation=false;CHECK(!p.update(i).would_request_35g);}CHECK(!ob::Decision::actuator_execution);});
    test("owner_roi_ultrasound_debounce",[]{ob::Policy p(roi);CHECK(arrival(p).would_request_35g);CHECK(!p.update(owner(3000,5)).would_request_35g);});
    test("outside_roi_invalid_distance_mixed_dog",[]{for(unsigned kind=0;kind<4;++kind){ob::Policy p(roi);for(unsigned n=0;n<8;++n){auto i=owner(1000+n*500,n);if(kind==0)i.box={.01,.01,.1,.1};if(kind==1)i.distance=4;if(kind==2)i.distance_valid=false;if(kind==3)i.dog_present=true;CHECK(!p.update(i).would_request_35g);}}});
    test("lost_detection_stale_duplicate_and_cooldown",[]{
        ob::Policy p(roi);for(unsigned n=0;n<6;++n)CHECK(!p.update(owner(1000+n*500,1)).would_request_35g);
        auto stale=owner(5000,9);stale.captured=1000;CHECK(!p.update(stale).would_request_35g);
        CHECK(arrival(p,6000).would_request_35g);
        auto lost=owner(8500,5);lost.identity=ob::Identity::UNKNOWN;CHECK(p.update(lost).state=="LEAVING");
        CHECK(!arrival(p,9000).would_request_35g);
        lost.now=lost.captured=12000;CHECK(!p.update(lost).would_request_35g);
        CHECK(arrival(p,7210000).would_request_35g);
    });
    test("eating_vs_sniffing_does_not_top_up",[]{ob::Policy p(roi);CHECK(arrival(p).would_request_35g);for(unsigned n=0;n<6;++n)CHECK(!p.update(owner(3000+n*500,n+5)).would_request_35g);auto i=owner(6000,11);CHECK(p.update(i).state=="SNIFFING");i.now=i.captured=6500;i.sequence++;i.consumption_valid=true;i.consumed=5;auto d=p.update(i);CHECK(d.state=="EATING"&&!d.would_request_35g);});
    test("preference_configured_thresholds_and_attribution",[]{
        for(double consumed:{0.,5.,10.,18.,25.}){auto p=ob::preference(weights(35,1000),weights(35-consumed,61000),1000,61000,{},true,true);CHECK(p.valid&&p.consumed==consumed);CHECK(p.classification==(consumed>=18?"LIKE":consumed<=5?"DISLIKE":"UNCERTAIN"));}
        ob::PreferenceConfig c;c.like_min=12;c.dislike_max=3;CHECK(ob::preference(weights(35,1000),weights(22,61000),1000,61000,c,true,true).classification=="LIKE");
        CHECK(!ob::preference(weights(35,1000),weights(10,61000,2),1000,61000,{},true,true).valid);
        CHECK(!ob::preference(weights(35,1000),weights(36,61000),1000,61000,{},true,true).valid);
        CHECK(!ob::preference(weights(35,1000),weights(20,61000),1000,61000,{},false,true).valid);
    });
    test("35g_added_delta_and_duplicate",[]{Run r;CHECK(r.controller.start(1,35,r.sample)==db::Reason::DUPLICATE);r.finish();CHECK(r.controller.state()==db::State::COMPLETE);CHECK(r.controller.dispensed()==35&&r.sample.grams==130);CHECK(!r.out.attached&&!r.journal.pending);std::cout<<"SIM_FEED_RESULT {\"scenario\":\"nominal\",\"state\":\"COMPLETE\",\"target_grams\":35,\"dispensed_grams\":"<<r.controller.dispensed()<<",\"source\":\"SIMULATED\",\"physical_pass\":false}\n";});
    test("35g_tolerance_overshoot_is_not_success",[]{Run r;r.finish("",36);CHECK(r.controller.state()==db::State::FAULT);CHECK(std::string(db::name(r.controller.reason()))=="TARGET_OVERSHOOT");CHECK(!r.out.attached);std::cout<<"SIM_FEED_RESULT {\"scenario\":\"overshoot\",\"state\":\"FAULT\",\"reason\":\"TARGET_OVERSHOOT\",\"source\":\"SIMULATED\",\"physical_pass\":false}\n";});
    test("35g_timeout_invalid_sensor_disconnect_no_progress",[]{for(const char* fault:{"TIMEOUT","HX_TIMEOUT","INVALID","DISCONNECT","NO_PROGRESS"}){Run r;r.finish(fault);CHECK(r.controller.state()==db::State::FAULT);CHECK(!r.out.attached);std::cout<<"SIM_FEED_RESULT {\"scenario\":\""<<fault<<"\",\"state\":\"FAULT\",\"reason\":\""<<db::name(r.controller.reason())<<"\",\"source\":\"SIMULATED\",\"physical_pass\":false}\n";}});
    test("35g_uncalibrated_rejected_before_output",[]{FakeOutput out;FakeJournal j;db::Controller c(out,j);c.boot(true,false,0);CHECK(c.configure({1400,1600,1500,1560,100,40,500,5,5,.2f,.2f,35,45}));db::Observation s{1000,1000,true,false,true,95,1};CHECK(c.arm(s)==db::Reason::HX711_NOT_CALIBRATED&&out.opens==0);});
    std::cout<<"OFFLINE_LOGIC_PASS groups="<<groups<<" checks="<<checks<<" source=SIMULATED physical_pass=false\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
