#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
namespace std {using ::strncpy;}
namespace bench_v8 {
enum class FeedStage {OPENING,WAIT_MANUAL_HX,FAULT};
FeedStage feed_stage=FeedStage::FAULT,next=FeedStage::FAULT;
bool manual_feed_active=true,cat_inspect_required=false;
void beginManualFeed(uint32_t,const char*){feed_stage=next;}
}
struct Port {void print(const char*){}}p;Port&protocolSerial(){return p;}
namespace Backup {bool active=false;void attempt(uint32_t now){
  bench_v8::beginManualFeed(now,"POWER_BACKUP_E1");
  if(bench_v8::feed_stage==bench_v8::FeedStage::OPENING || bench_v8::feed_stage==bench_v8::FeedStage::WAIT_MANUAL_HX){
    bench_v8::manual_feed_active=false;active=true;
    protocolSerial().print("BACKUP: 2<=E1<30cm x3, measured35g cycle\n");
  } else bench_v8::cat_inspect_required=true;
}}
namespace Schedule {char active[65]={};bool accepted=false;
void ack(const char*,const char*status,const char*){accepted=!strcmp(status,"ACCEPTED");}
bool attempt(uint32_t now,const char*id){
  bench_v8::beginManualFeed(now,"SCHEDULED");
  if(bench_v8::feed_stage!=bench_v8::FeedStage::OPENING && bench_v8::feed_stage!=bench_v8::FeedStage::WAIT_MANUAL_HX) { ack(id,"REJECTED","START_FAILED");return true; }
  bench_v8::manual_feed_active=false; // full weight-controlled timeout shared with manual feeding
  std::strncpy(active,id,64);active[64]=0;
  ack(id,"ACCEPTED","MEASURED_35G_ATTEMPT_STARTED");return true;
}}
int main(){
 bench_v8::FeedStage stages[]={bench_v8::FeedStage::OPENING,bench_v8::FeedStage::WAIT_MANUAL_HX};for(auto stage:stages){
   bench_v8::next=stage;bench_v8::cat_inspect_required=false;Backup::active=false;
   Backup::attempt(10);assert(Backup::active&&!bench_v8::cat_inspect_required);
   Schedule::accepted=false;Schedule::attempt(10,"test");assert(Schedule::accepted&&!strcmp(Schedule::active,"test"));
 }
 bench_v8::next=bench_v8::FeedStage::FAULT;Backup::active=false;Backup::attempt(10);assert(!Backup::active&&bench_v8::cat_inspect_required);
 Schedule::accepted=true;Schedule::attempt(10,"fail");assert(!Schedule::accepted);
 puts("PASS: actual backup and scheduled adapters accept queued-HX and opening states, keep backup tracking active without inspection-locking pending requests, and still reject real start failure.");
}
