#include <cstdio>
#include <cstdlib>
#include <vector>
#include <string>
#include "m4/approach_dog_warning.h"
#include "approach_fusion.h"
#include "feed_policy.h"
#include "roi_species.h"
namespace ad=m4::approach_dog;
unsigned checks=0,cases=0;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"FAIL line%d: %s\n",__LINE__,#x);std::exit(1);}}while(0)
struct IO:m4::PinIO {
 struct Edge{uint32_t at;bool high;};std::vector<Edge> edges;std::vector<int> order;uint32_t now=0;bool high=false;
 bool inputAllowed(int p)const override{return p==2;}bool outputAllowed(int p)const override{return p==2;}
 void input(int,m4::Pull)override{}void output(int p)override{CHECK(p==2);order.push_back(2);}
 bool read(int)override{return high;}void write(int p,bool value)override{CHECK(p==2);high=value;edges.push_back({now,value});order.push_back(value?1:0);}
 void pauseMicros(uint32_t)override{}void enterCritical()override{}void exitCritical()override{}
 unsigned lows()const{unsigned n=0;for(auto e:edges)if(!e.high)++n;return n;}
};
struct F {
 IO io;ad::Approach gate;ad::Buzzer buzzer{io};ad::Receiver receiver{gate,buzzer,123};dog_wire::Parser parser;
 forcat::ApproachFusion fusion;forcat::FeedArbiter arbiter;uint32_t now=100,seq=0,request=1;unsigned auto_requests=0,warnings=0;
 std::string species="NONE";bool ai_fresh=true,roi=true;ad::Result last=ad::BAD_COMMAND;
 F(){io.now=now;buzzer.begin();uint8_t p[9]{1};dog_wire::put(p+1,123);dog_wire::put(p+5,456);wire(dog_wire::HELLO,p,9);}
 void advance(uint32_t ms){for(uint32_t i=0;i<ms;i+=10){now+=10;io.now=now;buzzer.tick(now);gate.tick(now);}}
 void wire(uint8_t cmd,const uint8_t* p,uint16_t n,bool corrupt=false,uint32_t id=0){
   uint8_t bytes[uart_v1::MAX_FRAME];size_t size=0;CHECK(uart_v1::encode(id?id:++request,cmd,p,n,bytes,sizeof(bytes),size));
   if(corrupt)bytes[size-1]^=1;
   for(size_t i=0;i<size;++i)parser.feed(bytes[i],now,[&](uint32_t rid,uint8_t c,const uint8_t* data,uint16_t count){last=receiver.receive(rid,c,data,count,now);});
 }
 void warning(bool corrupt=false,uint32_t id=0){uint8_t p[21]{1};dog_wire::put(p+1,123);dog_wire::put(p+5,456);dog_wire::put(p+9,gate.event());dog_wire::put(p+13,gate.eventAt());dog_wire::put(p+17,gate.eventAt()+1500);wire(dog_wire::WARNING,p,21,corrupt,id);}
 void sample(float cm,bool valid=true,uint32_t gap=500){
   advance(gap);gate.sample(valid,cm,now,now);
   forcat::ApproachEvidence a{123,456,now,now,gate.event(),gate.eventAt(),gate.valid(),gate.state()==ad::State::CONFIRMED,cm};
   forcat::RoiAiEvidence ai{species,ai_fresh,roi,++seq,now};
   ai.roi_mode=forcat::food_roi::Mode::ROI_ENABLED; // these historical cases explicitly exercise ROI mode
   const auto action=fusion.update(a,ai,now);
   if(action==forcat::ApproachAction::DOG_WARNING){++warnings;warning();}
   if(action==forcat::ApproachAction::AUTO_CAT){++auto_requests;forcat::FeedEvidence e;e.species="CAT";e.observations_fresh=e.near_confirmed_stable=e.telemetry_safe=true;
     const auto d=arbiter.evaluate({std::to_string(auto_requests),"AUTO_CAT","",35},e,now);
     CHECK(!d.qualified && !d.actuator_execution && d.qualification_reason=="WEIGHT_NOT_CALIBRATED");}
 }
 void far(){for(int i=0;i<5;++i)sample(35);CHECK(gate.state()==ad::State::ARMED);}
 void near(){sample(19);sample(18);sample(19);}
};
template<class T>void test(const char* name,T body){body();++cases;std::printf("PASS %02u %s\n",cases,name);}
int main(){
 test("boot_near_no_feed_no_beep",[]{F f;f.species="DOG";for(int i=0;i<10;++i)f.sample(19);CHECK(f.gate.state()==ad::State::NOT_ARMED && !f.warnings && !f.auto_requests && f.io.lows()==0);});
 test("far2s_then3near_CAT_one_arbiter_dryrun_blocked",[]{F f;f.species="CAT";f.far();f.near();f.sample(19);CHECK(f.auto_requests==1 && !f.warnings && !f.io.lows());});
 test("same_approach_DOG_exact_two_200ms_beeps",[]{F f;f.species="DOG";f.far();f.near();CHECK(f.warnings==1 && !f.auto_requests && !f.io.high);const auto at=f.now;f.advance(200);CHECK(f.io.high);f.advance(200);CHECK(!f.io.high);f.advance(200);CHECK(f.io.high && f.buzzer.completed()==1 && f.io.lows()==2);CHECK(f.io.edges[1].at==at && f.io.edges[2].at==at+200 && f.io.edges[3].at==at+400 && f.io.edges[4].at==at+600);});
 test("DOG_near2minutes_no_repeat",[]{F f;f.species="DOG";f.far();f.near();for(int i=0;i<240;++i)f.sample(18);CHECK(f.warnings==1 && f.buzzer.completed()==1 && f.io.lows()==2);});
 test("new_approach_before60s_no_beep",[]{F f;f.species="DOG";f.far();f.near();f.advance(600);f.far();f.near();CHECK(f.warnings==2 && f.last==ad::COOLDOWN && f.io.lows()==2);});
 test("leave_and_new_approach_after60s_two_more",[]{F f;f.species="DOG";f.far();f.near();f.advance(61000);f.far();f.near();f.advance(600);CHECK(f.buzzer.completed()==2 && f.io.lows()==4);});
 test("DOG25cm_no_event",[]{F f;f.species="DOG";f.far();for(int i=0;i<10;++i)f.sample(25);CHECK(!f.warnings && !f.io.lows());});
 test("mixed_CAT_DOG_ROI_DOG_priority_only_warning",[]{forcat::RoiSpecies roi(true,0,0,1,1);roi.box(false,true,.95,.1,.1,.9,.9);roi.box(true,false,.8,.1,.1,.9,.9);CHECK(roi.species()=="DOG");F f;f.species=roi.species();f.far();f.near();CHECK(f.warnings==1 && f.auto_requests==0);});
 test("NONE_no_action",[]{F f;f.far();f.near();CHECK(!f.warnings && !f.auto_requests);});
 test("AI_stale_offline_unreviewedROI_no_action",[]{for(int mode=0;mode<3;++mode){F f;f.species=mode==0?"UNKNOWN":"DOG";f.ai_fresh=mode!=1;f.roi=mode!=2;f.far();f.near();CHECK(!f.warnings && !f.auto_requests);}forcat::RoiSpecies roi(false,0,0,1,1);roi.box(true,false,.99,0,0,1,1);CHECK(roi.species()=="UNKNOWN");});
 test("invalid_null_timeout_below5_never_confirms",[]{F f;f.species="DOG";f.far();for(int i=0;i<5;++i){f.sample(19);f.sample(0,false);f.sample(4);}CHECK(!f.warnings && f.gate.state()==ad::State::ARMED);});
 test("19_35_18_not_three_consecutive",[]{F f;f.species="DOG";f.far();f.sample(19);f.sample(35);f.sample(18);CHECK(!f.warnings);});
 test("CRC_duplicate_stale_command_session_replay_rejected",[]{F f;f.far();f.near();f.warning(true);CHECK(f.io.lows()==0);f.warning(false,100);CHECK(f.last==ad::ACCEPTED);f.warning(false,100);CHECK(f.last==ad::DUPLICATE && f.io.lows()==1);F old;old.far();old.near();old.advance(1510);old.sample(18,true,0);old.warning();CHECK(old.last==ad::STALE && old.io.lows()==0);uint8_t hello[9]{1};dog_wire::put(hello+1,123);dog_wire::put(hello+5,789);f.wire(dog_wire::HELLO,hello,9);f.warning();CHECK(f.last==ad::OLD_SESSION);uint8_t p[1]{1};F bad;bad.wire(uart_v1::FEED_REQUEST,p,1);CHECK(bad.last==ad::BAD_COMMAND && !bad.io.lows());});
 test("boot_HIGH_before_OUTPUT_and_OFF_after",[]{F f;CHECK(f.io.order[0]==1 && f.io.order[1]==2 && f.io.high);CHECK(f.buzzer.start(f.now));f.advance(600);CHECK(f.io.high && !f.buzzer.active());});
 test("buzzer_tick_nonblocking_duplicates_do_not_extend",[]{F f;CHECK(f.buzzer.start(f.now));f.advance(100);CHECK(!f.buzzer.start(f.now));f.advance(100);CHECK(f.io.high);f.advance(400);CHECK(f.buzzer.completed()==1);});
 test("warning_has_only_GPIO2_and_AUTO_cooldown2h",[]{F f;f.species="DOG";f.far();f.near();f.advance(600);CHECK(f.io.lows()==2 && !f.auto_requests);forcat::FeedArbiter a(100);forcat::FeedEvidence e;e.weight_calibrated=e.telemetry_safe=e.near_confirmed_stable=e.observations_fresh=true;e.species="CAT";CHECK(a.evaluate({"a","AUTO_CAT","",35},e,1000).qualified);CHECK(a.evaluate({"b","AUTO_CAT","",35},e,2000).qualification_reason=="COOLDOWN");CHECK(a.evaluate({"c","AUTO_CAT","",35},e,7201000).qualified);});
 test("three_samples_outside1500ms_no_event",[]{F f;f.species="DOG";f.far();f.sample(19);f.sample(18,true,750);f.sample(19,true,900);CHECK(!f.warnings);});
 test("invalid_not_release_hysteresis_not_rearm",[]{F f;f.species="DOG";f.far();f.near();for(int i=0;i<8;++i)f.sample(0,false);for(int i=0;i<8;++i)f.sample(25);f.near();CHECK(f.warnings==1);});
 test("transport_delayed_AI_ROI_outside_no_action",[]{F f;f.species="DOG";f.far();f.sample(19);f.sample(18);f.advance(500);f.gate.sample(true,19,f.now,f.now);
   forcat::ApproachEvidence a{123,456,f.now,f.now,f.gate.event(),f.gate.eventAt(),true,true,19};
   forcat::RoiAiEvidence ai{"DOG",true,true,++f.seq,static_cast<uint64_t>(f.now)+2000};
   CHECK(f.fusion.update(a,ai,static_cast<uint64_t>(f.now)+2000)==forcat::ApproachAction::NONE && f.warnings==0 && f.io.lows()==0);
   forcat::RoiSpecies roi(true,.4,.4,.6,.6);roi.box(true,false,.9,0,0,.2,.2);CHECK(roi.species()=="NONE");});
 std::printf("APPROACH_DOG_CASES_PASS cases=%u assertions=%u mock_only=true\n",cases,checks);
}
