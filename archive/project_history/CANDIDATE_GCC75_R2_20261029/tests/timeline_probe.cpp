// Real parser/framer/session, synthetic clock/file only. No serial API linked.
#include "telemetry.h"
#include "diagnostic_session.h"
#include <fstream>
#include <iostream>
int main(int argc,char** argv){try{
    if(argc!=2)return 2;
    std::ifstream input(argv[1]);std::string line;std::getline(input,line);
    if(!input||line.empty())return 2;
    forcat::LineFramer framer;forcat::Telemetry parsed;
    line+='\n';
    for(size_t at=0;at<line.size();at+=7){
        framer.feed(line.data()+at,std::min(size_t(7),line.size()-at),[&](const std::string& text){parsed=forcat::parseTelemetry(text);});
    }
    if(!parsed.normalized)return 2;
    forcat::DiagnosticSession session;session.connection();bool connected=true;
    auto emit=[&](const char* name,uint64_t now,uint64_t last_rx){
        auto v=forcat::own(json_object_new_object());forcat::put(v.get(),"case",name);
        forcat::put(v.get(),"health",session.health(now,3000));forcat::put(v.get(),"serial_connected",connected);
        forcat::integer(v.get(),"at_ms",static_cast<int64_t>(now));forcat::integer(v.get(),"last_rx_ms",static_cast<int64_t>(last_rx));
        forcat::put(v.get(),"source","SIMULATED");forcat::put(v.get(),"physical_pass",false);
        json_object_object_add(v.get(),"telemetry",json_object_get(parsed.normalized.get()));
        std::cout<<forcat::encode(v.get())<<'\n';
    };
    session.accept(parsed.uptime,100000);emit("initial",100000,100000);
    session.accept(parsed.uptime,103500);emit("duplicate_frozen",103500,103500);
    session.disconnect();connected=false;emit("unplug",103600,103500);
    session.connection();connected=true;emit("reconnect_waiting",103700,103500);
    session.accept(parsed.uptime+1,103800);emit("progress_resumes",103800,103800);
    session.invalid(true);session.accept(parsed.uptime+2,103900);emit("unsafe_latched",103900,103900);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
