// File-only executable. No serial, device discovery, camera, services or TX API.
#include "telemetry.h"
#include "diagnostic_session.h"
#include <fstream>
#include <iostream>
int main(int argc,char**argv){
 if(argc!=3){std::cerr<<"parser_replay EXISTING_CAPTURE CHUNK_SIZE\n";return 2;}
 try{
  const unsigned chunk=static_cast<unsigned>(std::stoul(argv[2]));if(chunk<1||chunk>8192)return 2;
  std::ifstream in(argv[1],std::ios::binary);if(!in)return 2;
  forcat::LineFramer framer;forcat::DiagnosticSession state;state.connection();unsigned accepted=0,rejected=0;
  auto emit=[&](const std::string& line){
   if(line.empty()||line[0]!='{')return;
   auto result=forcat::own(json_object_new_object());
   try{auto parsed=forcat::parseTelemetry(line);state.accept(parsed.uptime,1000);++accepted;
     forcat::put(result.get(),"event","ACCEPTED_SOFTWARE_REPLAY");
     json_object_object_add(result.get(),"telemetry",json_object_get(parsed.normalized.get()));
   }catch(const forcat::UnsafeTelemetry&e){state.invalid(true);++rejected;forcat::put(result.get(),"event","UNSAFE_LATCHED");forcat::put(result.get(),"reason",e.what());}
    catch(const std::invalid_argument&e){state.invalid();++rejected;forcat::put(result.get(),"event","REJECTED");forcat::put(result.get(),"reason",e.what());}
   forcat::put(result.get(),"health",state.health(1000,3000));forcat::put(result.get(),"physical_pass",false);
   std::cout<<forcat::encode(result.get())<<'\n';
  };
  std::vector<char> buffer(chunk);
  while(in){in.read(buffer.data(),buffer.size());const auto count=in.gcount();if(count<=0)break;
    const auto old=framer.oversized;framer.feed(buffer.data(),static_cast<size_t>(count),emit);
    if(old!=framer.oversized)state.invalid();
  }
  auto summary=forcat::own(json_object_new_object());forcat::put(summary.get(),"event","REPLAY_SUMMARY");
  forcat::integer(summary.get(),"accepted",accepted);forcat::integer(summary.get(),"rejected",rejected);
  forcat::integer(summary.get(),"oversized",static_cast<int64_t>(framer.oversized));
  forcat::put(summary.get(),"health_before_file_close",state.health(1000,3000));
  forcat::put(summary.get(),"transmitted_commands",false);forcat::put(summary.get(),"physical_pass",false);
  std::cout<<forcat::encode(summary.get())<<'\n';
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
