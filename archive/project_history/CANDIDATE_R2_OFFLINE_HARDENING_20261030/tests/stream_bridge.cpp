// Scripted transport adapter ONLY. Uses actual parser/framer/session; no serial/DB.
#include "telemetry.h"
#include "diagnostic_session.h"
#include <fstream>
#include <iostream>
#include <iterator>
int main(int argc,char** argv){try{
    if(argc!=2)return 2;
    std::ifstream file(argv[1]);std::string body((std::istreambuf_iterator<char>(file)),{});
    if(body.size()>512*1024)return 2;
    auto script=forcat::own(json_tokener_parse(body.c_str()));
    if(forcat::text(script.get(),"source")!="SIMULATED")return 2;
    auto steps=forcat::field(script.get(),"steps");
    forcat::DiagnosticSession session;forcat::LineFramer framer;forcat::Json latest;
    bool connected=false;uint64_t now=0,last_rx=0;unsigned accepted=0,rejected=0;
    for(size_t index=0;index<json_object_array_length(steps);++index){
        auto step=json_object_array_get_idx(steps,index);now=forcat::counter(step,"host_ms");
        const auto op=forcat::text(step,"op");
        if(op=="CONNECT"){session.connection();connected=true;latest.reset();framer.clear();}
        else if(op=="DISCONNECT"){session.disconnect();connected=false;latest.reset();framer.clear();}
        else if(op=="STARTUP"){session.startup();latest.reset();framer.clear();}
        else if(op=="RESTORE_HISTORY"){latest=forcat::parseTelemetry(forcat::text(step,"data")).normalized;}
        else if(op=="RX"){
            const auto data=forcat::text(step,"data");const auto old=framer.oversized;
            framer.feed(data.data(),data.size(),[&](const std::string& line){
                try{
                    auto parsed=forcat::parseTelemetry(line);session.accept(parsed.uptime,now);
                    if(!session.lastAccepted()){++rejected;return;}
                    latest=parsed.normalized;last_rx=now;++accepted;
                }catch(const forcat::UnsafeTelemetry&){session.invalid(true);++rejected;}
                 catch(const std::invalid_argument&){session.invalid();++rejected;}
            });
            if(old!=framer.oversized){session.invalid();++rejected;}
        }else if(op!="TICK")throw std::invalid_argument("unknown transport operation");
        auto out=forcat::own(json_object_new_object());
        forcat::put(out.get(),"case",forcat::text(step,"case"));forcat::put(out.get(),"health",session.health(now,3000));
        forcat::put(out.get(),"serial_connected",connected);forcat::integer(out.get(),"updated_monotonic_ms",static_cast<int64_t>(now));
        forcat::integer(out.get(),"last_rx_monotonic_ms",static_cast<int64_t>(last_rx));
        forcat::integer(out.get(),"accepted",accepted);forcat::integer(out.get(),"rejected",rejected);
        forcat::put(out.get(),"source","SIMULATED");forcat::put(out.get(),"physical_pass",false);
        json_object_object_add(out.get(),"telemetry",latest?json_object_get(latest.get()):nullptr);
        std::cout<<forcat::encode(out.get())<<'\n';
    }
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
