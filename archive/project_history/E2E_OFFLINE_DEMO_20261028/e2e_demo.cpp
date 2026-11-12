#include "sim_support.h"
using namespace offline_demo;
unsigned assertions=0,safety_cases=0;
void check(bool value,const std::string& message){++assertions;require(value,message);}
const char* reviewed_roi="{\"enabled\":true,\"calibrated\":true,\"review_id\":\"SYNTHETIC_E2E_ONLY\",\"x1\":0.25,\"y1\":0.25,\"x2\":0.75,\"y2\":0.75}";
void trigger(Harness& h){h.distance=35;h.advance(2600);h.distance=19;h.advance(500);h.distance=18;h.advance(500);h.distance=19;h.advance(500);}
template<class F>void safetyCase(Log& log,const std::string& name,F fn){
 Clock clock("TEST_"+name);log.context(clock,"SAFETY_"+name);fn(clock,log);++safety_cases;
 log.event("TEST_CASE_PASSED",{{"test_name",quote(name)},{"hardware_access","false"}});
}
Preference preferenceBoundary(double consumed,const std::string& fault=""){
 Consumption c;std::vector<Weight> initial{{35,0,true,1},{35,100,true,1},{35,200,true,1},{35,300,true,1}};
 check(c.begin("BOUNDARY_FOOD",initial,300,1,true),"preference start");
 for(uint64_t at=600;at<=60300;at+=300){
   double grams=35-consumed;bool valid=true;uint32_t generation=1;
   if(fault=="NEGATIVE")grams=-.1;
   if(fault=="NAN")grams=std::numeric_limits<double>::quiet_NaN();
   if(fault=="INVALID")valid=false;
   if(fault=="TARE"&&at>=30000)generation=2;
   if(fault=="UNSTABLE"&&at>=57000)grams=(at%600)?5:7;
   if(fault=="STABLE_NOISE"){const double offsets[]={-.03,-.01,.01,.03};grams+=offsets[(at/300)%4];}
   c.observe({grams,at+(fault=="FUTURE_TIME"&&at==30000?100:0),valid,generation},at);
 }
 return c.finish(60300);
}
void runMainDemo(Log& log,Clock& clock,Harness& h){
 log.context(clock,"SCENARIO_1_CAT_FEED");h.prepare();h.arrival("CAT");
 check(h.auto_requests==1&&h.feeding,"CAT did not create exactly one eligible request");
 h.dispense();check(h.feed_success&&h.last_actual==35&&h.servo.angle==90,"CAT35g did not close/complete");
 const auto opens=h.servo.opens;h.advance(3000);check(h.auto_requests==1&&h.servo.opens==opens,"standing CAT retriggered");
 log.event("SCENARIO_RESULT",{{"scenario_number","1"},{"status",quote("PASS")},{"request_count","1"},{"actual_dispensed_grams",number(h.last_actual)},{"servo_final_degrees","90"}});

 log.context(clock,"SCENARIO_2_DOG_WARNING");const auto requests=h.auto_requests,lows=h.buzzer_io.lows;
 h.arrival("DOG");h.advance(800);check(h.warnings_received==1&&h.buzzer_io.lows==lows+2,"DOG missing two beep edges");
 h.advance(120000);check(h.warnings_received==1&&h.auto_requests==requests&&h.servo.opens==opens,"DOG standing repeated or fed");
 log.event("SCENARIO_RESULT",{{"scenario_number","2"},{"status",quote("PASS")},{"dog_warnings","1"},{"buzzer_pulse_count","2"},{"servo_new_opens","0"},{"dog_near_ms","120000"}});

 log.context(clock,"SCENARIO_3_FOOD_A");h.scene("CAT");h.mass=35;h.advance(1500);
 check(h.beginMeal("FOOD_A"),"FOOD_A observation did not start after stable feed");
 const auto start=clock.now;const auto open_before=h.servo.opens,requests_before=h.auto_requests;
 while(clock.now-start<60000){const auto elapsed=clock.now-start;h.mass=elapsed<20000?35:elapsed<45000?25:5;h.step();}
 check(h.preference_result.ready&&h.preference_result.valid&&h.preference_result.starting==35&&h.preference_result.remaining==5&&h.preference_result.consumed==30&&h.preference_result.classification=="LIKE","FOOD_A not LIKE30g");
 check(h.servo.opens==open_before&&h.auto_requests==requests_before,"consumption reopened servo");
 log.event("SCENARIO_RESULT",{{"scenario_number","3"},{"status",quote("PASS")},{"food_name",quote("FOOD_A")},{"starting_mass","35"},{"remaining_mass","5"},{"consumed_mass","30"},{"classification",quote("LIKE")},{"observation_ms","60000"}});

 log.context(clock,"SCENARIO_4_FOOD_B");h.jump(7201000);h.clearBowl();h.food_name="FOOD_B";h.arrival("CAT");
 check(h.auto_requests==2&&h.feeding,"second meal not admitted after valid fake cooldown");
 h.dispense();check(h.feed_success&&h.last_actual==35&&h.controller.record().portions==2,"second dispense/meal ledger failed");
 h.advance(1500);check(h.beginMeal("FOOD_B"),"FOOD_B start");const auto begin=clock.now;const auto before=h.servo.opens;
 while(clock.now-begin<60000){h.mass=clock.now-begin<20000?35:30;h.step();}
 check(h.preference_result.valid&&h.preference_result.consumed==5&&h.preference_result.classification=="DISLIKE"&&h.servo.opens==before,"FOOD_B not DISLIKE5g or reopened");
 log.event("SCENARIO_RESULT",{{"scenario_number","4"},{"status",quote("PASS")},{"food_name",quote("FOOD_B")},{"starting_mass","35"},{"remaining_mass","30"},{"consumed_mass","5"},{"classification",quote("DISLIKE")},{"observation_ms","60000"}});
}
void runSafety(Log& log){
 safetyCase(log,"ROI_ENABLED_CAT_E2E",[](Clock& c,Log& l){Harness h(c,l);h.roi_config=forcat::food_roi::parseConfig(reviewed_roi);h.prepare();h.arrival("CAT");h.dispense();check(h.successes==1&&h.last_actual==35,"ROI enabled feed failed");});
 safetyCase(log,"ROI_OUTSIDE_CAT_DOG_NONE",[](Clock& c,Log& l){Harness h(c,l);h.roi_config=forcat::food_roi::parseConfig(reviewed_roi);h.prepare();h.detections={{"CAT",.9,{.01,.01,.1,.1}},{"DOG",.9,{.8,.8,.95,.95}}};trigger(h);check(h.auto_requests==0&&h.warnings_received==0&&h.servo.opens==0,"outside ROI acted");h.detections.clear();h.advance(3000);check(!h.auto_requests,"NONE acted");});
 safetyCase(log,"MIXED_DOG_PRIORITY",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.detections={{"CAT",.9,{.3,.3,.7,.7}},{"DOG",.9,{.3,.3,.7,.7}}};trigger(h);h.advance(800);check(h.auto_requests==0&&h.warnings_received==1&&h.servo.opens==0,"mixed scene fed");});
 safetyCase(log,"UNREVIEWED_ROI_BLOCK",[](Clock& c,Log& l){Harness h(c,l);h.roi_config=forcat::food_roi::parseConfig("{\"enabled\":true}");h.prepare();h.arrival("CAT");check(!h.auto_requests&&!h.servo.opens,"invalid ROI acted");});
 safetyCase(log,"BOOT_NEAR_NO_ACTION",[](Clock& c,Log& l){Harness h(c,l);h.scene("DOG");h.distance=19;h.advance(5000);check(!h.auto_requests&&!h.warnings_received&&!h.servo.opens,"boot near acted");});
 safetyCase(log,"DISTANCE_20_30_5_HYSTERESIS",[](Clock& c,Log& l){Harness h(c,l);h.distance=30;h.scene("CAT");h.advance(4000);h.distance=20;h.advance(2000);check(!h.auto_requests,"30cm rearmed or boot20cm acted");h.distance=30.001;h.advance(2600);h.distance=20;h.advance(500);h.distance=5;h.advance(500);h.distance=20;h.advance(500);check(h.auto_requests==1,"5/20 inclusive edge did not confirm");});
 safetyCase(log,"BAD_DISTANCE_NO_EVENT",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.scene("CAT");h.distance=35;h.advance(2600);for(int i=0;i<5;++i){h.distance=19;h.advance(500);h.distance_valid=false;h.advance(500);h.distance_valid=true;h.distance=4;h.advance(500);}check(!h.auto_requests,"bad samples confirmed");});
 safetyCase(log,"NEAR_WINDOW_EXPIRED",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.scene("CAT");h.distance=35;h.advance(2600);h.observation_period=900;h.next_observation=c.now+900;h.distance=19;h.advance(2700);check(!h.auto_requests,"outside1.5s confirmed");});
 safetyCase(log,"DUPLICATE_REQUEST",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.arrival("CAT");h.dispense();h.dispatch(h.request_id,false);check(h.successes==1&&h.servo.opens==1,"duplicate reopened");});
 safetyCase(log,"BUSY_REQUEST_PRESERVES_ACTIVE_ID",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.arrival("CAT");const auto original=h.request_id;
   h.mass=1;h.arrival("CAT");check(h.auto_requests==2&&h.request_id==original&&h.feeding&&h.servo.opens==1,"busy request clobbered active feed ID");
   h.dispense();check(h.successes==1&&h.request_id==original,"wrong request completed after busy rejection");});
 safetyCase(log,"PERSISTENCE_FAILURE_NO_OPEN",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.store.fail=true;h.arrival("CAT");check(h.errors==1&&!h.servo.opens&&!h.successes&&h.servo.angle==90,"journal failure opened or succeeded");});
 safetyCase(log,"CAT_NEAR120S_ONE_FEED",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.arrival("CAT");h.dispense();h.advance(120000);check(h.auto_requests==1&&h.successes==1&&h.servo.opens==1,"standing cat refed");});
 safetyCase(log,"COOLDOWN",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.arrival("CAT");h.dispense();h.clearBowl();h.arrival("CAT");check(h.auto_requests==2&&!h.feeding&&h.servo.opens==1,"cooldown bypass");});
 safetyCase(log,"DAILY_PORTIONS",[](Clock& c,Log& l){Harness h(c,l);h.store.record.portions=4;h.controller.boot(h.store.record);h.prepare();h.arrival("CAT");check(!h.feeding&&h.servo.opens==0&&h.controller.reason()==safety::FeedReason::DAILY_PORTIONS,"meal quota bypass");});
 safetyCase(log,"DAILY_GRAMS",[](Clock& c,Log& l){Harness h(c,l);h.store.record.grams=120;h.store.record.portions=3;h.controller.boot(h.store.record);h.prepare();h.arrival("CAT");check(!h.feeding&&!h.servo.opens&&h.controller.reason()==safety::FeedReason::DAILY_GRAMS,"gram quota bypass");});
 safetyCase(log,"HX_NOT_VALIDATED",[](Clock& c,Log& l){Harness h(c,l);h.sim_hx_validated=false;h.prepare();h.arrival("CAT");check(!h.feeding&&!h.servo.opens,"unvalidated HX opened");});
 safetyCase(log,"PRODUCTION_LOCK",[](Clock& c,Log& l){Harness h(c,l,Scope::PRODUCTION_LOCK_TEST);h.prepare();h.arrival("CAT");check(!h.servo.apply(true)&&h.servo.angle==90&&h.servo.opens==0&&!h.feeding,"production scope bypass");});
 for(const std::string mode:{"TIMEOUT","NO_PROGRESS","INVALID","DISCONNECTED","NAN","NEGATIVE","DROP","HUGE","TARE","UART_STALE","AI_STALE","OVERSHOOT"}){
  safetyCase(log,"FEED_"+mode,[&](Clock& c,Log& l){Harness h(c,l);h.prepare();h.arrival("CAT");h.dispense(mode);check(h.errors==1&&h.successes==0&&h.servo.angle==90&&h.servo.opens==1,"failed feed became success: "+mode);});
 }
 safetyCase(log,"MINOR_OVERSHOOT_RECORDED_NOT_FORCED_35",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.arrival("CAT");h.dispense("SMALL_OVERSHOOT");check(h.successes==1&&h.last_actual==35.5,"overshoot was hidden");});
 safetyCase(log,"AI_OFFLINE_BEFORE_REQUEST",[](Clock& c,Log& l){Harness h(c,l);h.ai_fresh=false;h.prepare();h.arrival("CAT");check(!h.auto_requests&&!h.servo.opens,"AI stale opened");});
 safetyCase(log,"UART_STALE_BEFORE_REQUEST",[](Clock& c,Log& l){Harness h(c,l);h.uart_fresh=false;h.prepare();h.arrival("CAT");check(!h.auto_requests&&!h.servo.opens,"UART stale opened");});
 safetyCase(log,"DOG_FAR_25CM",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.scene("DOG");h.distance=35;h.advance(2600);h.distance=25;h.advance(5000);check(!h.warnings_received&&!h.servo.opens,"far DOG warned");});
 safetyCase(log,"DOG_CRC_REJECT",[](Clock& c,Log& l){Harness h(c,l);h.crc_corrupt=true;h.prepare();h.arrival("DOG");h.advance(1000);check(!h.warnings_received&&!h.buzzer_io.lows&&!h.servo.opens,"bad CRC beeped");});
 safetyCase(log,"DOG_COMMAND_EXPIRED",[](Clock& c,Log& l){Harness h(c,l);h.wire_delay=1600;h.prepare();h.arrival("DOG");h.advance(2500);check(!h.warnings_received&&!h.buzzer_io.lows,"expired command beeped");});
 safetyCase(log,"DOG_DUPLICATE_AND_COOLDOWN",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.arrival("DOG");h.advance(800);h.warning();h.advance(500);check(h.warnings_received==1&&h.buzzer_io.lows==2,"duplicate warning repeated");h.arrival("DOG");h.advance(800);check(h.warnings_received==1,"cooldown bypass");h.jump(61000);h.arrival("DOG");h.advance(800);check(h.warnings_received==2&&h.buzzer_io.lows==4,"new eligible warning missing");});
 for(const auto& entry:std::vector<std::pair<double,std::string>>{{0,"DISLIKE"},{5,"DISLIKE"},{5.000001,"UNCERTAIN"},{10,"UNCERTAIN"},{17.999999,"UNCERTAIN"},{18,"LIKE"},{30,"LIKE"},{35,"LIKE"}}){
  safetyCase(log,"PREFERENCE_BOUNDARY_"+number(entry.first),[&](Clock&,Log& l){auto p=preferenceBoundary(entry.first);check(p.ready&&p.valid&&p.classification==entry.second,"preference boundary wrong");
   l.event("PREFERENCE_BOUNDARY_RESULT",{{"consumed",number(p.consumed)},{"classification",quote(p.classification)}});});
 }
 for(const std::string fault:{"NEGATIVE","NAN","INVALID","TARE","UNSTABLE","FUTURE_TIME"}){
  safetyCase(log,"PREFERENCE_"+fault,[&](Clock&,Log& l){const auto p=preferenceBoundary(30,fault);check(p.ready&&!p.valid&&p.classification=="UNCERTAIN","bad observation got preference");l.event("PREFERENCE_INVALID_RESULT",{{"reason",quote(p.reason)}});});
 }
 safetyCase(log,"PREFERENCE_WEIGHT_INCREASE",[](Clock&,Log&){auto p=preferenceBoundary(-1);check(!p.valid&&p.classification=="UNCERTAIN","negative consumption classified");});
 safetyCase(log,"PREFERENCE_STABLE_NOISE",[](Clock&,Log&){auto p=preferenceBoundary(30,"STABLE_NOISE");check(p.valid&&p.classification=="LIKE"&&std::fabs(p.consumed-30)<1e-9,"stable noise misclassified");});
 safetyCase(log,"PREFERENCE_STALE_AND_EMPTY_START",[](Clock&,Log&){Consumption m;std::vector<Weight> start{{35,0,true,1},{35,100,true,1},{35,200,true,1},{35,300,true,1}};
   check(m.begin("STALE",start,300,1,true),"start");check(!m.finish(60300).valid,"stale final samples accepted");
   Consumption empty;for(auto& point:start)point.grams=0;check(!empty.begin("EMPTY",start,300,1,true),"empty starting meal accepted");
   for(auto& point:start)point.grams=35;check(!empty.begin("REAL",start,300,1,false),"non-simulation preference accepted");});
 safetyCase(log,"PREFERENCE_REFILL_UNCERTAIN",[](Clock&,Log&){Consumption m;std::vector<Weight> start{{35,0,true,1},{35,100,true,1},{35,200,true,1},{35,300,true,1}};
   check(m.begin("REFILL",start,300,1,true),"start");for(uint64_t at=600;at<=60300;at+=300)m.observe({at<20000?25.0:at<40000?30.0:5.0,at,true,1},at);
   const auto p=m.finish(60300);check(!p.valid&&p.classification=="UNCERTAIN","food refill counted as consumption");});
 safetyCase(log,"PREFERENCE_60S_AND_GAP",[](Clock&,Log&){Consumption m;std::vector<Weight> start{{35,0,true,1},{35,100,true,1},{35,200,true,1},{35,300,true,1}};check(m.begin("GAP",start,300,1,true),"begin");check(!m.finish(60000).ready,"window ended early");m.observe({5,60300,true,1},60300);auto p=m.finish(60300);check(p.ready&&!p.valid,"gap accepted");});
 safetyCase(log,"CONSUMPTION_ERROR_NEVER_REOPENS_SERVO",[](Clock& c,Log& l){Harness h(c,l);h.prepare();h.arrival("CAT");h.dispense();check(h.beginMeal("ERROR_FOOD"),"observation begin");const auto opened=h.servo.opens;h.sensor_fault=SensorFault::RAW_INVALID;h.advance(60000);check(h.preference_result.ready&&!h.preference_result.valid&&h.servo.opens==opened&&h.successes==1,"invalid consumption refed");});
}
int main(int argc,char** argv){
 if(argc!=3||std::string(argv[1])!="--simulation-only"){std::cerr<<"Usage: e2e_demo --simulation-only FAKE_EPOCH_MS\n";return 2;}
 try{
   Log log(std::stoull(argv[2]));Clock primary("PRIMARY");log.context(primary,"SCENARIO_1_CAT_FEED");
   Harness main(primary,log);runMainDemo(log,primary,main);runSafety(log);
   log.context(primary,"SUMMARY");
   check(main.successes==2&&main.controller.record().portions==2&&main.servo.angle==90,"main end state");
   log.event("E2E_SUITE_COMPLETED",{{"scenario_count","4"},{"safety_cases",integer(safety_cases)},{"assertions",integer(assertions)},
     {"main_successful_simulated_feeds","2"},{"main_simulated_dispensed_grams","70"},{"production_servo",quote("LOCKED")},{"production_pump",quote("LOCKED")}});
   return 0;
 }catch(const std::exception& e){std::cerr<<"E2E_OFFLINE_FAILURE "<<e.what()<<'\n';return 1;}
}
