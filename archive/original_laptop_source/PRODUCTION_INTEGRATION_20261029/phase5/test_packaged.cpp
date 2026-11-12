#include "state_wire.h"
#include "preview_queue.h"
#include "approach_fusion.h"
#include <iostream>
#include <string>
int main(){
  forcat::StateWire wire;std::string out;
  auto sink=[&](const char* p,size_t n)->intptr_t{out.append(p,n);return static_cast<intptr_t>(n);};
  if(!wire.offer("FORCAT_FRAME_V1 {}",sink)||out!="FORCAT_FRAME_V1 {}\n")return 1;
  forcat::preview::Queue<int> queue;queue.demand(true,1000);
  if(!queue.offer(1,"same-frame",{1,1,1000,1000,640,480,640,480},1000))return 2;
  forcat::preview::Item<int> item;if(!queue.take(item,0)||item.image!=1)return 3;
  forcat::ApproachFusion fusion;forcat::ApproachEvidence a;forcat::RoiAiEvidence ai;
  if(fusion.update(a,ai,1000)!=forcat::ApproachAction::NONE)return 4;
  if(latency::binding_error({{true,true,{1,3,320,320}},{false,true,{1,84,2100}}},false)!="")return 5;
  std::cout<<"PACKAGED_CXX14_PASS fake_io_only=true target_ARM64_build=NOT_VERIFIED\n";
}
