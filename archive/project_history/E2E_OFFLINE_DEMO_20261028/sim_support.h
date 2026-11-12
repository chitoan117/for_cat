#pragma once
#if defined(ARDUINO) || defined(ESP_PLATFORM)
#error "Offline demo must never be built as embedded firmware"
#endif
#include <cmath>
#include <cstdint>
#include <deque>
#include <iomanip>
#include <iostream>
#include <locale>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include "roi_species.h"
#include "approach_fusion.h"
#include "feed_policy.h"
#include "m4/hx711.h"
#include "m4/approach_dog_warning.h"
#include "safety_logic.h"
#include "simulation_preference.h"

namespace offline_demo {
using Fields=std::vector<std::pair<std::string,std::string>>;
inline std::string quote(const std::string& s){std::ostringstream out;out<<'"';for(unsigned char c:s){
 if(c=='"'||c=='\\')out<<'\\'<<c;else if(c<32)out<<"\\u00"<<std::hex<<std::setw(2)<<std::setfill('0')<<static_cast<unsigned>(c)<<std::dec;else out<<c;
 }out<<'"';return out.str();}
inline std::string number(double n){if(!std::isfinite(n))return "null";std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(15)<<n;return out.str();}
inline std::string integer(uint64_t n){return std::to_string(n);}
inline std::string hexBytes(const uint8_t* data,size_t size){std::ostringstream out;out<<std::hex<<std::setfill('0');for(size_t i=0;i<size;++i)out<<std::setw(2)<<static_cast<unsigned>(data[i]);return out.str();}
struct Clock {uint64_t now=0;std::string domain;explicit Clock(std::string name):domain(std::move(name)){};};
struct Log {
 uint64_t sequence=0,epoch_ms;Clock* clock=nullptr;std::string scenario;
 explicit Log(uint64_t epoch):epoch_ms(epoch){}
 void context(Clock& c,const std::string& label){clock=&c;scenario=label;}
 void event(const std::string& kind,const Fields& data={}){
   if(!clock)throw std::runtime_error("missing fake clock");
   std::cout<<"{\"seq\":"<<++sequence<<",\"mode\":\"SIMULATION\",\"simulation\":true,\"production_actuator_execution\":false,\"physical_hx711_pass\":false,\"clock_domain\":"<<quote(clock->domain)
    <<",\"scenario\":"<<quote(scenario)<<",\"fake_ms\":"<<clock->now<<",\"timestamp_unix_ms\":"<<epoch_ms+clock->now<<",\"kind\":"<<quote(kind);
   for(const auto& p:data)std::cout<<','<<quote(p.first)<<':'<<p.second;
   std::cout<<'}'<<std::endl;
 }
};
inline void require(bool ok,const std::string& why){if(!ok)throw std::runtime_error(why);}
enum class Scope {SIMULATION,PRODUCTION_LOCK_TEST};
struct FakeServo {
 Log& log;Scope scope;int angle=90;unsigned opens=0,closes=0;
 FakeServo(Log& l,Scope s):log(l),scope(s){}
 bool apply(bool open){
   if(open&&scope!=Scope::SIMULATION){log.event("SIMULATION_CAPABILITY_REJECTED",{{"reason",quote("PRODUCTION_SCOPE_CANNOT_OPEN_FAKE_DISPATCH")}});return false;}
   const int wanted=open?45:90;if(wanted!=angle){angle=wanted;if(open)++opens;else++closes;
     log.event("SIMULATED_SERVO",{{"angle_degrees",integer(static_cast<unsigned>(angle))},{"state",quote(open?"OPEN":"CLOSED")},{"gpio_access",quote("NONE_FAKE_OBJECT_ONLY")}});}
   return true;
 }
};
struct FakeHxPins final:m4::PinIO {
 std::deque<bool> bits;unsigned conversions=0;
 bool inputAllowed(int p)const override{return p==4;}bool outputAllowed(int p)const override{return p==5;}
 void input(int p,m4::Pull)override{require(p==4,"fake HX input pin");}void output(int p)override{require(p==5,"fake HX output pin");}
 bool read(int p)override{require(p==4,"fake HX DOUT");if(bits.empty())return true;const bool bit=bits.front();bits.pop_front();return bit;}
 void write(int p,bool)override{require(p==5,"fake HX SCK");}void pauseMicros(uint32_t)override{}void enterCritical()override{}void exitCritical()override{}
 void raw(int32_t value){require(bits.empty(),"unconsumed fake ADC bits");bits.push_back(false);for(int n=23;n>=0;--n)bits.push_back((static_cast<uint32_t>(value)>>n)&1u);++conversions;}
};
struct FakeBuzzerPins final:m4::PinIO {
 Log& log;unsigned lows=0,highs=0;explicit FakeBuzzerPins(Log& l):log(l){}
 bool inputAllowed(int p)const override{return p==2;}bool outputAllowed(int p)const override{return p==2;}
 void input(int,m4::Pull)override{}void output(int p)override{require(p==2,"buzzer cannot configure servo/pump");}
 bool read(int)override{return true;}
 void write(int p,bool high)override{require(p==2,"DOG_WARNING only touches fake GPIO2");if(high)++highs;else++lows;
   log.event("SIMULATED_BUZZER_EDGE",{{"gpio",integer(2)},{"level",quote(high?"HIGH":"LOW")},{"audible_state",quote(high?"OFF":"ON")},{"active_low","true"},{"vcc_nominal_volts","3.3"}});}
 void pauseMicros(uint32_t)override{}void enterCritical()override{}void exitCritical()override{}
};
struct FakeDailyStore:safety::DailyStore {
 safety::DailyRecord record;Log& log;bool fail=false;
 explicit FakeDailyStore(Log& l):log(l){record.day=20261028;}
 bool save(const safety::DailyRecord& next)override{if(fail)return false;record=next;
   log.event("SIMULATED_DAILY_LEDGER",{{"day",integer(next.day)},{"portions",integer(next.portions)},{"grams",number(next.grams)},{"needs_inspection",next.needs_inspection?"true":"false"}});return true;}
};
inline const char* reason(safety::FeedReason r){switch(r){
 case safety::FeedReason::NONE:return "NONE";case safety::FeedReason::BUSY:return "BUSY";
 case safety::FeedReason::DAILY_PORTIONS:return "DAILY_PORTIONS";case safety::FeedReason::DAILY_GRAMS:return "DAILY_GRAMS";
 case safety::FeedReason::COOLDOWN:return "COOLDOWN";case safety::FeedReason::TIMEOUT:return "TIMEOUT";
 case safety::FeedReason::NO_PROGRESS:return "NO_PROGRESS";case safety::FeedReason::INVALID_WEIGHT:return "INVALID_WEIGHT";
 case safety::FeedReason::HX711_FAULT:return "HX711_FAULT";case safety::FeedReason::PERSISTENCE_FAULT:return "PERSISTENCE_FAULT";
 case safety::FeedReason::SAFE_MODE:return "SAFE_MODE";case safety::FeedReason::RTC_INVALID:return "RTC_INVALID";
 case safety::FeedReason::FOOD_EMPTY:return "FOOD_EMPTY";case safety::FeedReason::SERVO_FAULT:return "SERVO_FAULT";
 case safety::FeedReason::CLOSE_FAILURE:return "CLOSE_FAILURE";default:return "TARGET_OUT_OF_RANGE";}}
struct Detection {std::string species;double confidence=.9;forcat::food_roi::Box box{.35,.35,.65,.65};};
enum class SensorFault {NONE,RAW_INVALID,DISCONNECTED,INVALID_NUMBER,TARE_CHANGED};
struct PendingWire {uint64_t delivery=0;std::vector<uint8_t> bytes;};

class Harness {
 public:
 Clock& clock;Log& log;Scope scope;
 FakeHxPins hx_io;m4::Hx711 hx{hx_io};FakeServo servo;FakeDailyStore store;
 safety::FeedController controller;
 FakeBuzzerPins buzzer_io;m4::approach_dog::Buzzer buzzer;
 m4::approach_dog::Approach approach; m4::approach_dog::Receiver receiver;dog_wire::Parser parser;
 forcat::ApproachFusion fusion;forcat::FeedArbiter arbiter;
 forcat::food_roi::Config roi_config;
 Consumption meal;
 std::vector<Detection> detections;std::vector<Weight> settled,closing;
 std::deque<PendingWire> packets;
 double mass=0,distance=35,baseline=0,last_actual=0,dispense_peak=0,empty_container_gross=0;
 bool enforce_empty_container=false,distance_valid=true,ai_fresh=true,uart_fresh=true,sim_hx_validated=true;
 bool crc_corrupt=false,feeding=false,feed_success=false,meal_reported=false;
 SensorFault sensor_fault=SensorFault::NONE;uint32_t generation=1,feed_generation=1,ai_seq=0,wire_id=1;
 unsigned auto_requests=0,warning_attempts=0,warnings_received=0,successes=0,errors=0;uint64_t next_observation=0,wire_delay=0,observation_period=500;
 std::string request_id,food_name="FOOD_A",last_error;std::string last_species="NONE";
 uint32_t boot_nonce=123,link_token=456;
 static safety::FeedPolicy policy(){safety::FeedPolicy p;p.cooldown_seconds=7200;return p;}
 Harness(Clock& c,Log& l,Scope s=Scope::SIMULATION):clock(c),log(l),scope(s),servo(l,s),store(l),controller(policy()),
   buzzer_io(l),buzzer(buzzer_io),receiver(approach,buzzer,123){
   static_assert(!forcat::FeedDecision::actuator_execution,"production arbiter must never enable hardware");
   roi_config=forcat::food_roi::parseConfig("{}");
   require(hx.begin({{4,true},{5,true},500},static_cast<uint32_t>(clock.now)),"fake HX begin");
   hx.applyCalibration({true,true,1000000,0.001}); // SYNTHETIC calibration, never real NVS
   controller.attachStore(store);controller.boot(store.record);buzzer.begin();
   uint8_t hello[9]{1};dog_wire::put(hello+1,boot_nonce);dog_wire::put(hello+5,link_token);send(dog_wire::HELLO,hello,9,false,0);deliver();
   log.event("SIMULATION_BOUNDARY",{{"production_servo","\"LOCKED\""},{"production_pump","\"LOCKED\""},{"hx_validation",quote("SIMULATED_ONLY_PHYSICAL_PENDING")},{"daily_max_portions",integer(policy().max_daily_portions)},{"daily_max_grams",number(policy().max_daily_grams)}});
 }
 ~Harness(){if(servo.angle!=90){servo.apply(false);log.event("SIMULATION_TEARDOWN_CLOSE",{{"success_claimed","false"}});}}
 bool active()const{const auto s=controller.state();return s==safety::FeedState::PRECHECK||s==safety::FeedState::DISPENSING||s==safety::FeedState::CLOSING;}
 bool weightValid()const{return sensor_fault!=SensorFault::INVALID_NUMBER&&hx.signed_grams.valid&&std::isfinite(hx.signed_grams.value)&&std::fabs(hx.signed_grams.value)<=1500&&clock.now>=hx.signed_grams.sampled_at_ms&&clock.now-hx.signed_grams.sampled_at_ms<600;}
 void scene(const std::string& species){detections.clear();if(species=="CAT"||species=="DOG")detections.push_back({species,.9,{.35,.35,.65,.65}});}
 void send(uint8_t command,const uint8_t* payload,uint16_t n,bool corrupt,uint64_t delay,uint32_t fixed_id=0){
   uint8_t bytes[uart_v1::MAX_FRAME];size_t count=0;
   require(uart_v1::encode(fixed_id?fixed_id:++wire_id,command,payload,n,bytes,sizeof(bytes),count),"wire encode");
   if(corrupt)bytes[count-1]^=1;
   packets.push_back({clock.now+delay,std::vector<uint8_t>(bytes,bytes+count)});
   log.event("UART_SIMULATED_TX",{{"command",integer(command)},{"request_id_wire",integer(fixed_id?fixed_id:wire_id)},{"crc_corrupt_injected",corrupt?"true":"false"},{"delivery_ms",integer(clock.now+delay)},{"frame_hex",quote(hexBytes(bytes,count))}});
 }
 void deliver(){while(!packets.empty()&&packets.front().delivery<=clock.now){auto p=packets.front();packets.pop_front();bool callback=false;
   for(auto byte:p.bytes)parser.feed(byte,static_cast<uint32_t>(clock.now),[&](uint32_t id,uint8_t cmd,const uint8_t* payload,uint16_t n){
     callback=true;const auto result=receiver.receive(id,cmd,payload,n,static_cast<uint32_t>(clock.now));
     if(cmd==dog_wire::WARNING&&result==m4::approach_dog::ACCEPTED){++warnings_received;log.event("DOG_WARNING",{{"status",quote("SIMULATED_RECEIVED_SEQUENCE_STARTED")},{"receipt_only_not_completion","true"}});}
     log.event("UART_SIMULATED_ACK",{{"request_id_wire",integer(id)},{"command",integer(cmd)},{"result_code",integer(result)},{"receipt_only_not_completion","true"}});
   });
   if(!callback)log.event("UART_FRAME_REJECTED_NO_EFFECT",{{"crc_validation",quote("NO_VALID_CALLBACK")}});
 }}
 void warning(){++warning_attempts;uint8_t p[21]{1};dog_wire::put(p+1,boot_nonce);dog_wire::put(p+5,link_token);
   dog_wire::put(p+9,approach.event());dog_wire::put(p+13,approach.eventAt());dog_wire::put(p+17,approach.eventAt()+1500);
   send(dog_wire::WARNING,p,21,crc_corrupt,wire_delay);
 }
 void inputObservation(){
   forcat::RoiSpecies classified(roi_config,640,480);
   for(const auto& d:detections)classified.box(d.species=="DOG",d.species=="CAT",d.confidence,d.box.x1,d.box.y1,d.box.x2,d.box.y2);
   std::string input_boxes="[";for(size_t i=0;i<detections.size();++i){const auto& d=detections[i];if(i)input_boxes+=',';
     input_boxes+="{\"species\":"+quote(d.species)+",\"confidence\":"+number(d.confidence)+",\"bbox\":["+number(d.box.x1)+','+number(d.box.y1)+','+number(d.box.x2)+','+number(d.box.y2)+"]}";
   }input_boxes+=']';
   last_species=classified.species();
   log.event("SIMULATED_CAMERA_DETECTION",{{"classification",quote(last_species)},{"roi_mode",quote(forcat::food_roi::name(roi_config.selection))},
      {"bbox_source",quote("SYNTHETIC_NORMALIZED_ORIGINAL")},{"detections",input_boxes},{"frame_width","640"},{"frame_height","480"},
      {"tray_membership_proven",roi_config.selection==forcat::food_roi::Mode::ROI_ENABLED&&classified.detected()?"true":"false"},
      {"detections_count",integer(detections.size())},{"ai_fresh",ai_fresh?"true":"false"},{"roi_decision_eligible",classified.eligible()?"true":"false"}});
   const auto now=static_cast<uint32_t>(clock.now);const bool fired=approach.sample(distance_valid,static_cast<float>(distance),now,now);
   log.event("SIMULATED_APPROACH_SAMPLE",{{"distance_cm",distance_valid?number(distance):"null"},{"raw_distance_valid",distance_valid?"true":"false"},
     {"sample_ms",integer(now)},{"valid_for_approach",approach.valid()?"true":"false"},{"state",quote(m4::approach_dog::name(approach.state()))},{"approach_event_id",integer(approach.event())},{"new_confirmation",fired?"true":"false"}});
   forcat::RoiAiEvidence ai{last_species,ai_fresh,roi_config.roiReady(),++ai_seq,clock.now};
   ai.roi_mode=roi_config.selection;ai.config_valid=roi_config.syntax_valid;ai.bbox_available=true;ai.decision_eligible=classified.eligible();
   forcat::ApproachEvidence a{boot_nonce,link_token,now,now,approach.event(),approach.eventAt(),approach.valid(),approach.state()==m4::approach_dog::State::CONFIRMED,distance};
   if(!uart_fresh){log.event("UART_STALE_BLOCK",{{"action",quote("NONE")}});return;}
   const auto action=fusion.update(a,ai,clock.now);
   if(action==forcat::ApproachAction::AUTO_CAT){++auto_requests;const auto candidate=clock.domain+"_AUTO_"+std::to_string(auto_requests);dispatch(candidate,true);}
   if(action==forcat::ApproachAction::DOG_WARNING)warning();
 }
 safety::FeedInputs inputs()const{
   safety::FeedInputs in;in.now_ms=static_cast<uint32_t>(clock.now);in.epoch_seconds=(log.epoch_ms+clock.now)/1000;in.day=20261028;
   in.rtc_valid=true;in.food_available=true;in.scale=weightValid()?safety::Health::OK:safety::Health::FAULT;
   in.servo=safety::Health::OK;in.measured_grams=hx.signed_grams.valid?hx.signed_grams.value:0;
   in.servo_closed=servo.angle==90;
   if(controller.state()==safety::FeedState::CLOSING){double value=0;in.servo_closed=servo.angle==90&&stable(closing,clock.now,generation,value);
     if(in.servo_closed)in.measured_grams=static_cast<float>(value);}
   return in;
 }
 void dispatch(const std::string& id,bool generated){
   if(generated)log.event("AUTO_CAT_REQUEST",{{"request_id",quote(id)},{"source",quote("AUTO_CAT")},{"target_grams","35"},{"food_name",quote(food_name)}});
   forcat::FeedEvidence e;e.species=last_species;e.observations_fresh=ai_fresh&&uart_fresh;e.near_confirmed_stable=approach.state()==m4::approach_dog::State::CONFIRMED;
   e.telemetry_safe=uart_fresh;e.busy=active()||meal.active();e.weight_calibrated=scope==Scope::SIMULATION&&sim_hx_validated&&weightValid();
   const auto d=arbiter.evaluate({id,"AUTO_CAT","",35,static_cast<int64_t>(log.epoch_ms+clock.now)},e,clock.now);
   log.event("ARBITER_DECISION",{{"request_id",quote(id)},{"qualified",d.qualified?"true":"false"},{"qualification_reason",quote(d.qualification_reason)},
       {"production_policy_actuator_execution","false"},{"hx_validation_scope",quote(scope==Scope::SIMULATION?"SIMULATED_VALIDATED":"PHYSICAL_PENDING")}});
   if(!d.qualified||scope!=Scope::SIMULATION){log.event("SIM_DISPATCH_BLOCKED",{{"request_id",quote(id)},{"reason",quote(d.qualification_reason)}});return;}
   if(enforce_empty_container){double empty=0;if(!stable(settled,clock.now,generation,empty)||std::fabs(empty-empty_container_gross)>.2){
     log.event("SIM_DISPATCH_BLOCKED",{{"request_id",quote(id)},{"reason",quote("BOWL_NOT_EMPTY_OR_BASELINE_SHIFT")}});return;
   }}
   auto in=inputs();const bool accepted=controller.request(++control_id_,35,in);
   if(!accepted||controller.state()!=safety::FeedState::PRECHECK){log.event("SIM_DISPATCH_BLOCKED",{{"request_id",quote(id)},{"reason",quote(reason(controller.reason()))}});return;}
   request_id=id;feeding=true;feed_success=false;last_error.clear();baseline=in.measured_grams;dispense_peak=0;feed_generation=generation;closing.clear();
   log.event("SIM_DISPENSE_STARTED",{{"request_id",quote(id)},{"baseline_grams",number(baseline)},{"target_grams","35"},{"validation_authority",quote("FAKE_SENSOR_ONLY")}});
 }
 void step(){
   clock.now+=100;const auto now=static_cast<uint32_t>(clock.now);
   if(sensor_fault!=SensorFault::DISCONNECTED){
     int32_t raw=0;
     const double counts=1000000+mass*1000;
     if(sensor_fault!=SensorFault::RAW_INVALID&&std::isfinite(counts)&&counts>-8388608&&counts<8388607)raw=static_cast<int32_t>(std::llround(counts));
     hx_io.raw(raw);
   }
   hx.poll(now);approach.tick(now);buzzer.tick(now);deliver();
   if(clock.now>=next_observation){inputObservation();next_observation=clock.now+observation_period;}
   if(hx.signed_grams.fresh){
     const Weight point{hx.signed_grams.value,clock.now,weightValid(),generation};
     settled.push_back(point);if(settled.size()>4)settled.erase(settled.begin());
     if(controller.state()==safety::FeedState::CLOSING){closing.push_back(point);if(closing.size()>4)closing.erase(closing.begin());}
     log.event("SIMULATED_HX711",{{"request_id",quote(request_id)},{"raw_counts",hx.raw.valid?number(hx.raw.value):"null"},
       {"measurement_grams",point.valid?number(point.grams):"null"},{"valid",point.valid?"true":"false"},{"tare_generation",integer(generation)}});
     if(meal.active())meal.observe({point.grams-baseline,point.at,point.valid,point.generation},clock.now);
   }
   auto in=inputs();
   if(active()){
     std::string fault;
     if(!uart_fresh)fault="UART_STALE";else if(!ai_fresh||last_species!="CAT")fault="AI_NOT_FRESH_CAT";
     else if(generation!=feed_generation||sensor_fault==SensorFault::TARE_CHANGED)fault="CALIBRATION_OR_TARE_CHANGED";
     else if(sensor_fault==SensorFault::INVALID_NUMBER)fault="INVALID_NUMBER";
     else if(!weightValid())fault="HX711_INVALID_OR_TIMEOUT";
     else if(in.measured_grams-baseline>35.7)fault="OVERSHOOT_TARGET_BAND";
     else if(in.measured_grams<baseline-0.2)fault="NEGATIVE_OR_DROPPED_WEIGHT";
     else if(controller.state()==safety::FeedState::DISPENSING&&in.measured_grams-baseline+0.7<dispense_peak)fault="WEIGHT_DROP_DURING_DISPENSE";
     if(in.scale==safety::Health::OK&&in.measured_grams-baseline>dispense_peak)dispense_peak=in.measured_grams-baseline;
     if(!fault.empty()){last_error=fault;in.scale=safety::Health::FAULT;}
   }
   const auto previous=controller.state();controller.tick(in);
   require(servo.apply(controller.openRequested()),"production scope attempted simulator opening");
   if(previous!=safety::FeedState::CLOSING&&controller.state()==safety::FeedState::CLOSING)closing.clear();
   if(feeding&&controller.state()==safety::FeedState::COMPLETE){
     feeding=false;feed_success=true;++successes;last_actual=in.measured_grams-baseline;
     log.event("FEED_COMPLETED",{{"request_id",quote(request_id)},{"food_name",quote(food_name)},{"status",quote("SIMULATION_SUCCESS")},
       {"actual_dispensed_grams",number(last_actual)},{"daily_portions",integer(controller.record().portions)},{"daily_grams",number(controller.record().grams)}});
   }
   if(feeding&&controller.state()==safety::FeedState::FAULT){
     feeding=false;feed_success=false;++errors;
     if(last_error.empty())last_error=reason(controller.reason());
     log.event("FEED_ERROR",{{"request_id",quote(request_id)},{"reason",quote(last_error)},{"controller_reason",quote(reason(controller.reason()))},
       {"actual_dispensed_grams",weightValid()?number(hx.signed_grams.value-baseline):"null"},{"servo_closed",servo.angle==90?"true":"false"}});
   }
   if(meal.active()){
     if(!weightValid())meal.invalidate("SENSOR_INVALID_OR_STALE");
     if(generation!=feed_generation)meal.invalidate("CALIBRATION_OR_TARE_CHANGED");
     auto result=meal.finish(clock.now);if(result.ready&&!meal_reported){meal_reported=true;preference_result=result;
       log.event("MEAL_PREFERENCE",{{"request_id",quote(request_id)},{"food_name",quote(result.food)},
         {"starting_mass",number(result.starting)},{"remaining_mass",result.valid?number(result.remaining):"null"},
         {"consumed_mass",result.valid?number(result.consumed):"null"},{"classification",quote(result.classification)},
         {"reason",quote(result.reason)},{"observation_started_ms",integer(result.started_at)},{"observation_finished_ms",integer(result.finished_at)},
         {"weight_evidence",quote("SIMULATED_NOT_ANIMAL_BEHAVIOR")}});
     }
   }
 }
 void advance(uint64_t ms){require(ms%100==0,"step interval100ms");for(uint64_t n=0;n<ms;n+=100)step();}
 void jump(uint64_t ms){require(!active()&&!meal.active()&&!buzzer.active(),"fake jump only while quiescent");clock.now+=ms;approach.tick(static_cast<uint32_t>(clock.now));
   log.event("FAKE_CLOCK_ADVANCE",{{"advanced_ms",integer(ms)},{"wall_sleep_ms","0"}});}
 void arrival(const std::string& animal){scene(animal);distance=35;advance(2600);distance=19;advance(500);distance=18;advance(500);distance=19;advance(500);}
 void prepare(){scene("NONE");distance=35;advance(1500);}
 void dispense(const std::string& mode="NORMAL"){
   const auto until=clock.now+25000;uint64_t open_at=0;double initial_added=0;
   while(feeding&&clock.now<until){
     if(servo.angle==45){if(!open_at){open_at=clock.now;initial_added=std::max(0.0,mass-baseline);}const double seconds=(clock.now-open_at)/1000.0;
       if(mode=="NORMAL")mass=baseline+std::min(35.0,initial_added+seconds*10);
       else if(mode=="OVERSHOOT")mass=baseline+36;
       else if(mode=="SMALL_OVERSHOOT")mass=baseline+35.5;
       else if(mode=="TIMEOUT")mass=baseline+seconds*.1;
       else if(mode=="INVALID")sensor_fault=SensorFault::RAW_INVALID;
       else if(mode=="DISCONNECTED")sensor_fault=SensorFault::DISCONNECTED;
       else if(mode=="NAN"){mass=std::numeric_limits<double>::quiet_NaN();sensor_fault=SensorFault::INVALID_NUMBER;}
       else if(mode=="NEGATIVE")mass=baseline-1;
       else if(mode=="DROP")mass=baseline+(seconds<1?5:1);
       else if(mode=="HUGE")mass=1e12;
       else if(mode=="TARE"){++generation;sensor_fault=SensorFault::TARE_CHANGED;}
       else if(mode=="UART_STALE")uart_fresh=false;
       else if(mode=="AI_STALE")ai_fresh=false;
     }
     step();
   }
   require(!feeding,"simulated dispensing failed to terminate");
 }
 bool beginMeal(const std::string& food){
   if(!feed_success||servo.angle!=90||feeding)return false;
   std::vector<Weight> net=settled;for(auto& s:net)s.grams-=baseline;
   const bool ok=meal.begin(food,net,clock.now,generation,scope==Scope::SIMULATION);
   if(ok){meal_reported=false;feed_generation=generation;log.event("CONSUMPTION_OBSERVATION_STARTED",{{"food_name",quote(food)},
       {"request_id",quote(request_id)},{"starting_mass",number(last_actual)},{"duration_ms","60000"}});}
   return ok;
 }
  void clearBowl(){require(!active()&&!meal.active(),"no bowl reset during dispense/consumption");mass=empty_container_gross;sensor_fault=SensorFault::NONE;
   log.event("SIMULATED_BOWL_CLEARED_BETWEEN_MEALS",{{"food_mass",number(mass)}});advance(1500);}
 Preference preference_result;
 private:uint32_t control_id_=0;
};
} // namespace offline_demo
