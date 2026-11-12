#pragma once
// Bounded preview consumer of the existing latest-frame primitive. No capture API.
#include "latency_support.h"
#include <atomic>
#include <cstdint>
#include <string>
#include <stdexcept>
namespace forcat { namespace preview {
struct Stamp {
 uint64_t id=0,metadata_id=0,captured_ms=0,metadata_ms=0;
 int width=0,height=0,metadata_width=0,metadata_height=0;
 bool matches(uint64_t now)const{return id&&id==metadata_id&&width>=2&&height>=2&&width==metadata_width&&height==metadata_height&&
   captured_ms==metadata_ms&&now>=captured_ms&&now-captured_ms<=1500;}
};
template<class Image>struct Item {Image image;std::string metadata;Stamp stamp;};
template<class Image>class Queue {
 latency::LatestSlot<Item<Image>> slot_;
 std::atomic<uint64_t> demand_until_{0};uint64_t last_offer_=0;bool have_offer_=false;unsigned fps_;
 public:
 explicit Queue(unsigned fps=6):fps_(fps){if(fps<1||fps>10)throw std::invalid_argument("preview FPS must be1..10");}
 void demand(bool wanted,uint64_t now){demand_until_.store(wanted?now+1000:0,std::memory_order_relaxed);}
 bool offer(Image image,std::string metadata,Stamp stamp,uint64_t now){
   if(demand_until_.load(std::memory_order_relaxed)<=now || !stamp.matches(now) ||
      (have_offer_&&now>=last_offer_&&now-last_offer_<1000/fps_))return false;
   have_offer_=true;last_offer_=now;
   return slot_.publish({std::move(image),std::move(metadata),stamp},latency::Clock::now(),0);
 }
 bool take(Item<Image>& out,unsigned timeout_ms=100){latency::Packet<Item<Image>> packet;
   if(!slot_.take(packet,std::chrono::milliseconds(timeout_ms)))return false;out=std::move(packet.image);return true;}
 void close(){slot_.close();}latency::CaptureCounts counts()const{return slot_.counts();}
};
} }
