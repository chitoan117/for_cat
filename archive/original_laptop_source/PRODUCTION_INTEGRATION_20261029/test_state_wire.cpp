#include "state_wire.h"
#include "approach_fusion.h"
#include <iostream>
#include <cstdlib>
unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){std::cerr<<"FAIL "<<__LINE__<<'\n';std::exit(1);}}while(0)
int main(){
  forcat::StateWire w;std::string out;bool stalled=true;
  auto sink=[&](const char* p,size_t n)->intptr_t{if(stalled)return 0;size_t take=n>3?3:n;out.append(p,take);return take;};
  CHECK(w.offer("first",sink));
  for(int i=0;i<1000;++i)CHECK(w.offer("latest"+std::to_string(i),sink));
  CHECK(w.buffered()<32768 && w.dropped()==999);
  stalled=false;for(int i=0;i<100;++i)CHECK(w.flush(sink));
  CHECK(out=="first\nlatest999\n");
  CHECK(!w.offer("bad\nline",sink));
  CHECK(!w.offer(std::string(17000,'x'),sink));
  forcat::ApproachFusion f;forcat::ApproachEvidence a{1,2,1000,1000,1,1000,true,true,19};
  forcat::RoiAiEvidence ai;ai.species="CAT";ai.fresh=true;ai.producer_epoch="A";
  for(unsigned i=0;i<4;++i){a.now=a.sample=1000+i*500;a.event_at=a.now;ai.stamp=a.now;ai.sequence=i+1;
    CHECK(f.update(a,ai,a.now)==(i==3?forcat::ApproachAction::AUTO_CAT:forcat::ApproachAction::NONE));}
  ai.producer_epoch="B";
  for(unsigned i=0;i<4;++i){a.now=a.sample=3000+i*500;a.event_at=a.now;ai.stamp=a.now;ai.sequence=i+1;CHECK(f.update(a,ai,a.now)==forcat::ApproachAction::NONE);}
  std::cout<<"STATE_WIRE_CONTRACT_PASS checks="<<checks<<" CXX14 fake_sink_only=true\n";
}
