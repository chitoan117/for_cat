#pragma once
#include <cstdint>
#include <string>
namespace forcat {
// Shared deterministic freshness/reboot state used by live candidate and replay.
// Cache history is not usable after invalid data, startup, disconnect or staleness.
class DiagnosticSession {
 bool connected_=false,seen_=false,bad_=false,unsafe_=false;
  uint32_t uptime_=0;uint64_t rx_=0,progress_=0,reboots_=0;
  bool last_accepted_=false,have_host_=false;
  uint64_t last_host_=0;
 public:
  void connection(){connected_=true;seen_=false;bad_=false;have_host_=false;last_accepted_=false;}
  void disconnect(){connected_=false;seen_=false;last_accepted_=false;}
  void startup(){if(seen_)++reboots_;seen_=false;bad_=false;have_host_=false;last_accepted_=false;}
 void invalid(bool unsafe=false){bad_=true;unsafe_=unsafe_||unsafe;}
  bool accept(uint32_t uptime,uint64_t now){
    last_accepted_=false;
    if(unsafe_||!connected_)return false;
    if((have_host_&&now<last_host_)||(seen_&&static_cast<uint32_t>(uptime-uptime_)>0x7fffffffu)){
      bad_=true;return false;
    }
    if(!seen_ || uptime!=uptime_)progress_=now;
    seen_=true;uptime_=uptime;rx_=now;bad_=false;last_host_=now;have_host_=true;last_accepted_=true;
    return false; // restart authority is explicit startup/reconnect, not a backwards packet
 }
 std::string health(uint64_t now,uint64_t stale_ms)const{
   if(unsafe_ || bad_)return "ESP32_BAD_TELEMETRY";
   if(!connected_)return "ESP32_DISCONNECTED";
   if(!seen_ || now<rx_ || now<progress_ || now-rx_>stale_ms || now-progress_>stale_ms)return "ESP32_STALE";
   return "ESP32_CONNECTED";
 }
  uint64_t reboots()const{return reboots_;}
  bool lastAccepted()const{return last_accepted_;}
};
}
