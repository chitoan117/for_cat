#pragma once
#include <cstdint>
#include <string>
namespace forcat {
// Shared deterministic freshness/reboot state used by live candidate and replay.
// Cache history is not usable after invalid data, startup, disconnect or staleness.
class DiagnosticSession {
 bool connected_=false,seen_=false,bad_=false,unsafe_=false;
 uint32_t uptime_=0;uint64_t rx_=0,progress_=0,reboots_=0;
 public:
 void connection(){connected_=true;seen_=false;bad_=false;}
 void disconnect(){connected_=false;seen_=false;}
 void startup(){if(seen_)++reboots_;seen_=false;bad_=false;}
 void invalid(bool unsafe=false){bad_=true;unsafe_=unsafe_||unsafe;}
 bool accept(uint32_t uptime,uint64_t now){
   if(unsafe_)return false;
   const bool reboot=seen_ && uptime<uptime_ && uptime_-uptime<0x80000000u;
   if(reboot)++reboots_;
   if(!seen_ || uptime!=uptime_)progress_=now;
   seen_=true;uptime_=uptime;rx_=now;bad_=false;return reboot;
 }
 std::string health(uint64_t now,uint64_t stale_ms)const{
   if(unsafe_ || bad_)return "ESP32_BAD_TELEMETRY";
   if(!connected_)return "ESP32_DISCONNECTED";
   if(!seen_ || now<rx_ || now<progress_ || now-rx_>stale_ms || now-progress_>stale_ms)return "ESP32_STALE";
   return "ESP32_CONNECTED";
 }
 uint64_t reboots()const{return reboots_;}
};
}
