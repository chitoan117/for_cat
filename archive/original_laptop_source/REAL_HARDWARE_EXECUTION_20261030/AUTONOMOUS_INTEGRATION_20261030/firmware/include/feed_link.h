#pragma once
// Closed-loop application protocol V1 in the existing UARTv1 CRC envelope.
// NOT the ASCII diag_manual_station protocol; no Arduino/Serial dependency here.
#include <cmath>
#include <cstdint>
#include <cstring>
#include "uart_v1.h"
#include "m4/dispense_bench.h"

namespace feed_link {
enum Op:uint8_t {HELLO=64,CONFIGURE=65,ARM=66,FEED=67,HEARTBEAT=68,ABORT=69,QUERY=70,DOG=71,RESULT=72,CAPABILITIES=73,INSPECT=74};
enum Error:uint8_t {ACTUATION_DISABLED=100,BAD_SCHEMA=101,SESSION=102,REPLAY=103,CLOSE_UNVERIFIED=104,
                   LINK_TIMEOUT=105,BAD_CONFIG=106,NO_DISPENSE_ACTION=107,NO_CLOSURE_PROVIDER=108};
enum Flag:uint8_t {FINAL=1,SETTLED=2,PWM_OFF=4,CLOSED=8,JOURNAL_OK=16,WEIGHT_VALID=32,CAL_VALID=64};
inline uint32_t get32(const uint8_t* p){return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
inline void put32(uint8_t* p,uint32_t n){for(unsigned i=0;i<4;++i)p[i]=static_cast<uint8_t>(n>>(i*8));}
inline uint16_t get16(const uint8_t* p){return static_cast<uint16_t>(p[0]|uint16_t(p[1])<<8);}
inline void put16(uint8_t* p,uint16_t n){p[0]=static_cast<uint8_t>(n);p[1]=static_cast<uint8_t>(n>>8);}
inline float getFloat(const uint8_t* p){auto n=get32(p);float f=0;std::memcpy(&f,&n,4);return f;}
inline void putFloat(uint8_t* p,float f){uint32_t n=0;std::memcpy(&n,&f,4);put32(p,n);}
struct Closure {bool available=false,closed=false;uint32_t sampled_at_ms=0;};
class Sink {public:virtual ~Sink()=default;virtual void emit(uint32_t id,uint8_t op,const uint8_t* bytes,uint16_t n)=0;};
class Warning {public:virtual ~Warning()=default;virtual bool pulse(uint32_t now)=0;};
class TrackingOutput:public m4::servo_bench::Output {
    m4::servo_bench::Output& io_;
 public:
    uint32_t now=0,last_open=0;uint16_t open_us=0;bool attached=false,opened=false;
    explicit TrackingOutput(m4::servo_bench::Output& io):io_(io){}
    bool start(uint16_t us)override{const bool ok=io_.start(us);if(ok)attached=true;return ok;}
    bool write(uint16_t us)override{const bool ok=io_.write(us);if(ok && us==open_us){opened=true;last_open=now;}return ok;}
    bool off()override{const bool ok=io_.off();if(ok)attached=false;return ok;}
};
class Endpoint {
    TrackingOutput output_;
    m4::dispense_bench::Journal& journal_;
    m4::dispense_bench::Controller control_;
    Sink& sink_;Warning& warning_;
    bool enabled_=false,inspection_=true,reported_=false,have_clock_=false;
    uint32_t boot_=0,link_=0,generation_=0,seq_=0,last_rx_=0,last_now_=0,origin_=0;
    uint16_t transaction_cal_=0;
    uint8_t override_reason_=0;
    m4::dispense_bench::Observation obs_{};Closure closure_{};
    uint8_t terminal_[35]{};bool cached_=false;
    void prefix(uint8_t* p){p[0]=1;put32(p+1,boot_);put32(p+5,link_);put32(p+9,seq_);}
    bool closed()const{return closure_.available && closure_.closed &&
        static_cast<uint32_t>(obs_.now_ms-closure_.sampled_at_ms)<=1500 &&
        (!output_.opened || static_cast<uint32_t>(closure_.sampled_at_ms-output_.last_open)<=0x7fffffffu);}
    void ack(uint32_t id,uint8_t op,uint8_t error=0){uint8_t p[15]{};prefix(p);p[13]=op;p[14]=error;sink_.emit(id,error?uart_v1::NACK:uart_v1::ACK,p,sizeof(p));}
    void capabilities(uint32_t id){uint8_t p[23]{};prefix(p);
        p[13]=static_cast<uint8_t>((enabled_?1:0)|(!inspection_?2:0)|(closure_.available?4:0)|(control_.configured()?8:0));
        put32(p+14,lastId());p[18]=static_cast<uint8_t>(inspection_||control_.locked());p[19]=static_cast<uint8_t>(control_.state());
        p[20]=static_cast<uint8_t>(control_.reason());put16(p+21,obs_.calibration_id);sink_.emit(id,CAPABILITIES,p,sizeof(p));}
    void result(bool final){
        if(!control_.id())return;
        uint8_t p[35]{};prefix(p);if(!link_)put32(p+5,origin_);put32(p+13,origin_);
        const bool complete=control_.state()==m4::dispense_bench::State::COMPLETE;
        const bool good_cal=obs_.calibrated && obs_.calibration_id && obs_.calibration_id==transaction_cal_;
        const bool measurement=complete && good_cal && obs_.healthy && std::isfinite(control_.dispensed());
        const bool latest=control_.baselineValid() && good_cal && obs_.healthy && std::isfinite(obs_.grams) &&
            static_cast<uint32_t>(obs_.now_ms-obs_.sample_at_ms)<=1500;
        const bool success=complete && !inspection_ && !override_reason_ && closed() && !output_.attached && control_.pulses()>0;
        p[17]=static_cast<uint8_t>(final?(success?1:3):0);p[18]=static_cast<uint8_t>(control_.state());
        p[19]=override_reason_?override_reason_:static_cast<uint8_t>(control_.reason());
        p[20]=static_cast<uint8_t>((final?FINAL:0)|(complete?SETTLED:0)|(!output_.attached?PWM_OFF:0)|(closed()?CLOSED:0)|
             (complete && !inspection_ && !control_.locked()?JOURNAL_OK:0)|(measurement?WEIGHT_VALID:0)|(good_cal?CAL_VALID:0));
        put16(p+21,transaction_cal_);putFloat(p+23,35.f);putFloat(p+27,measurement?control_.dispensed():0.f);
        // Last observation is separate from a settled/qualified final measurement.
        putFloat(p+31,latest?obs_.grams-control_.baseline():NAN);
        if(final){std::memcpy(terminal_,p,sizeof(p));cached_=true;reported_=true;}
        sink_.emit(control_.id(),RESULT,p,sizeof(p));
    }
    void abort(uint8_t reason){override_reason_=reason;control_.abort(obs_.now_ms);inspection_=true;}
 public:
    Endpoint(m4::servo_bench::Output& out,m4::dispense_bench::Journal& journal,Sink& sink,Warning& warning,bool enabled=false)
        :output_(out),journal_(journal),control_(output_,journal),sink_(sink),warning_(warning),enabled_(enabled){}
    uint32_t highwater_=0;
    uint32_t lastId()const{return highwater_;}
    void boot(uint32_t nonce,bool initialized,bool pending,uint32_t last,uint32_t now){
        boot_=nonce?nonce:1;link_=generation_=seq_=origin_=0;highwater_=last;last_rx_=last_now_=now;
        inspection_=!initialized||pending;cached_=reported_=have_clock_=false;override_reason_=0;
        output_.now=now;output_.opened=false;control_.boot(initialized,pending,last);
    }
    void tick(m4::dispense_bench::Observation observation,Closure closure,bool allow_pulse=true){
        obs_=observation;closure_=closure;output_.now=obs_.now_ms;
        if(have_clock_ && static_cast<uint32_t>(obs_.now_ms-last_now_)>0x7fffffffu)abort(SESSION);
        have_clock_=true;last_now_=obs_.now_ms;
        if(link_ && static_cast<uint32_t>(obs_.now_ms-last_rx_)>=1500){
            if(control_.active() || control_.state()==m4::dispense_bench::State::ARMED)abort(LINK_TIMEOUT);
            link_=0;
        }
        const auto event=control_.tick(obs_);
        if(allow_pulse && event==m4::dispense_bench::Event::NONE && control_.pulsePending())control_.launchPulse(obs_);
        const auto state=control_.state();
        if(!reported_ && control_.id() && (state==m4::dispense_bench::State::COMPLETE || state==m4::dispense_bench::State::FAULT)){
            if(state==m4::dispense_bench::State::COMPLETE && (!closed() || output_.attached || !control_.pulses())){
                inspection_=true;override_reason_=!control_.pulses()?NO_DISPENSE_ACTION:CLOSE_UNVERIFIED;
                if(!journal_.write(true,control_.id()))override_reason_=static_cast<uint8_t>(m4::dispense_bench::Reason::PERSISTENCE_FAULT);
            }
            if(state==m4::dispense_bench::State::FAULT)inspection_=true;
            result(true);
        }
    }
    void receive(uint32_t id,uint8_t op,const uint8_t* p,uint16_t n){
        if(op==HELLO){
            if(n!=5 || p[0]!=1 || !get32(p+1) || id!=get32(p+1)){ack(id,op,BAD_SCHEMA);return;}
            if(control_.active() || control_.state()==m4::dispense_bench::State::ARMED)abort(SESSION);
            if(generation_==UINT32_MAX){ack(id,op,SESSION);return;}
            link_=++generation_;seq_=0;last_rx_=obs_.now_ms;capabilities(id);return;
        }
        if(n<13 || p[0]!=1){ack(id,op,BAD_SCHEMA);return;}
        const auto seq=get32(p+9);
        if(!link_ || get32(p+1)!=boot_ || get32(p+5)!=link_){if(control_.active())abort(SESSION);ack(id,op,SESSION);return;}
        if(!seq || seq<=seq_){if(control_.active())abort(REPLAY);ack(id,op,REPLAY);return;}
        seq_=seq;last_rx_=obs_.now_ms;
        if(op==HEARTBEAT && n==13){ack(id,op);return;}
        if(op==QUERY && n==13){
            if(id==control_.id() && cached_){prefix(terminal_);sink_.emit(id,RESULT,terminal_,sizeof(terminal_));}
            else if(id==control_.id() && control_.active())result(false);
            else capabilities(id);
            return;
        }
        if((op==ABORT || op==DOG) && n==13){
            if(control_.active() || control_.state()==m4::dispense_bench::State::ARMED)abort(static_cast<uint8_t>(m4::dispense_bench::Reason::ABORTED));
            if(op==DOG && enabled_)warning_.pulse(obs_.now_ms);
            ack(id,op);return;
        }
        if(!enabled_){ack(id,op,ACTUATION_DISABLED);return;}
        if(!closure_.available){ack(id,op,NO_CLOSURE_PROVIDER);return;}
        if(op==INSPECT && n==13){
            if(!closed() || !control_.inspect(obs_.now_ms)){ack(id,op,CLOSE_UNVERIFIED);return;}
            inspection_=false;ack(id,op);return;
        }
        if(inspection_){ack(id,op,static_cast<uint8_t>(m4::dispense_bench::Reason::INSPECTION_REQUIRED));return;}
        if(op==CONFIGURE && n==48){
            m4::dispense_bench::Settings s;
            s.safe_min_us=get16(p+13);s.safe_max_us=get16(p+15);s.close_us=get16(p+17);s.open_us=get16(p+19);
            s.coarse_ms=get16(p+21);s.fine_ms=get16(p+23);s.settle_ms=get16(p+25);s.max_pulses=p[27];
            s.fine_threshold_g=getFloat(p+28);s.tolerance_g=getFloat(p+32);s.stable_range_g=getFloat(p+36);
            s.max_target_g=getFloat(p+40);s.max_dispensed_g=getFloat(p+44);
            if(!s.valid() || s.safe_max_us-s.safe_min_us>100 || s.tolerance_g!=5.f || s.max_target_g!=35.f || s.max_dispensed_g!=40.f || !control_.configure(s)){
                ack(id,op,BAD_CONFIG);return;}
            output_.open_us=s.open_us;ack(id,op);return;
        }
        if(op==ARM && n==13){
            if(!closed()){ack(id,op,CLOSE_UNVERIFIED);return;}
            if(control_.state()==m4::dispense_bench::State::COMPLETE)control_.disarm(obs_.now_ms);
            transaction_cal_=obs_.calibration_id;
            ack(id,op,static_cast<uint8_t>(control_.arm(obs_)));return;
        }
        if(op==FEED && n==13){
            if(!id || id>0xffffffu){ack(id,op,static_cast<uint8_t>(m4::dispense_bench::Reason::INVALID_ID));return;}
            if(id<=highwater_){
                if(id==control_.id()){ack(id,op);if(cached_){prefix(terminal_);sink_.emit(id,RESULT,terminal_,sizeof(terminal_));}else result(false);}
                else ack(id,op,static_cast<uint8_t>(m4::dispense_bench::Reason::DUPLICATE));
                return;
            }
            const auto code=control_.start(id,35.f,obs_);
            if(code==m4::dispense_bench::Reason::NONE){highwater_=id;origin_=link_;cached_=reported_=false;override_reason_=0;output_.opened=false;}
            else if(code==m4::dispense_bench::Reason::PERSISTENCE_FAULT)highwater_=id>highwater_?id:highwater_;
            ack(id,op,static_cast<uint8_t>(code));if(code==m4::dispense_bench::Reason::NONE)result(false);return;
        }
        ack(id,op,BAD_SCHEMA);
    }
    m4::dispense_bench::State state()const{return control_.state();}
    bool active()const{return control_.active();}
    void transportFault(){if(control_.active() || control_.state()==m4::dispense_bench::State::ARMED)abort(LINK_TIMEOUT);link_=0;inspection_=true;}
};
} // namespace feed_link
