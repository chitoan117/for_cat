#include "diagnostic_session.h"
#include <iostream>
#include <stdexcept>
unsigned checks=0;
void check(bool yes){++checks;if(!yes)throw std::runtime_error("session failed");}
int main(){try{
 forcat::DiagnosticSession s;check(s.health(1000,3000)=="ESP32_DISCONNECTED");
 s.connection();check(s.health(1000,3000)=="ESP32_STALE");
 s.accept(100,1000);check(s.health(4000,3000)=="ESP32_CONNECTED");check(s.health(4001,3000)=="ESP32_STALE");
 s.accept(100,4000);check(s.health(4001,3000)=="ESP32_STALE"); // heartbeat duplicate cannot refresh progress
 s.accept(200,4100);check(s.health(4100,3000)=="ESP32_CONNECTED");
 s.invalid();check(s.health(4100,3000)=="ESP32_BAD_TELEMETRY");
 s.accept(300,4200);check(s.health(4200,3000)=="ESP32_CONNECTED");
 check(s.accept(10,4300));check(s.reboots()==1);check(s.health(4300,3000)=="ESP32_CONNECTED");
 s.startup();check(s.health(4300,3000)=="ESP32_STALE" && s.reboots()==2);
 s.accept(20,4400);s.disconnect();check(s.health(4400,3000)=="ESP32_DISCONNECTED");
 s.connection();check(s.health(4400,3000)=="ESP32_STALE");
 s.accept(0xfffffff0,4500);check(!s.accept(10,4600)); // millis wrap, not reboot
 s.invalid(true);check(s.health(4600,3000)=="ESP32_BAD_TELEMETRY");
 s.disconnect();s.connection();s.accept(30,4700);check(s.health(4700,3000)=="ESP32_BAD_TELEMETRY");
 std::cout<<"DIAGNOSTIC_SESSION_PASS checks="<<checks<<" deterministic_clock=true physical_pass=false\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
