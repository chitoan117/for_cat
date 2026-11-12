// Portable file-only executable: actual patched parser/framer/session/CLI.
#include "telemetry.h"
#include "diagnostic_session.h"
#include "manual_session.h"
#include "feed_policy.h"
#include "decision_logic.h"
#include "approach_fusion.h"
#include <fstream>
#include <iostream>
#include <iterator>
using namespace forcat;
#include "bridge_options.h"
std::string load(const char* path){std::ifstream f(path);if(!f)throw std::invalid_argument("fixture missing");return std::string(std::istreambuf_iterator<char>(f),{});}
int main(int argc,char** argv){try{
    if(argc<2)return 2;
    const std::string mode=argv[1];
    if(mode=="options"){
        const auto o=options(argc-1,argv+1);
        std::cout<<"{\"mode\":\"PLAN_ONLY\",\"explicit_manual\":"<<(o.firmware_policy==FirmwarePolicy::MANUAL_STATION_READ_ONLY?"true":"false")
          <<",\"would_open_serial\":"<<(o.live_serial?"true":"false")<<",\"serial_tx_enabled\":false,\"actuator_execution\":false}\n";
        return 0;
    }
    if(mode=="parse" && argc==4){
        const std::string profile=argv[3];
        const auto policy=profile=="manual"?FirmwarePolicy::MANUAL_STATION_READ_ONLY:profile=="legacy"?FirmwarePolicy::LEGACY_CURRENT_HARDWARE:FirmwarePolicy::KIT_QUAD_ONLY;
        auto t=parseTelemetry(load(argv[2]),policy);
        std::cout<<encode(t.normalized.get())<<'\n';return 0;
    }
    if(mode!="script" || argc!=3)return 2;
    const auto body=load(argv[2]);rejectDuplicateKeys(body);
    auto script=own(json_tokener_parse(body.c_str()));auto steps=field(script.get(),"steps");
    DiagnosticSession diagnostic;ManualSessionFence manual;LineFramer framer;Json latest;
    bool connected=false,unsafe=false;unsigned accepted=0,rejected=0,noise=0;
    for(size_t index=0;index<json_object_array_length(steps);++index){
        auto step=json_object_array_get_idx(steps,index);const auto op=text(step,"op");
        const auto now=counter(step,"host_ms");
        if(op=="CONNECT"){connected=true;diagnostic.connection();manual.connection();latest.reset();framer.clear();}
        else if(op=="DISCONNECT"){connected=false;diagnostic.disconnect();manual.disconnect();latest.reset();framer.clear();}
        else if(op=="STARTUP"){diagnostic.startup();manual.startup();latest.reset();framer.clear();}
        else if(op=="RX" && connected && !unsafe){
            const auto data=text(step,"data");const auto oversized=framer.oversized;
            framer.feed(data.data(),data.size(),[&](const std::string& line){
                if(unsafe)return;
                if(line[0]!='{'){++noise;return;}
                try{
                    auto t=parseTelemetry(line,FirmwarePolicy::MANUAL_STATION_READ_ONLY);
                    if(!manual.accept(t,now))throw std::invalid_argument("manual replay/session");
                    diagnostic.accept(t.uptime,now);
                    if(!diagnostic.lastAccepted())throw std::invalid_argument("diagnostic ordering");
                    latest=t.normalized;++accepted;
                }catch(const UnsafeTelemetry&){unsafe=true;diagnostic.invalid(true);++rejected;}
                 catch(const std::invalid_argument&){diagnostic.invalid();++rejected;}
            });
            if(framer.oversized!=oversized){diagnostic.invalid();++rejected;}
        }else if(op!="TICK" && op!="RX")throw std::invalid_argument("unknown script op");
        const auto health=diagnostic.health(now,3000);
        if(health!="ESP32_CONNECTED")latest.reset();
        auto out=own(json_object_new_object());put(out.get(),"case",text(step,"case"));put(out.get(),"health",health);
        put(out.get(),"source","OFFLINE_FIXTURE_SIMULATION");put(out.get(),"serial_connected",connected);
        put(out.get(),"serial_tx_enabled",false);put(out.get(),"actuator_execution",false);put(out.get(),"physical_pass",false);
        integer(out.get(),"accepted",accepted);integer(out.get(),"rejected",rejected);integer(out.get(),"noise",noise);
        json_object_object_add(out.get(),"telemetry",latest?json_object_get(latest.get()):nullptr);
        std::cout<<encode(out.get())<<'\n';
    }
    return 0;
}catch(const UnsafeTelemetry& e){std::cerr<<"UNSAFE "<<e.what()<<'\n';return 3;}
 catch(const std::exception& e){std::cerr<<"INVALID "<<e.what()<<'\n';return 1;}}
