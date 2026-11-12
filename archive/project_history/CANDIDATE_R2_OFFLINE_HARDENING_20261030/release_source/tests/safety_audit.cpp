#include "m4/dispense_bench.h"
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
namespace db=m4::dispense_bench;
unsigned checks=0,cases=0;
#define CHECK(x) do{++checks;if(!(x))throw std::runtime_error("SAFETY check line="+std::to_string(__LINE__));}while(false)
struct Output:m4::servo_bench::Output {
    bool attached=false,opened=false,abort_on_open=false;unsigned opens=0;
    std::function<void()> abort;
    bool start(uint16_t)override{attached=true;return true;}
    bool write(uint16_t value)override{
        if(!attached)return false;
        if(value==1560){++opens;if(abort_on_open){abort_on_open=false;abort();}opened=true;}
        else opened=false;
        return true;
    }
    bool off()override{attached=opened=false;return true;}
};
struct Journal:db::Journal {
    bool pending=false,abort_start=false,abort_complete=false,fail_clear=false;
    std::function<void()> abort;
    bool write(bool value,uint32_t)override{
        if(!value&&fail_clear)return false;
        pending=value;
        if(value&&abort_start){abort_start=false;abort();}
        if(!value&&abort_complete){abort_complete=false;abort();}
        return true;
    }
};
struct Fixture {
    Output out;Journal journal;db::Controller c{out,journal};
    db::Observation s{1000,1000,true,true,true,95,123};
    Fixture(){c.boot(true,false,0);CHECK(c.configure({1400,1600,1500,1560,100,40,500,12,5,5,.2f,35,45}));
        CHECK(c.arm(s)==db::Reason::NONE);out.abort=journal.abort=[this]{c.abort(s.now_ms);};}
    void start(){CHECK(c.start(1,35,s)==db::Reason::NONE);}
    db::Event tick(float grams=95,bool fresh=true){s.now_ms+=100;s.sample_at_ms=s.now_ms;s.grams=grams;s.fresh=fresh;return c.tick(s);}
    void baseline(){start();for(unsigned i=0;i<4;++i)tick();CHECK(c.baselineValid());}
    void measure(){baseline();c.launchPulse(s);for(unsigned i=0;i<40;++i){tick();if(c.state()==db::State::MEASURE&&!c.pulsePending())return;}throw std::runtime_error("measure failed");}
    void close(){for(unsigned i=0;i<20&&c.state()==db::State::FAULT_CLOSING;++i){s.now_ms+=100;c.tick(s);}}
    void finish(float delta){baseline();c.launchPulse(s);for(unsigned i=0;i<700&&c.state()!=db::State::COMPLETE&&c.state()!=db::State::FAULT;++i){auto e=tick(95+delta);if(e==db::Event::NONE&&c.pulsePending())c.launchPulse(s);}close();}
};
void observation(const char* label,Fixture& f){std::cout<<"OBS "<<label<<" state="<<db::name(f.c.state())<<" reason="<<db::name(f.c.reason())<<" opens="<<f.out.opens<<" pending="<<f.journal.pending<<'\n';}
void probes(){
    {Fixture f;f.baseline();f.s.now_ms+=100;f.s.sample_at_ms=f.s.now_ms;f.s.grams=131;f.s.fresh=false;f.c.launchPulse(f.s);f.close();observation("unfresh_pulse",f);}
    {Fixture f;f.measure();const auto start=f.s.now_ms;for(unsigned n=0;n<4;++n){f.s.now_ms+=100;f.s.sample_at_ms=start+100-n*100;f.s.grams=130;f.c.tick(f.s);}f.close();observation("backward_samples",f);}
    {Fixture f;f.journal.abort_complete=true;f.finish(35);observation("cancel_during_completion",f);}
    {Fixture f;f.journal.abort_start=true;f.c.start(1,35,f.s);f.close();observation("cancel_during_start",f);}
    {Fixture f;f.s.calibration_id=124;f.c.start(1,35,f.s);f.close();observation("calibration_changed_before_start",f);}
    {Fixture f;f.baseline();f.out.abort_on_open=true;f.c.launchPulse(f.s);observation("cancel_during_open_before_close_hold",f);f.close();}
}
template<class F>void test(const char* label,F body){body();++cases;std::cout<<"PASS "<<label<<'\n';}
int main(int argc,char** argv){try{
    if(argc==2&&std::string(argv[1])=="--probe"){probes();return 0;}
    test("unfresh_sample_must_not_open",[]{Fixture f;f.baseline();f.s.fresh=false;f.s.grams=131;f.s.now_ms+=100;f.s.sample_at_ms=f.s.now_ms;f.c.launchPulse(f.s);f.close();CHECK(f.out.opens==0&&f.c.state()==db::State::FAULT);});
    test("decreasing_sample_timestamps_are_not_four_independent_samples",[]{Fixture f;f.measure();const auto start=f.s.now_ms;for(unsigned n=0;n<4;++n){f.s.now_ms+=100;f.s.sample_at_ms=start+100-n*100;f.s.grams=130;f.c.tick(f.s);}f.close();CHECK(f.c.state()==db::State::FAULT);});
    test("journal_callback_cannot_promote_fault_to_complete",[]{Fixture f;f.journal.abort_complete=true;f.finish(35);CHECK(f.c.state()==db::State::FAULT&&f.journal.pending);});
    test("journal_callback_cannot_resurrect_start",[]{Fixture f;f.journal.abort_start=true;CHECK(f.c.start(1,35,f.s)!=db::Reason::NONE);f.close();CHECK(f.c.state()==db::State::FAULT);CHECK(f.c.start(1,35,f.s)==db::Reason::DUPLICATE);});
    test("late_open_callback_is_compensated",[]{Fixture f;f.baseline();f.out.abort_on_open=true;f.c.launchPulse(f.s);CHECK(!f.out.opened);f.close();CHECK(f.c.state()==db::State::FAULT&&!f.out.attached);});
    test("calibration_change_between_arm_and_start_is_rejected",[]{Fixture f;f.s.calibration_id=124;CHECK(f.c.start(1,35,f.s)!=db::Reason::NONE);f.close();CHECK(!f.journal.pending&&f.out.opens==0);});
    test("same_stamp_conflicting_weight_is_invalid",[]{Fixture f;f.baseline();f.s.grams=131;f.c.launchPulse(f.s);f.close();CHECK(f.out.opens==0&&f.c.state()==db::State::FAULT);});
    test("host_clock_regression_is_invalid",[]{Fixture f;f.baseline();f.s.now_ms-=100;f.s.sample_at_ms=f.s.now_ms;f.c.launchPulse(f.s);f.close();CHECK(f.out.opens==0&&f.c.state()==db::State::FAULT);});
    test("late_callbacks_cannot_complete_after_fault",[]{Fixture f;f.baseline();f.c.abort(f.s.now_ms);for(unsigned n=0;n<30;++n){f.tick(130);f.c.launchPulse(f.s);}CHECK(f.c.state()==db::State::FAULT&&f.out.opens==0);});
    test("journal_failure_and_reboot_pending_require_inspection",[]{Fixture f;f.journal.fail_clear=true;f.finish(35);CHECK(f.c.state()==db::State::FAULT);Output o;Journal j;db::Controller c(o,j);c.boot(true,true,1);CHECK(c.arm(f.s)==db::Reason::INSPECTION_REQUIRED&&o.opens==0);});
    test("updated_profile_target_and_accepted_final_remain_valid",[]{for(float delta:{35.0f,36.0f,40.0f}){Fixture f;f.finish(delta);CHECK(f.c.state()==db::State::COMPLETE&&!f.out.attached);}});
    test("invalid_weight_calibration_timeout_disconnect_fail_closed",[]{for(unsigned fault=0;fault<7;++fault){Fixture f;f.baseline();f.c.launchPulse(f.s);if(fault==0)f.s.grams=std::numeric_limits<float>::quiet_NaN();if(fault==1)f.s.grams=std::numeric_limits<float>::infinity();if(fault==2)f.s.grams=-1;if(fault==3)f.s.calibrated=false;if(fault==4)f.s.calibration_id++;if(fault==5)f.s.now_ms+=60000;if(fault==6)f.c.abort(f.s.now_ms);f.c.tick(f.s);f.close();CHECK(f.c.state()==db::State::FAULT&&!f.out.attached);}});
    std::cout<<"HARDENING_SAFETY_PASS cases="<<cases<<" checks="<<checks<<" source=SIMULATED physical_pass=false\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
