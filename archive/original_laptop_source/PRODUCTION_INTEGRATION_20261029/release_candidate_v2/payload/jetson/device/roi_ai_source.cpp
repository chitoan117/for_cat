// Optional ROI, default FULL_FRAME. Reuses current detector/decoder/capture;
// original source/binary/engine stay unchanged. Never runs alongside another camera owner.
#include "shadow/geometry_detector.cpp"
#include "telemetry.h"
#include "roi_species.h"
#include "preview_publisher.h"
#include "state_wire.h"
#include <cerrno>
#include <sys/file.h>
#include <fcntl.h>
#include <unistd.h>

namespace {
uint64_t monotonicMs(){return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(latency::Clock::now().time_since_epoch()).count());}
std::string lineFile(const std::string& p){std::ifstream in(p);std::string s;std::getline(in,s);return s;}
}
int main(int argc,char** argv){
 using namespace forcat;
 if(argc!=4&&argc!=6){std::cerr<<"roi_ai_source CANONICAL_DB ROI_CONFIG_OR_- CAMERA_DEVICE [--roi-mode FULL_FRAME|ROI_ENABLED]\n";return 2;}
 try{
   std::cout.rdbuf(std::cerr.rdbuf()); // TensorRT diagnostics must not interleave framed stdout
   std::signal(SIGINT,onSignal);std::signal(SIGTERM,onSignal);
   const std::string dbpath=argv[1],device=argv[3];
   const int lock=open((dbpath+"-capture.lock").c_str(),O_CREAT|O_RDWR|O_CLOEXEC,0600);
   if(lock<0 || flock(lock,LOCK_EX|LOCK_NB)<0)throw std::runtime_error("another candidate capture owner exists");
   const auto flags=fcntl(STDOUT_FILENO,F_GETFL,0);
   if(flags<0 || fcntl(STDOUT_FILENO,F_SETFL,flags|O_NONBLOCK)<0)throw std::runtime_error("state stdout nonblocking setup");
   std::signal(SIGPIPE,SIG_IGN);
   StateWire state_wire;
   auto sink=[](const char* bytes,size_t n)->intptr_t{const auto result=write(STDOUT_FILENO,bytes,n);
     return result<0 && (errno==EAGAIN || errno==EWOULDBLOCK || errno==EINTR)?0:result;};
   food_roi::Mode override_mode=food_roi::Mode::INVALID;
   if(argc==6){override_mode=food_roi::mode(argv[5]);if(std::string(argv[4])!="--roi-mode"||override_mode==food_roi::Mode::INVALID)throw std::invalid_argument("invalid explicit ROI mode");}
   std::ifstream cfgfile(argv[2]);std::string body;
   if(std::string(argv[2])!="-"&&cfgfile){char bytes[4097];cfgfile.read(bytes,sizeof(bytes));body.assign(bytes,static_cast<size_t>(cfgfile.gcount()));}
   else body="{}"; // no ROI configuration does not disable FULL_FRAME recognition
   auto config=food_roi::parseConfig(body,override_mode);
   if(!config.compatibleCamera(device)){config.syntax_valid=false;config.error="ROI_CAMERA_MISMATCH";}
   const std::string boot=lineFile("/proc/sys/kernel/random/boot_id");
   const std::string epoch=boot+":"+std::to_string(getpid())+":"+std::to_string(monotonicMs());
   auto save=[&](const char* health,const RoiSpecies* scene,bool fresh,uint64_t stamp,uint32_t sequence,json_object* boxes,int frame_width,int frame_height,size_t total,uint64_t capture_sequence=0){
     const bool eligible=scene&&scene->eligible()&&fresh;
      auto state=own(json_object_new_object());put(state.get(),"health",health);put(state.get(),"classification",eligible?scene->species():"UNKNOWN");
      integer(state.get(),"ai_schema_version",1);put(state.get(),"data_source","REAL");put(state.get(),"simulated",false);put(state.get(),"producer_epoch",epoch);
     number(state.get(),"confidence",eligible&&scene->detected(),scene?scene->confidence():0);put(state.get(),"source","EXISTING_CPP_TENSORRT_OPTIONAL_FOOD_ROI");
     put(state.get(),"host_boot_id",boot);put(state.get(),"actuator_execution",false);put(state.get(),"roi_calibrated",config.roiReady());
     put(state.get(),"roi_mode",food_roi::name(config.selection));put(state.get(),"roi_config_valid",config.syntax_valid);
     put(state.get(),"roi_decision_eligible",eligible);put(state.get(),"bbox_available",scene!=nullptr);
     put(state.get(),"bbox_coordinate_space","NORMALIZED_ORIGINAL");put(state.get(),"full_frame_is_tray_evidence",false);
     put(state.get(),"bbox_geometry_valid",scene&&!scene->invalid());integer(state.get(),"frame_width",frame_width);integer(state.get(),"frame_height",frame_height);
     integer(state.get(),"detections_count",static_cast<int64_t>(total));put(state.get(),"bbox_list_truncated",total>8);
     integer(state.get(),"source_frame_id",static_cast<int64_t>(capture_sequence));
     json_object_object_add(state.get(),"detections",boxes?json_object_get(boxes):json_object_new_array());
     put(state.get(),"roi_revision",config.review_id);put(state.get(),"roi_error",config.error);integer(state.get(),"roi_observation_ms",static_cast<int64_t>(stamp));
     if(config.roiReady()){auto region=json_object_new_array();for(double n:{config.roi.x1,config.roi.y1,config.roi.x2,config.roi.y2})json_object_array_add(region,json_object_new_double(n));json_object_object_add(state.get(),"food_roi",region);}
     else json_object_object_add(state.get(),"food_roi",nullptr);
      integer(state.get(),"roi_sequence",sequence);integer(state.get(),"updated_monotonic_ms",static_cast<int64_t>(stamp));
     const auto wall=std::time(nullptr);std::tm tm{};gmtime_r(&wall,&tm);char iso[40];std::strftime(iso,sizeof(iso),"%Y-%m-%dT%H:%M:%SZ",&tm);
     put(state.get(),"last_observation_at",iso);
      const auto json=encode(state.get());
      if(!state_wire.offer("FORCAT_FRAME_V1 "+json,sink) && state_wire.failed())throw std::runtime_error("state consumer disconnected");
      return json;
   };
   save("DISCONNECTED",nullptr,false,0,0,nullptr,0,0,0);
   geometry_validation::Detector detector(ENGINE_PATH); // same FP16 engine, preprocessing and per-class NMS
   latency::Options options;options.device=device;options.gui=false;options.snapshot=false;
    latency::Capture capture(true);capture.open(options);uint32_t sequence=0;
   preview::Publisher preview_publisher;
   while(!interrupted.load(std::memory_order_relaxed)){
     latency::Packet<cv::Mat> packet;
     if(!capture.take(packet)){if(capture.failed())throw std::runtime_error("camera offline");continue;}
     const auto stamp=static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(packet.received.time_since_epoch()).count());
     const auto detections=detector.infer(packet.image);
     const bool fresh=monotonicMs()>=stamp&&monotonicMs()-stamp<=1500;
     RoiSpecies scene(config,packet.image.cols,packet.image.rows);auto boxes=own(json_object_new_array());
     // infer() already undoes letterbox and returns normalized ORIGINAL-camera
     // coordinates. Never reapply a320x320 transform to these boxes.
     for(const auto& detection:detections){
       const auto relation=scene.box(detection.object==behavior_shadow::Object::Dog,detection.object==behavior_shadow::Object::Cat,detection.confidence,
         detection.box.x1,detection.box.y1,detection.box.x2,detection.box.y2);
       if(json_object_array_length(boxes.get())<8){auto item=json_object_new_object();put(item,"species",detection.object==behavior_shadow::Object::Dog?"DOG":"CAT");
         number(item,"confidence",std::isfinite(detection.confidence),detection.confidence);put(item,"roi_relation",food_roi::name(relation));
         auto bbox=json_object_new_object();number(bbox,"x1",std::isfinite(detection.box.x1),detection.box.x1);number(bbox,"y1",std::isfinite(detection.box.y1),detection.box.y1);
         number(bbox,"x2",std::isfinite(detection.box.x2),detection.box.x2);number(bbox,"y2",std::isfinite(detection.box.y2),detection.box.y2);json_object_object_add(item,"bbox",bbox);json_object_array_add(boxes.get(),item);}
     }
     if(sequence==UINT32_MAX)break;
     ++sequence;
     const auto evidence=save("ONLINE",&scene,fresh,stamp,sequence,boxes.get(),packet.image.cols,packet.image.rows,detections.size(),packet.sequence);
     preview_publisher.offer(packet.image,evidence,packet.sequence,stamp);
   }
    preview_publisher.stop();capture.stop();save("DISCONNECTED",nullptr,false,0,sequence,nullptr,0,0,0);
    state_wire.flush(sink);close(lock);return 0;
  }catch(const std::exception& e){std::cerr<<"ROI_AI_ERROR "<<e.what()<<'\n';return 1;}
}
