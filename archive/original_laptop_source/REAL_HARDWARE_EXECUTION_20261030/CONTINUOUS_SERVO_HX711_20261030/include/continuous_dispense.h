#pragma once
// Serialized supervised continuous-servo dose, not a position-servo adapter.
#include <cmath>
#include <cstdint>
#include "continuous_servo.h"
namespace forcat_continuous {
enum class Mode {Supervised,Automatic};
enum class State {Disarmed,Armed,Baseline,Opening,WaitingMass,Closing,NeutralHold,Settling,AwaitingOwner,Complete,FaultClosing,FaultNeutral,Fault};
enum class Reason {None,Config,Approval,Position,Weight,Calibration,Clock,ConflictingSample,Lease,Timeout,NoProgress,Overshoot,UnderTarget,Stopped,Output,Persistence,Inspection,Duplicate,Busy};
inline const char* name(State s){switch(s){
    case State::Disarmed:return "DISARMED";case State::Armed:return "ARMED_NO_MOTION";
    case State::Baseline:return "WAIT_BASELINE";case State::Opening:return "ROTATE_OPEN_DIRECTION";
    case State::WaitingMass:return "NEUTRAL_WAIT_MASS";case State::Closing:return "ROTATE_CLOSE_DIRECTION";
    case State::NeutralHold:return "NEUTRAL_STOP_COMMAND";case State::Settling:return "WAIT_STABLE_MASS";
    case State::AwaitingOwner:return "MEASURED_NEEDS_OWNER_CONFIRMATION";case State::Complete:return "COMPLETE_WITH_POSITION_FEEDBACK";
    case State::FaultClosing:return "FAULT_BOUNDED_CLOSE_UNVERIFIED";case State::FaultNeutral:return "FAULT_NEUTRAL_COMMAND";default:return "FAULT";
}}
struct Sample {uint32_t now_ms=0,sample_at_ms=0,generation=0;bool healthy=false,calibrated=false,fresh=false;float grams=0;};
struct Position {bool available=false,healthy=false,qualified=false,closed=false,opened=false;uint32_t observed_ms=0;};
struct Settings {
    PulseCalibration pulses{};
    uint32_t opening_ms=0,closing_ms=0,neutral_hold_ms=0,settle_ms=0,stable_span_ms=0;
    uint32_t baseline_timeout_ms=0,settle_timeout_ms=0,no_progress_ms=0,total_timeout_ms=0;
    float stable_range_g=0,closing_lead_g=0;
    bool travel_timing_verified=false,closing_lead_verified=false,detach_after_neutral=false,pwm_loss_stop_verified=false;
    bool supervised_bounded_fault_close=false;
    bool valid()const{return pulses.valid() && travel_timing_verified && opening_ms>=20 && opening_ms<=5000 &&
        closing_ms>=20 && closing_ms<=3000 && neutral_hold_ms>=20 && neutral_hold_ms<=500 && settle_ms>=500 && settle_ms<=5000 &&
        stable_span_ms>=100 && stable_span_ms<=1500 && baseline_timeout_ms>=1000 && baseline_timeout_ms<=10000 &&
        settle_timeout_ms>=settle_ms+stable_span_ms && settle_timeout_ms<=10000 && no_progress_ms>=500 && no_progress_ms<=10000 &&
        total_timeout_ms>opening_ms+closing_ms+neutral_hold_ms+settle_ms+stable_span_ms && total_timeout_ms<=60000 &&
        std::isfinite(stable_range_g) && stable_range_g>0 && stable_range_g<=2 &&
        std::isfinite(closing_lead_g) && closing_lead_g>=0 && closing_lead_g<=3 &&
        (closing_lead_g==0 || closing_lead_verified) && (!detach_after_neutral || pwm_loss_stop_verified);}
};
class Journal {public:virtual ~Journal()=default;virtual bool write(bool pending,uint32_t id)=0;};
class Controller {
    Driver& driver_;Journal& journal_;Settings settings_{};Mode mode_=Mode::Supervised;
    State state_=State::Disarmed;Reason reason_=Reason::None;
    bool configured_=false,locked_=true,have_clock_=false,have_sample_=false,baseline_valid_=false,actual_valid_=false;
    bool in_effect_=false,new_sample_=false,left_closed_=false,open_confirmed_=false,close_started_=false;
    uint32_t epoch_=0,last_now_=0,observed_at_=0,generation_=0,phase_at_=0,started_at_=0,lease_at_=0;
    uint32_t opening_at_=0,closing_at_=0,last_progress_=0,highwater_=0,id_=0;
    unsigned arms_=0,window_count_=0;float observed_grams_=0,baseline_=0,actual_=0,latest_=0,last_progress_mass_=0;
    float window_[4]{};uint32_t window_time_[4]{};
    struct Effect {bool& flag;explicit Effect(bool& f):flag(f){flag=true;}~Effect(){flag=false;}};
    template<class F> bool effect(F f){Effect guard(in_effect_);return f();}
    bool terminal()const{return state_==State::Disarmed || state_==State::AwaitingOwner || state_==State::Complete || state_==State::Fault;}
    bool faultState()const{return state_==State::FaultClosing || state_==State::FaultNeutral || state_==State::Fault;}
    void resetWindow(){window_count_=0;}
    bool clock(uint32_t now){
        if(have_clock_ && static_cast<uint32_t>(now-last_now_)>0x7fffffffu)return false;
        have_clock_=true;last_now_=now;return true;
    }
    bool positionUsable(const Sample& s,const Position& p)const{return p.available&&p.healthy&&p.qualified&&
        !(p.closed&&p.opened)&&static_cast<uint32_t>(s.now_ms-p.observed_ms)<=1500;}
    bool closedNow(const Sample& s,const Position& p)const{return positionUsable(s,p)&&p.closed&&close_started_&&
        static_cast<uint32_t>(p.observed_ms-closing_at_)<=0x7fffffffu;}
    Reason sample(const Sample& s,bool require_new){
        new_sample_=false;
        if(!s.calibrated || !s.generation)return Reason::Calibration;
        if(!s.healthy || !std::isfinite(s.grams) || std::fabs(s.grams)>100000 || static_cast<uint32_t>(s.now_ms-s.sample_at_ms)>1500)return Reason::Weight;
        if(have_sample_){
            const auto delta=static_cast<uint32_t>(s.sample_at_ms-observed_at_);
            if(delta>0x7fffffffu || (delta==0 && s.grams!=observed_grams_))return Reason::ConflictingSample;
            if(!s.fresh && (delta || s.grams!=observed_grams_))return Reason::Weight;
            new_sample_=s.fresh && delta!=0;
        }else new_sample_=s.fresh;
        if(require_new && !s.fresh)return Reason::Weight;
        if(s.fresh){have_sample_=true;observed_at_=s.sample_at_ms;observed_grams_=s.grams;}
        return Reason::None;
    }
    bool stable(float& mean){
        if(window_count_<4)return false;
        const unsigned last=(window_count_-1)%4,first=window_count_%4;
        if(static_cast<uint32_t>(window_time_[last]-window_time_[first])<settings_.stable_span_ms)return false;
        float lo=window_[0],hi=lo,total=0;
        for(float v:window_){if(v<lo)lo=v;if(v>hi)hi=v;total+=v;}
        mean=total/4;return hi-lo<=settings_.stable_range_g;
    }
    void add(const Sample& s){if(!new_sample_)return;const auto i=window_count_%4;window_[i]=s.grams;window_time_[i]=s.sample_at_ms;++window_count_;}
    void compensateNeutral(){
        const bool neutral=effect([&]{return driver_.neutral();});
        if(!neutral){reason_=Reason::Output;effect([&]{return driver_.detach();});state_=State::Fault;}
    }
    void neutral(uint32_t now,bool fault){
        ++epoch_;phase_at_=now;state_=fault?State::FaultNeutral:State::NeutralHold;
        if(in_effect_)return; // outer caller compensates the late external effect
        compensateNeutral();
    }
    void fault(Reason why,uint32_t now,bool force_neutral=false){
        if(faultState())return;
        reason_=why;locked_=true;
        if(why!=Reason::UnderTarget && !(why==Reason::Overshoot && state_==State::Settling && actual_valid_))actual_valid_=false;
        const bool can_close=!force_neutral && settings_.supervised_bounded_fault_close && mode_==Mode::Supervised &&
            (state_==State::Opening || state_==State::WaitingMass || state_==State::Closing) &&
            why!=Reason::Clock && why!=Reason::Position && why!=Reason::Output && !in_effect_;
        if(can_close){
            ++epoch_;
            if(state_!=State::Closing){closing_at_=now;close_started_=true;}
            state_=State::FaultClosing;const auto epoch=epoch_;
            const bool ok=effect([&]{return driver_.rotateClose();});
            if(epoch!=epoch_){compensateNeutral();return;}
            if(!ok){reason_=Reason::Output;neutral(now,true);}return;
        }
        neutral(now,true);
    }
    void open(const Sample& s){
        ++epoch_;state_=State::Opening;opening_at_=s.now_ms;last_progress_=s.now_ms;last_progress_mass_=0;resetWindow();
        const auto epoch=epoch_;const bool attached=driver_.attached()?driver_.rotation()==Rotation::Neutral:effect([&]{return driver_.attachNeutral();});
        if(epoch!=epoch_ || state_!=State::Opening){compensateNeutral();return;}
        if(!attached){fault(Reason::Output,s.now_ms,true);return;}
        const bool ok=effect([&]{return driver_.rotateOpen();});
        if(epoch!=epoch_ || state_!=State::Opening){compensateNeutral();return;}
        if(!ok)fault(Reason::Output,s.now_ms,true);
    }
    void close(const Sample& s){
        ++epoch_;state_=State::Closing;closing_at_=s.now_ms;close_started_=true;
        const auto epoch=epoch_;const bool ok=effect([&]{return driver_.rotateClose();});
        if(epoch!=epoch_ || state_!=State::Closing){compensateNeutral();return;}
        if(!ok)fault(Reason::Output,s.now_ms,true);
    }
 public:
    Controller(Driver& driver,Journal& journal):driver_(driver),journal_(journal){}
    void boot(bool initialized,bool pending,uint32_t last_id){
        if(in_effect_)return;
        ++epoch_;state_=State::Disarmed;reason_=Reason::None;configured_=false;locked_=!initialized||pending;
        have_clock_=have_sample_=baseline_valid_=actual_valid_=left_closed_=open_confirmed_=close_started_=false;
        highwater_=last_id;id_=0;arms_=0;resetWindow();
        if(!effect([&]{return driver_.boot();})){state_=State::Fault;reason_=Reason::Output;locked_=true;}
    }
    bool configure(Settings s){
        if(in_effect_||state_!=State::Disarmed||locked_||configured_||arms_||!s.valid())return false;
        if(!driver_.configure(s.pulses))return false;
        settings_=s;configured_=true;return true;
    }
    Reason arm(const Sample& s,const Position& p,Mode mode,bool owner_approved){
        if(in_effect_)return Reason::Busy;
        if(locked_)return Reason::Inspection;
        if(!configured_)return Reason::Config;
        if(!owner_approved)return Reason::Approval;
        if((state_!=State::Disarmed&&state_!=State::Complete)||arms_>=3)return Reason::Busy;
        if(!clock(s.now_ms))return Reason::Clock;
        const auto ok=sample(s,true);if(ok!=Reason::None)return ok;
        if(p.available && !positionUsable(s,p))return Reason::Position;
        if(mode==Mode::Automatic && (!positionUsable(s,p)||!p.closed))return Reason::Position;
        mode_=mode;generation_=s.generation;state_=State::Armed;phase_at_=lease_at_=s.now_ms;++arms_;return Reason::None; // no PWM!
    }
    Reason start(uint32_t id,const Sample& s){
        if(in_effect_)return Reason::Busy;
        if(!id||id>0xffffffu||id<=highwater_)return Reason::Duplicate;
        if(state_!=State::Armed)return Reason::Busy;
        if(!clock(s.now_ms)){fault(Reason::Clock,last_now_,true);return reason_;}
        if(s.now_ms-lease_at_>=1500){fault(Reason::Lease,s.now_ms,true);return reason_;}
        if(s.now_ms-phase_at_>=2000){fault(Reason::Timeout,s.now_ms,true);return reason_;}
        const auto ok=sample(s,true);if(ok!=Reason::None || s.generation!=generation_){fault(ok==Reason::None?Reason::Calibration:ok,s.now_ms,true);return reason_;}
        // Reserve before persistence and before any rotation. Reentrant STOP cannot
        // resurrect the request or recycle its ID, including failed journal writes.
        highwater_=id;id_=id;locked_=true;state_=State::Baseline;started_at_=phase_at_=lease_at_=s.now_ms;
        baseline_valid_=actual_valid_=left_closed_=open_confirmed_=close_started_=false;resetWindow();
        const auto epoch=epoch_;const bool saved=effect([&]{return journal_.write(true,id);});
        if(epoch!=epoch_ || state_!=State::Baseline){compensateNeutral();return reason_;}
        if(!saved){fault(Reason::Persistence,s.now_ms,true);return reason_;}
        return Reason::None;
    }
    void heartbeat(uint32_t now){
        if(in_effect_||terminal()||faultState())return;
        if(!clock(now)){fault(Reason::Clock,last_now_,true);return;}
        lease_at_=now;
    }
    void stop(uint32_t now){
        if(state_==State::FaultNeutral || state_==State::Fault)return; // never extend stop hold/deadline
        reason_=Reason::Stopped;locked_=true;actual_valid_=false;neutral(now,true);
    }
    void tick(const Sample& s,const Position& p){
        if(in_effect_||terminal())return;
        if(!clock(s.now_ms)){
            reason_=Reason::Clock;locked_=true;++epoch_;state_=State::Fault;
            effect([&]{return driver_.neutral();});effect([&]{return driver_.detach();});return;
        }
        if(state_==State::FaultClosing){
            if(s.now_ms-started_at_>=settings_.total_timeout_ms || closedNow(s,p) || s.now_ms-closing_at_>=settings_.closing_ms)neutral(s.now_ms,true);
            return;
        }
        if(state_==State::FaultNeutral){
            if(s.now_ms-phase_at_<settings_.neutral_hold_ms)return;
            const auto epoch=epoch_;
            if(settings_.detach_after_neutral){
                const bool off=effect([&]{return driver_.detach();});
                if(epoch!=epoch_){compensateNeutral();return;}
                if(!off){reason_=Reason::Output;state_=State::Fault;locked_=true;return;}
            }
            state_=State::Fault;return;
        }
        if(s.now_ms-lease_at_>=1500){fault(Reason::Lease,s.now_ms,true);return;}
        if(state_==State::Armed){if(s.now_ms-phase_at_>=2000)fault(Reason::Timeout,s.now_ms,true);return;}
        if(s.now_ms-started_at_>=settings_.total_timeout_ms){fault(Reason::Timeout,s.now_ms,true);return;}
        const auto ok=sample(s,false);
        if(ok!=Reason::None || s.generation!=generation_){fault(ok==Reason::None?Reason::Calibration:ok,s.now_ms);return;}
        if(p.available && !positionUsable(s,p)){fault(Reason::Position,s.now_ms,true);return;}
        if(mode_==Mode::Automatic && !positionUsable(s,p)){fault(Reason::Position,s.now_ms,true);return;}
        if(baseline_valid_){
            latest_=s.grams-baseline_;
            if(latest_>40.f){fault(Reason::Overshoot,s.now_ms);return;}
            if(latest_<-settings_.stable_range_g){fault(Reason::Weight,s.now_ms,true);return;}
        }
        if(state_==State::NeutralHold){
            if(mode_==Mode::Automatic && !closedNow(s,p)){fault(Reason::Position,s.now_ms,true);return;}
            if(s.now_ms-phase_at_<settings_.neutral_hold_ms)return;
            const auto epoch=epoch_;
            if(settings_.detach_after_neutral){
                const bool off=effect([&]{return driver_.detach();});
                if(epoch!=epoch_){compensateNeutral();return;}
                if(!off){reason_=Reason::Output;state_=State::Fault;locked_=true;return;}
            }
            state_=State::Settling;phase_at_=s.now_ms;resetWindow();return;
        }
        if(state_==State::Baseline){
            if(mode_==Mode::Automatic && !p.closed){fault(Reason::Position,s.now_ms,true);return;}
            if(s.now_ms-phase_at_>=settings_.baseline_timeout_ms){fault(Reason::Timeout,s.now_ms,true);return;}
            add(s);float mean=0;if(stable(mean)){baseline_=mean;baseline_valid_=true;latest_=0;open(s);}return;
        }
        if(positionUsable(s,p) && static_cast<uint32_t>(p.observed_ms-opening_at_)<=0x7fffffffu){
            if(!p.closed)left_closed_=true;
            if(p.opened)open_confirmed_=true;
        }
        if(state_==State::Opening || state_==State::WaitingMass){
            if(new_sample_ && latest_>=35.f-settings_.closing_lead_g){close(s);return;}
            if(new_sample_ && latest_-last_progress_mass_>=settings_.stable_range_g/4){last_progress_=s.now_ms;last_progress_mass_=latest_;}
            if(s.now_ms-last_progress_>=settings_.no_progress_ms){fault(Reason::NoProgress,s.now_ms);return;}
            if(state_==State::Opening && (open_confirmed_ || s.now_ms-opening_at_>=settings_.opening_ms)){
                if(mode_==Mode::Automatic && !open_confirmed_){fault(Reason::Position,s.now_ms,true);return;}
                state_=State::WaitingMass;const auto epoch=epoch_;const bool neutral_ok=effect([&]{return driver_.neutral();});
                if(epoch!=epoch_){compensateNeutral();return;}if(!neutral_ok)fault(Reason::Output,s.now_ms,true);
            }return;
        }
        if(state_==State::Closing){
            if(closedNow(s,p)){neutral(s.now_ms,false);return;}
            if(s.now_ms-closing_at_>=settings_.closing_ms){
                if(mode_==Mode::Automatic){fault(Reason::Position,s.now_ms,true);return;}
                neutral(s.now_ms,false);
            }return;
        }
        if(state_==State::Settling){
            if(mode_==Mode::Automatic && !closedNow(s,p)){fault(Reason::Position,s.now_ms,true);return;}
            if(s.now_ms-phase_at_>=settings_.settle_timeout_ms){fault(Reason::Timeout,s.now_ms,true);return;}
            if(s.now_ms-phase_at_<settings_.settle_ms)return;
            add(s);float mean=0;if(!stable(mean))return;
            actual_=mean-baseline_;actual_valid_=true;
            if(actual_<30.f){fault(Reason::UnderTarget,s.now_ms,true);return;}
            if(actual_>40.f){fault(Reason::Overshoot,s.now_ms,true);return;}
            if(mode_==Mode::Supervised){state_=State::AwaitingOwner;locked_=true;return;}
            if(!left_closed_ || !open_confirmed_ || !closedNow(s,p)){fault(Reason::Position,s.now_ms,true);return;}
            const auto epoch=epoch_;const bool saved=effect([&]{return journal_.write(false,id_);});
            if(epoch!=epoch_ || state_!=State::Settling){
                locked_=true;const bool restored=effect([&]{return journal_.write(true,id_);});if(!restored)reason_=Reason::Persistence;compensateNeutral();return;
            }
            if(!saved){fault(Reason::Persistence,s.now_ms,true);return;}
            locked_=false;state_=State::Complete;
        }
    }
    State state()const{return state_;}Reason reason()const{return reason_;}
    uint32_t id()const{return id_;}uint32_t highwater()const{return highwater_;}
    bool inspectionRequired()const{return locked_;}bool baselineValid()const{return baseline_valid_;}
    float closeTriggerGrams()const{return 35.f-settings_.closing_lead_g;}
    float latestGrams()const{return baseline_valid_?latest_:NAN;}
    float actualGrams()const{return actual_valid_?actual_:NAN;}
};
} // namespace forcat_continuous
