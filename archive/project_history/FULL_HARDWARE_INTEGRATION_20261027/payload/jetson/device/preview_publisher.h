#pragma once
// Jetson-only adapter. It never opens a camera: images come from the detector's
// existing Capture/LatestSlot. JPEG, annotation and bounded HTTP run on this worker.
#include "preview_queue.h"
#include "telemetry.h"
#include <opencv2/opencv.hpp>
#include <atomic>
#include <fstream>
#include <thread>
#include <iostream>
#include <cstdlib>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/resource.h>
#include <sys/syscall.h>
namespace forcat { namespace preview {
inline uint64_t nowMs(){return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(latency::Clock::now().time_since_epoch()).count());}
inline std::string base64(const std::string& in){const char* alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";std::string out;
 for(size_t i=0;i<in.size();i+=3){const uint32_t n=(static_cast<uint32_t>(static_cast<unsigned char>(in[i]))<<16)|
   (i+1<in.size()?static_cast<uint32_t>(static_cast<unsigned char>(in[i+1]))<<8:0)|(i+2<in.size()?static_cast<unsigned char>(in[i+2]):0);
   out+=alphabet[(n>>18)&63];out+=alphabet[(n>>12)&63];out+=i+1<in.size()?alphabet[(n>>6)&63]:'=';out+=i+2<in.size()?alphabet[n&63]:'=';}
 return out;}
class Http {
 unsigned port_;std::string token_;
 public:
 Http(unsigned port,std::string token):port_(port),token_(std::move(token)){}
 std::string request(const std::string& path,const std::string& headers,const std::vector<uint8_t>& body={}){
   const auto deadline=nowMs()+250;
   const int fd=socket(AF_INET,SOCK_STREAM|SOCK_CLOEXEC,0);if(fd<0)return "";
   fcntl(fd,F_SETFL,fcntl(fd,F_GETFL,0)|O_NONBLOCK);
   sockaddr_in address{};address.sin_family=AF_INET;address.sin_port=htons(static_cast<uint16_t>(port_));inet_pton(AF_INET,"127.0.0.1",&address.sin_addr);
   connect(fd,reinterpret_cast<sockaddr*>(&address),sizeof(address));
   const std::string head=(body.empty()?"GET ":"POST ")+path+" HTTP/1.0\r\nHost: 127.0.0.1\r\nAuthorization: Bearer "+token_+"\r\nConnection: close\r\n"+headers+"Content-Length: "+std::to_string(body.size())+"\r\n\r\n";
   std::vector<uint8_t> bytes(head.begin(),head.end());bytes.insert(bytes.end(),body.begin(),body.end());size_t sent=0;std::string response;
   while(nowMs()<deadline&&sent<bytes.size()){
     pollfd p{fd,POLLOUT,0};if(poll(&p,1,10)<=0)continue;
     if(p.revents&(POLLERR|POLLHUP|POLLNVAL))break;
     const auto n=send(fd,bytes.data()+sent,bytes.size()-sent,MSG_NOSIGNAL);if(n>0)sent+=static_cast<size_t>(n);
   }
   while(nowMs()<deadline&&sent==bytes.size()&&response.size()<8192){
     pollfd p{fd,POLLIN,0};if(poll(&p,1,10)<=0)continue;char b[2048];const auto n=recv(fd,b,sizeof(b),0);
     if(n<=0)break;response.append(b,static_cast<size_t>(n));
   }
   close(fd);if(response.find(" 200 ")==std::string::npos)return "";
   const auto at=response.find("\r\n\r\n");return at==std::string::npos?"":response.substr(at+4);
 }
};
class Publisher {
 Queue<cv::Mat> queue_;std::atomic<bool> stop_{false};std::thread worker_;
  unsigned quality_=70;bool enabled_=false;
 void render(Item<cv::Mat>& item,Http& http){
   if(!item.stamp.matches(nowMs()))return;
   auto m=own(json_tokener_parse(item.metadata.c_str()));if(!m)return;
   const auto metadata_id=field(m.get(),"source_frame_id"),metadata_at=field(m.get(),"roi_observation_ms");
   if(!metadata_id||!metadata_at||!json_object_is_type(metadata_id,json_type_int)||!json_object_is_type(metadata_at,json_type_int)||
      json_object_get_int64(metadata_id)!=static_cast<int64_t>(item.stamp.id)||json_object_get_int64(metadata_at)!=static_cast<int64_t>(item.stamp.captured_ms)||
      counter(m.get(),"frame_width")!=static_cast<uint32_t>(item.image.cols)||counter(m.get(),"frame_height")!=static_cast<uint32_t>(item.image.rows))return;
   cv::Mat image;const double ratio=std::min(640.0/item.image.cols,480.0/item.image.rows);
   cv::resize(item.image,image,cv::Size(std::max(2,static_cast<int>(item.image.cols*ratio)),std::max(2,static_cast<int>(item.image.rows*ratio))));
    const auto epoch=text(m.get(),"producer_epoch");if(epoch.empty())return;
    auto result=own(json_object_new_object());put(result.get(),"producer_epoch",epoch);integer(result.get(),"frame_id",static_cast<int64_t>(item.stamp.id));
    integer(result.get(),"ai_schema_version",1);
   integer(result.get(),"metadata_frame_id",static_cast<int64_t>(item.stamp.id));integer(result.get(),"overlay_frame_id",static_cast<int64_t>(item.stamp.id));
   integer(result.get(),"captured_monotonic_ms",static_cast<int64_t>(item.stamp.captured_ms));integer(result.get(),"metadata_monotonic_ms",static_cast<int64_t>(item.stamp.metadata_ms));
   integer(result.get(),"width",image.cols);integer(result.get(),"height",image.rows);put(result.get(),"source","REAL");put(result.get(),"simulated",false);
   put(result.get(),"overlay_applied",true);copy(result.get(),"classification",m.get(),"classification");copy(result.get(),"confidence",m.get(),"confidence");
   const auto mode=text(m.get(),"roi_mode");put(result.get(),"roi_mode",mode=="ROI_ENABLED"?"ROI_ENABLED":"FULL_FRAME");
   auto boxes=json_object_new_array();auto input=field(m.get(),"detections");
   for(size_t i=0;input&&i<json_object_array_length(input)&&i<8;++i){auto d=json_object_array_get_idx(input,i),b=field(d,"bbox");
     double x1=0,y1=0,x2=0,y2=0;
     if(!nullableNumber(b,"x1",x1)||!nullableNumber(b,"y1",y1)||!nullableNumber(b,"x2",x2)||!nullableNumber(b,"y2",y2)||x1<0||y1<0||x1>=x2||y1>=y2||x2>1||y2>1)continue;
     auto out=json_object_new_object();copy(out,"species",d,"species");auto coords=json_object_new_array();for(double n:{x1,y1,x2,y2})json_object_array_add(coords,json_object_new_double(n));
     json_object_object_add(out,"bbox",coords);json_object_array_add(boxes,out);
     const auto color=text(d,"species")=="CAT"?cv::Scalar(30,230,80):cv::Scalar(30,70,240);
     cv::rectangle(image,cv::Point(static_cast<int>(x1*image.cols),static_cast<int>(y1*image.rows)),cv::Point(static_cast<int>(x2*image.cols),static_cast<int>(y2*image.rows)),color,2);
     double conf=0;nullableNumber(d,"confidence",conf);const std::string label=text(d,"species")+" "+std::to_string(static_cast<int>(conf*100))+"%";
     cv::putText(image,label,cv::Point(static_cast<int>(x1*image.cols),std::max(25,static_cast<int>(y1*image.rows)-5)),cv::FONT_HERSHEY_SIMPLEX,.5,color,1);
   }
   json_object_object_add(result.get(),"detections",boxes);
   json_object* roi=nullptr;
   if(mode=="ROI_ENABLED"&&json_object_object_get_ex(m.get(),"food_roi",&roi)&&roi&&json_object_array_length(roi)==4){
     const auto x1=json_object_get_double(json_object_array_get_idx(roi,0)),y1=json_object_get_double(json_object_array_get_idx(roi,1));
     const auto x2=json_object_get_double(json_object_array_get_idx(roi,2)),y2=json_object_get_double(json_object_array_get_idx(roi,3));
     cv::rectangle(image,cv::Point(static_cast<int>(x1*image.cols),static_cast<int>(y1*image.rows)),cv::Point(static_cast<int>(x2*image.cols),static_cast<int>(y2*image.rows)),cv::Scalar(0,220,255),2);
     json_object_object_add(result.get(),"food_roi",json_object_get(roi));
   }else json_object_object_add(result.get(),"food_roi",nullptr);
   const std::string roi_label=mode=="ROI_ENABLED"&&!boolean(m.get(),"roi_calibrated")?"ROI_ENABLED_NOT_CALIBRATED":mode;
   cv::putText(image,text(m.get(),"classification")+" | "+roi_label+" | frame "+std::to_string(item.stamp.id),cv::Point(8,18),cv::FONT_HERSHEY_SIMPLEX,.48,cv::Scalar(255,255,255),1);
   cv::putText(image,"REAL C++ | capture-ms "+std::to_string(item.stamp.captured_ms),cv::Point(8,image.rows-10),cv::FONT_HERSHEY_SIMPLEX,.42,cv::Scalar(255,255,255),1);
   std::vector<uint8_t> jpeg;if(!cv::imencode(".jpg",image,jpeg,{cv::IMWRITE_JPEG_QUALITY,static_cast<int>(quality_)})||jpeg.size()>524288)return;
   http.request("/internal/camera/frame","Content-Type: image/jpeg\r\nX-Frame-Meta: "+base64(encode(result.get()))+"\r\n",jpeg);
 }
 public:
 Publisher():queue_(6){
   try{
   const char* flag=std::getenv("FORCAT_STREAM_PUBLISH");if(!flag||std::string(flag)!="1")return;
   const char* path=std::getenv("FORCAT_CAMERA_PRODUCER_TOKEN_FILE");if(!path)throw std::invalid_argument("private producer token file required");
   std::ifstream file(path);std::string token;std::getline(file,token);if(!token.empty()&&token.back()=='\r')token.pop_back();
   if(token.size()<32||token.size()>128||token.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")!=std::string::npos)throw std::invalid_argument("producer token invalid");
   const char* quality=std::getenv("FORCAT_JPEG_QUALITY");if(quality)quality_=static_cast<unsigned>(std::stoul(quality));if(quality_<30||quality_>90)throw std::invalid_argument("JPEG quality30..90 required");
   unsigned port=8000;const char* port_env=std::getenv("API_PORT");if(port_env)port=static_cast<unsigned>(std::stoul(port_env));if(!port||port>65535)throw std::invalid_argument("API port");
    enabled_=true;
   worker_=std::thread([this,port,token]{Http http(port,token);uint64_t polled=0;
     setpriority(PRIO_PROCESS,static_cast<id_t>(syscall(SYS_gettid)),10); // lower only this encoder thread's scheduling priority
     while(!stop_.load()){
       if(nowMs()-polled>=500){polled=nowMs();bool wanted=false;try{auto data=own(json_tokener_parse(http.request("/internal/camera/demand","").c_str()));wanted=counter(data.get(),"viewers")>0;}catch(const std::exception&){}queue_.demand(wanted,nowMs());}
       Item<cv::Mat> item;if(queue_.take(item,50))try{render(item,http);}catch(const std::exception&){} // preview failure never kills detector
     }
   });
   }catch(const std::exception& e){enabled_=false;std::cerr<<"PREVIEW_DISABLED "<<e.what()<<'\n';} // AI remains available
 }
 void offer(const cv::Mat& image,const std::string& metadata,uint64_t id,uint64_t stamp){
   if(!enabled_)return;
   Stamp s{id,id,stamp,stamp,image.cols,image.rows,image.cols,image.rows};
   queue_.offer(image,metadata,s,nowMs()); // shared immutable Mat reference, no encode/network on AI thread
 }
 void stop(){stop_.store(true);queue_.close();if(worker_.joinable())worker_.join();}
 ~Publisher(){stop();}
};
} }
