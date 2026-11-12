#include "diagnostic_session.h"
#include <iostream>
#include <stdexcept>
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("session check="+std::to_string(checks));}
int main(int argc,char**){try{
    forcat::DiagnosticSession s;s.connection();s.accept(100,1000);s.accept(90,1100);
    if(argc==2){std::cout<<"OUT_OF_ORDER health="<<s.health(1100,3000)<<" physical_pass=false\n";return 0;}
    check(!s.lastAccepted()&&s.health(1100,3000)=="ESP32_BAD_TELEMETRY");
    s.accept(101,1200);check(s.lastAccepted()&&s.health(1200,3000)=="ESP32_CONNECTED");
    s.accept(102,1199);check(!s.lastAccepted());
    s.startup();s.accept(1,1300);check(s.lastAccepted());
    s.accept(1,5000);check(s.health(5000,3000)=="ESP32_STALE");
    s.disconnect();s.connection();check(s.health(5001,3000)=="ESP32_STALE");
    s.accept(0xfffffff0u,5100);check(s.lastAccepted());s.accept(10,5200);check(s.lastAccepted());
    s.invalid(true);s.startup();s.accept(20,5300);check(!s.lastAccepted()&&s.health(5300,3000)=="ESP32_BAD_TELEMETRY");
    std::cout<<"HARDENING_SESSION_PASS checks="<<checks<<" source=SIMULATED physical_pass=false\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
