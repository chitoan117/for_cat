#pragma once
#include "telemetry.h"
namespace forcat {
// Process-lifetime observation fencing, not a persisted MCU request ledger.
// UART reconnect/startup is the only authority for a new boot nonce; retained
// sensor history does not become live just because the tty was reopened.
class ManualSessionFence {
    bool connected_=false,remembered_=false,allow_boot_=false,need_progress_=false,fault_seen_=false,have_host_=false;
    uint32_t boot_=0,uptime_=0,session_high_=0,observed_session_=0,sequence_=0,arms_=0,pulses_=0;
    uint64_t host_=0;
    std::string signature_;
    std::set<uint32_t> retired_;
 public:
    void connection(){connected_=true;allow_boot_=true;need_progress_=remembered_;}
    void disconnect(){connected_=false;need_progress_=true;}
    void startup(){allow_boot_=true;need_progress_=remembered_;}
    bool accept(const Telemetry& t,uint64_t now){
        if(!connected_)return false;
        auto m=field(t.normalized.get(),"manual_station");
        const auto boot=counter(m,"boot_nonce"),session=counter(m,"session"),seq=counter(m,"last_sequence");
        const auto arms=counter(m,"servo_arms"),pulses=counter(m,"pump_pulses");
        const bool fault=boolean(m,"fault_latched");
        const auto signature=encode(t.normalized.get());
        if(have_host_ && now<host_)return false;
        const bool new_boot=!remembered_ || boot!=boot_;
        if(new_boot){
            if(!allow_boot_ || retired_.count(boot) || retired_.size()>=64)return false;
            if(remembered_)retired_.insert(boot_);
        }else{
            const auto delta=static_cast<uint32_t>(t.uptime-uptime_);
            if(delta>0x7fffffffu || (need_progress_ && delta==0) ||
               (delta==0 && signature!=signature_) || arms<arms_ || pulses<pulses_)return false;
            if(session && (session<session_high_ || (!observed_session_ && session==session_high_)))return false;
            if((!session || session==session_high_) && seq<sequence_)return false;
            if(fault_seen_ && !fault)throw UnsafeTelemetry("MANUAL_FAULT_RESURRECTED_WITHOUT_NEW_BOOT");
        }
        if(new_boot){session_high_=0;sequence_=0;fault_seen_=false;}
        session_high_=std::max(session_high_,session);observed_session_=session;sequence_=seq;
        boot_=boot;uptime_=t.uptime;arms_=arms;pulses_=pulses;fault_seen_=fault_seen_||fault;
        remembered_=true;allow_boot_=false;need_progress_=false;host_=now;have_host_=true;signature_=signature;
        return true;
    }
};
} // namespace forcat
