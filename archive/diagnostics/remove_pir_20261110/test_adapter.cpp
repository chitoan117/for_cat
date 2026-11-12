#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <assert.h>
#include <math.h>
#include "esp32/FallbackGate.h"
namespace std {using ::strcmp;inline float fabs(float v){return __builtin_fabsf(v);}}
uint8_t saved=0;bool nv_enable=false,fail_write=false;unsigned feeds=0;
class Preferences {public:bool begin(const char*,bool){return true;}bool getBool(const char*,bool){return nv_enable;}
uint8_t getUChar(const char*,uint8_t){return saved;}
size_t putBool(const char*,bool x){if(fail_write)return 0;nv_enable=x;return 1;}
size_t putUChar(const char*,uint8_t x){if(fail_write)return 0;saved=x;return 1;}};
struct Serial{void print(const char*){}} serial;Serial& protocolSerial(){return serial;}
bool sensors_enabled=true;

struct Raw {uint32_t sampled_at_ms=0;bool valid=true;float value=20;} ;
struct Sensor{Raw raw;}hc;
struct PWM {bool moving(){return false;}}pwm;
enum class BenchCal{Idle,Busy};BenchCal bench_cal=BenchCal::Idle;
namespace bench_v8 {
enum class FeedStage{IDLE,OPENING,DONE,FAULT};FeedStage feed_stage=FeedStage::IDLE;
enum class TimedGateStop{OPEN,CLOSED,UNKNOWN};TimedGateStop timed_gate_stop=TimedGateStop::CLOSED;
bool demo_exited=false,cat_inspect_required=false,dog_running=false,manual_feed_active=false;
bool busy(){return feed_stage==FeedStage::OPENING;}
bool benchScaleSample(uint32_t now,float& g,uint32_t& at){g=0;at=now;return true;}
void beginManualFeed(uint32_t,const char*){assert(saved==1);++feeds;feed_stage=FeedStage::OPENING;manual_feed_active=true;}
}
#include "backup_adapter.inc"
void sample_tick(uint32_t t){hc.raw.sampled_at_ms=t;power_backup::tick(t);}
int main(){
 using namespace power_backup;
 begin(0);assert(!enabled);sample_tick(31000);sample_tick(32000);sample_tick(33000);assert(feeds==0);
 command("backup_on",34000);command("jetson_ping",34000);
 sample_tick(35000);sample_tick(36000);sample_tick(37000);assert(feeds==0);
 sample_tick(50000);sample_tick(51000);sample_tick(52000);assert(feeds==1&&active&&saved==1&&!bench_v8::manual_feed_active);
 bench_v8::feed_stage=bench_v8::FeedStage::DONE;sample_tick(53000);assert(!active&&saved==2);
 gate=Gate{};begin(54000);assert(gate.used);sample_tick(350000);sample_tick(351000);sample_tick(352000);assert(feeds==1);
 saved=1;begin(360000);assert(bench_v8::cat_inspect_required);
 inspected(360001);assert(saved==2);
 bench_v8::cat_inspect_required=false;bench_v8::feed_stage=bench_v8::FeedStage::IDLE;
 gate=Gate{};saved=0;seen_host=false;boot_at=0;fail_write=true;
 sample_tick(400000);sample_tick(401000);sample_tick(402000);assert(feeds==1&&!storage_ok);
 puts("PASS: disabled default, independent heartbeat gating, persist-before-motion, completion latch, reboot no replay, interrupted inspection, write failure stops motion");
}
