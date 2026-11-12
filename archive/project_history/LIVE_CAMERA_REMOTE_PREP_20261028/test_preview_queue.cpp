#include "preview_queue.h"
#include <cstdio>
#include <cstdlib>
using namespace forcat::preview;
unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"FAIL line%d: %s\n",__LINE__,#x);std::exit(1);}}while(0)
int main(){
 Queue<int> q;Stamp s{1,1,100,100,640,480,640,480};
 CHECK(!q.offer(1,"frame1",s,100));q.demand(true,100);CHECK(q.offer(1,"frame1",s,100));
 s.id=s.metadata_id=2;s.captured_ms=s.metadata_ms=200;CHECK(!q.offer(2,"frame2",s,200));
 s.captured_ms=s.metadata_ms=300;CHECK(q.offer(2,"frame2",s,300));
 CHECK(q.counts().pending&&q.counts().replaced==1);Item<int> item;CHECK(q.take(item,0)&&item.image==2&&item.metadata=="frame2");
 CHECK(!q.take(item,0));q.demand(false,400);s.captured_ms=s.metadata_ms=500;CHECK(!q.offer(3,"off",s,500));
 q.demand(true,2001);CHECK(s.matches(2000)&&!s.matches(2001));CHECK(!q.offer(3,"stale",s,2001));s.captured_ms=s.metadata_ms=2001;s.metadata_id=99;CHECK(!q.offer(3,"bad_id",s,2001));
 s.metadata_id=s.id;s.metadata_width=320;CHECK(!q.offer(3,"bad_size",s,2001));
 Queue<int> slow;uint64_t now=100;for(unsigned i=1;i<=20000;++i){now+=200;slow.demand(true,now);
   Stamp stamp{i,i,now,now,640,480,640,480};CHECK(slow.offer(static_cast<int>(i),"same-frame",stamp,now));}
 CHECK(slow.counts().pending&&slow.counts().replaced==19999);
 CHECK(slow.take(item,0)&&item.image==20000);slow.close();CHECK(!slow.take(item,0));
 std::printf("PREVIEW_QUEUE_PASS assertions=%u offered_while_viewer_stalled=20000 pending_limit=1 fake_frames_only=true\n",checks);
}
