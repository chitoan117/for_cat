#include "preview_queue.h"
#include <atomic>
#include <future>
#include <iostream>
#include <memory>
#include <stdexcept>
using namespace forcat::preview;
std::atomic<int> alive{0},peak{0};
struct Image {
  const unsigned id;explicit Image(unsigned n):id(n){const int count=++alive;int old=peak.load();while(count>old&&!peak.compare_exchange_weak(old,count)){} }
  ~Image(){--alive;}
};
unsigned checks=0;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("resource check failed");}
int main(){
 try{
  Queue<std::shared_ptr<const Image>> q;std::promise<void> first,release;
  auto released=release.get_future();
  auto worker=std::async(std::launch::async,[&]{
    Item<std::shared_ptr<const Image>> item;
    if(!q.take(item,1000))throw std::runtime_error("initial frame absent");
    if(item.image->id!=item.stamp.id)throw std::runtime_error("identity mismatch");
    first.set_value();released.wait(); // deterministic stalled encoder/network
    return item.image->id;
  });
  const auto begin=latency::Clock::now();
  q.demand(true,1000);check(q.offer(std::make_shared<const Image>(1),"frame1",{1,1,1000,1000,640,480,640,480},1000));
  check(first.get_future().wait_for(std::chrono::seconds(1))==std::future_status::ready);
  for(unsigned n=2;n<=240;++n){const uint64_t now=1000+n*200;q.demand(true,now);
    if(!q.offer(std::make_shared<const Image>(n),"frame"+std::to_string(n),{n,n,now,now,640,480,640,480},now))throw std::runtime_error("offer stalled");}
  check(alive.load()==2 && peak.load()<=3);check(q.counts().pending && q.counts().replaced==238);
  release.set_value();check(worker.get()==1);
  Item<std::shared_ptr<const Image>> latest;check(q.take(latest,0) && latest.image->id==240 && latest.stamp.id==240);
  latest.image.reset();check(alive.load()==0);
  auto waiting=std::async(std::launch::async,[&]{Item<std::shared_ptr<const Image>> item;return q.take(item,10000);});
  q.close();check(waiting.wait_for(std::chrono::seconds(1))==std::future_status::ready && !waiting.get());
  Queue<int> bounded;bounded.demand(true,1000);
  check(!bounded.offer(1,std::string(4097,'x'),{1,1,1000,1000,640,480,640,480},1000));
  check(!bounded.offer(1,"oversize",{1,1,1000,1000,9999,480,9999,480},1000));
  std::cout<<"RESOURCE_BACKPRESSURE_PASS checks="<<checks<<" offered=240 peak_owned_images="<<peak.load()
           <<" windows_elapsed_ms="<<latency::milliseconds(begin,latency::Clock::now())<<" jetson_benchmark=false\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
