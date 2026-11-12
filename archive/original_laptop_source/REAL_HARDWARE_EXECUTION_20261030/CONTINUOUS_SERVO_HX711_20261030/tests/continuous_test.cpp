#include "continuous_dispense.h"
#include "continuous_hx_adapter.h"
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace forcat_continuous;
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("check="+std::to_string(checks));}
struct Output:m4::servo_bench::Output {
    bool attached=false,fail_start=false,fail_write=false,fail_off=false;uint16_t pulse=0;
    unsigned opens=0,closes=0,neutral_writes=0;std::function<void()> callback;bool callback_on_start=false;
    bool start(uint16_t value)override{if(fail_start)return false;if(callback_on_start&&callback){auto f=callback;callback=nullptr;f();}attached=true;pulse=value;return true;}
    bool write(uint16_t value)override{
        if(fail_write||!attached)return false;
        if(value==1530)++opens;else if(value==1470)++closes;else if(value==1500)++neutral_writes;
        if(callback){auto f=callback;callback=nullptr;f();}pulse=value;return true;
    }
    bool off()override{if(fail_off)return false;attached=false;pulse=0;return true;}
};
struct Store:Journal {
    bool pending=false,fail=false;uint32_t id=0;std::function<void()> on_start,on_clear;
    bool write(bool p,uint32_t n)override{
        if(fail)return false;
        if(p&&on_start){auto f=on_start;on_start=nullptr;f();}
        if(!p&&on_clear){auto f=on_clear;on_clear=nullptr;f();}
        pending=p;id=n;return true;
    }
};
Settings settings(){
    Settings s;s.pulses={1450,1550,1500,1495,1505,1530,1470,true,true,true};
    s.opening_ms=300;s.closing_ms=400;s.neutral_hold_ms=100;s.settle_ms=500;s.stable_span_ms=300;
    s.baseline_timeout_ms=3000;s.settle_timeout_ms=3000;s.no_progress_ms=2000;s.total_timeout_ms=10000;
    s.stable_range_g=.2f;s.travel_timing_verified=true;return s;
}
struct Rig {
    Output output;Store store;Driver driver{output};Controller controller{driver,store};
    Sample s{1000,1000,7,true,true,true,100};Position p{};Mode mode=Mode::Supervised;
    Rig(){controller.boot(true,false,0);}
    void configure(Settings cfg=settings()){check(controller.configure(cfg));}
    void start(Mode m=Mode::Supervised){mode=m;if(m==Mode::Automatic)p={true,true,true,true,false,s.now_ms};
        check(controller.arm(s,p,m,true)==Reason::None);check(!output.attached && output.opens==0 && output.closes==0);
        check(controller.start(1,s)==Reason::None);}
    void tick(float grams=100,bool heartbeat=true){
        s.now_ms+=100;s.sample_at_ms=s.now_ms;s.grams=grams;
        if(p.available)p.observed_ms=s.now_ms;
        if(heartbeat)controller.heartbeat(s.now_ms);
        controller.tick(s,p);
    }
    void baseline(){for(unsigned i=0;i<4;++i)tick();check(controller.state()==State::Opening);check(output.pulse==1530);}
    void untilMeasurement(float final_mass,bool feedback=false){
        for(unsigned i=0;i<25 && controller.state()!=State::AwaitingOwner && controller.state()!=State::Complete && controller.state()!=State::Fault;++i){
            if(feedback){p.closed=true;p.opened=false;}
            tick(100+final_mass);
        }
    }
};
struct NullPins:m4::PinIO {
    bool inputAllowed(int)const override{return true;}bool outputAllowed(int)const override{return true;}
    void input(int,m4::Pull)override{}void output(int)override{}bool read(int)override{return true;}
    void write(int,bool)override{}void pauseMicros(uint32_t)override{}void enterCritical()override{}void exitCritical()override{}
};
int main(int argc,char**argv){const std::string test=argc==2?argv[1]:"";try{
    if(argc!=2)return 2;
    if(test=="config_and_arm_no_motion"){
        Rig r;check(!r.controller.configure(Settings{}));auto bad=settings();bad.pulses.neutral_verified=false;check(!r.controller.configure(bad));
        bad=settings();bad.pulses.close_rotation_us=1540;check(!r.controller.configure(bad));
        bad=settings();bad.closing_lead_g=2;check(!r.controller.configure(bad));
        bad=settings();bad.detach_after_neutral=true;check(!r.controller.configure(bad));
        r.configure();check(r.controller.arm(r.s,r.p,Mode::Supervised,false)==Reason::Approval);r.start();
    }else if(test=="supervised_aim35_actual38_unconfirmed"){
        Rig r;r.configure();r.start();r.baseline();r.tick(110);r.tick(120);r.tick(130);
        check(r.controller.state()==State::WaitingMass && r.output.pulse==1500); // timed OPEN stops, not a position proof
        r.tick(135);check(r.controller.state()==State::Closing && r.output.pulse==1470);
        r.untilMeasurement(38);check(r.controller.state()==State::AwaitingOwner);check(r.controller.actualGrams()==38);
        check(r.controller.inspectionRequired() && r.store.pending);check(r.driver.rotation()==Rotation::Neutral);
    }else if(test=="measured_close_lead_not_lower_band"){
        Rig r;auto cfg=settings();cfg.closing_lead_g=2;cfg.closing_lead_verified=true;r.configure(cfg);r.start();r.baseline();
        r.tick(130);check(r.output.closes==0);r.tick(132);check(r.output.closes==0);
        r.tick(133);check(r.controller.state()==State::Closing && r.controller.closeTriggerGrams()==33);
        r.untilMeasurement(35);check(r.controller.actualGrams()==35 && r.controller.state()==State::AwaitingOwner);
    }else if(test=="persistent30_no_early_success_or_topup"){
        Rig r;r.configure();r.start();r.baseline();for(unsigned i=0;i<30;++i)r.tick(130);
        check(r.controller.state()==State::Fault && r.controller.reason()==Reason::NoProgress);
        check(r.output.opens==1 && r.output.closes==0);
    }else if(test=="automatic_needs_real_feedback_contract"){
        Rig r;r.configure();check(r.controller.arm(r.s,r.p,Mode::Automatic,true)==Reason::Position);
        r.start(Mode::Automatic);r.baseline();r.p.closed=false;r.p.opened=true;r.tick(120);
        check(r.controller.state()==State::WaitingMass);r.tick(135);r.untilMeasurement(38,true);
        check(r.controller.state()==State::Complete && r.controller.actualGrams()==38 && !r.store.pending);
    }else if(test=="automatic_close_timeout_not_closed"){
        Rig r;r.configure();r.start(Mode::Automatic);r.baseline();r.p.closed=false;r.p.opened=true;r.tick(120);r.tick(135);
        r.p.opened=false;r.untilMeasurement(38);check(r.controller.state()==State::Fault && r.controller.reason()==Reason::Position);
        check(r.store.pending);
    }else if(test=="overshoot_all_motion_and_settle_states"){
        for(unsigned phase=0;phase<3;++phase){Rig r;r.configure();r.start();r.baseline();
            if(phase>0)r.tick(135);
            if(phase>1){for(unsigned i=0;i<6;++i)r.tick(138);}
            r.tick(141);check(r.controller.reason()==Reason::Overshoot);for(unsigned i=0;i<6;++i)r.tick(141);
            check(r.controller.state()==State::Fault);check(r.output.opens==1);}
    }else if(test=="calibration_stale_conflict_and_clock_fail"){
        for(unsigned kind=0;kind<4;++kind){Rig r;r.configure();r.start();r.baseline();
            if(kind==0){r.s.generation=8;r.tick(110);}else if(kind==1){r.s.now_ms+=1600;r.controller.heartbeat(r.s.now_ms);r.controller.tick(r.s,r.p);check(r.controller.reason()==Reason::Weight);}
            else if(kind==2){r.s.grams=101;r.controller.tick(r.s,r.p);}else{r.s.now_ms-=100;r.controller.tick(r.s,r.p);}
            check(r.controller.state()!=State::Complete && r.controller.state()!=State::AwaitingOwner);
            check(r.driver.rotation()!=Rotation::OpenDirection);}
    }else if(test=="stop_no_reverse_and_no_deadline_extension"){
        Rig r;auto cfg=settings();cfg.supervised_bounded_fault_close=true;r.configure(cfg);r.start();r.baseline();
        r.controller.stop(r.s.now_ms);check(r.output.closes==0 && r.output.pulse==1500);
        r.controller.stop(r.s.now_ms+50);r.tick();check(r.controller.state()==State::Fault);
    }else if(test=="fault_close_optin_bounded_never_complete"){
        Rig r;auto cfg=settings();cfg.supervised_bounded_fault_close=true;r.configure(cfg);r.start();r.baseline();
        r.s.healthy=false;r.tick();check(r.controller.state()==State::FaultClosing && r.output.pulse==1470);
        for(unsigned i=0;i<8;++i)r.tick();check(r.controller.state()==State::Fault);check(r.output.closes==1);
    }else if(test=="link_loss_neutral_not_auto_rearm"){
        Rig r;r.configure();r.start();r.baseline();for(unsigned i=0;i<20;++i)r.tick(110,false);
        check(r.controller.state()==State::Fault && r.controller.reason()==Reason::Lease);
        check(r.output.opens==1 && r.controller.inspectionRequired());
    }else if(test=="idempotency_journal_fail_and_pending_reboot"){
        Rig r;r.configure();check(r.controller.arm(r.s,r.p,Mode::Supervised,true)==Reason::None);r.store.fail=true;
        check(r.controller.start(1,r.s)==Reason::Persistence);check(r.controller.highwater()==1 && r.output.opens==0);
        check(r.controller.start(1,r.s)==Reason::Duplicate);
        r.controller.boot(true,true,1);check(!r.controller.configure(settings()));
        check(r.controller.arm(r.s,r.p,Mode::Supervised,true)==Reason::Inspection);
        Rig other;other.configure();other.start();check(other.controller.start(1,other.s)==Reason::Duplicate);
        check(other.store.pending && other.output.opens==0);
    }else if(test=="frozen_samples_not_stable_window"){
        Rig r;r.configure();r.start();
        for(unsigned i=0;i<20;++i){r.s.now_ms+=100;r.controller.heartbeat(r.s.now_ms);r.controller.tick(r.s,r.p);}
        check(r.output.opens==0);check(r.controller.state()!=State::Complete);
    }else if(test=="late_attach_or_open_stop_cannot_resurrect"){
        for(bool during_start:{true,false}){Rig r;r.configure();r.start();r.output.callback_on_start=during_start;
            r.output.callback=[&]{r.controller.stop(r.s.now_ms);};
            for(unsigned i=0;i<4;++i)r.tick();
            check(r.controller.state()==State::FaultNeutral || r.controller.state()==State::Fault);
            check(r.driver.rotation()!=Rotation::OpenDirection);if(during_start)check(r.output.opens==0);}
    }else if(test=="late_journal_clear_stop_preserves_pending"){
        Rig r;r.configure();r.start(Mode::Automatic);r.baseline();r.p.closed=false;r.p.opened=true;r.tick(120);r.tick(135);
        r.store.on_clear=[&]{r.controller.stop(r.s.now_ms);};r.untilMeasurement(38,true);
        check(r.controller.state()==State::Fault && r.store.pending && r.controller.inspectionRequired());
    }else if(test=="raw_pwm_failure_no_false_success"){
        Rig r;r.configure();r.start();r.output.fail_start=true;for(unsigned i=0;i<4;++i)r.tick();
        check(r.controller.reason()==Reason::Output);check(r.controller.state()==State::Fault || r.controller.state()==State::FaultNeutral);
    }else if(test=="hx_adapter_uses_passed_reading_no_display_or_refit"){
        NullPins pins;m4::Hx711 hx(pins);hx.calibration={true,true,-600000,1./-1064.4473};
        hx.grams={true,138,1000,true};hx.display_grams={true,35,1000,true};hx.status={m4::Health::HEALTHY,m4::Reason::NONE};
        HxAdapter adapter;auto a=adapter.read(hx,1000);check(a.grams==138 && a.generation && a.fresh);
        hx.calibration.tare_counts+=.001;auto b=adapter.read(hx,1001);check(b.generation!=a.generation);
        check(hx.grams.value==138 && hx.display_grams.value==35);
    }else if(test=="below30_measured_fault_not_reopened"){
        Rig r;r.configure();r.start();r.baseline();r.tick(135);r.untilMeasurement(29);
        check(r.controller.state()==State::Fault && r.controller.reason()==Reason::UnderTarget);
        check(r.controller.actualGrams()==29 && r.output.opens==1);
    }else if(test=="inclusive_band_and_no_epsilon_widening"){
        for(float final_mass:{30.f,40.f}){Rig r;r.configure();r.start();r.baseline();r.tick(135);r.untilMeasurement(final_mass);
            check(r.controller.state()==State::AwaitingOwner && r.controller.actualGrams()==final_mass);}
        Rig high;high.configure();high.start();high.baseline();high.tick(std::nextafter(140.f,INFINITY));
        check(high.controller.reason()==Reason::Overshoot);
        // Apply nextafter at the actual gross sensor reading. Adding100 to a
        // nextafter(30) delta would round back to130 before the controller sees it.
        Rig low;low.configure();low.start();low.baseline();low.tick(135);low.untilMeasurement(std::nextafter(130.f,0.f)-100.f);
        check(low.controller.state()==State::Fault && low.controller.reason()==Reason::UnderTarget);
    }else if(test=="expired_arm_lease_and_reentrant_start_journal"){
        Rig r;r.configure();check(r.controller.arm(r.s,r.p,Mode::Supervised,true)==Reason::None);
        r.s.now_ms+=1600;r.s.sample_at_ms=r.s.now_ms;
        check(r.controller.start(1,r.s)==Reason::Lease);check(r.output.opens==0 && r.store.id==0);
        Rig stop;stop.configure();check(stop.controller.arm(stop.s,stop.p,Mode::Supervised,true)==Reason::None);
        stop.store.on_start=[&]{stop.controller.stop(stop.s.now_ms);};
        check(stop.controller.start(1,stop.s)==Reason::Stopped);check(stop.store.pending && stop.controller.highwater()==1);
        check(stop.output.opens==0 && stop.controller.state()!=State::Baseline);
    }else if(test=="closed_feedback_loss_after_neutral_blocks_complete"){
        Rig r;r.configure();r.start(Mode::Automatic);r.baseline();r.p.closed=false;r.p.opened=true;r.tick(120);r.tick(135);
        r.p.closed=true;r.p.opened=false;r.tick(138);check(r.controller.state()==State::NeutralHold);
        r.p.closed=false;r.tick(138);check(r.controller.state()==State::FaultNeutral || r.controller.state()==State::Fault);
        check(r.controller.reason()==Reason::Position && r.store.pending);
    }else return 2;
    std::cout<<"CONTINUOUS_PASS case="<<test<<" checks="<<checks<<" source=MOCK physical_pass=false\n";
}catch(const std::exception& e){std::cerr<<test<<" "<<e.what()<<'\n';return 1;}}
