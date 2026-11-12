// NEW ROI-specific tests only. No Jetson/CUDA/OpenCV/serial/camera dependency.
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <string>
#include <vector>
#include "food_roi.h"
#include "roi_species.h"
#include "approach_fusion.h"
#include "feed_policy.h"
#include "m4/approach_dog_warning.h"
using namespace forcat;
namespace roi=forcat::food_roi;
namespace ad=m4::approach_dog;
unsigned checks=0,cases=0;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"FAIL line%d: %s\n",__LINE__,#x);std::exit(1);}}while(0)
template<class F>void test(const char* name,F body){body();++cases;std::printf("PASS %02u %s\n",cases,name);}
const char* configured="{\"mode\":\"ROI_ENABLED\",\"enabled\":true,\"calibrated\":true,\"review_id\":\"SYNTHETIC_ONLY\",\"x1\":0.25,\"y1\":0.25,\"x2\":0.75,\"y2\":0.75}";
const roi::Box inside{.35,.35,.65,.65},outside{.02,.02,.18,.18};
roi::Relation add(RoiSpecies& scene,bool dog,const roi::Box& b){return scene.box(dog,!dog,.9,b.x1,b.y1,b.x2,b.y2);}
struct FakeIO:m4::PinIO {
 unsigned lows=0,highs=0;
 bool inputAllowed(int p)const override{return p==2;}bool outputAllowed(int p)const override{return p==2;}
 void input(int,m4::Pull)override{}void output(int p)override{CHECK(p==2);}bool read(int)override{return true;}
 void write(int p,bool high)override{CHECK(p==2);if(high)++highs;else++lows;}
 void pauseMicros(uint32_t)override{}void enterCritical()override{}void exitCritical()override{}
};
struct Episode {
 ad::Approach approach;ApproachFusion fusion;FeedArbiter arbiter;FakeIO io;ad::Buzzer buzzer{io};ad::Receiver receiver{approach,buzzer,123};
 uint32_t now=100,seq=0;unsigned auto_requests=0,warnings=0;bool roi_proven=false;
 RoiAiEvidence ai;
 Episode(const roi::Config& cfg,const std::string& species){
   buzzer.begin();uint8_t hello[9]{1};dog_wire::put(hello+1,123);dog_wire::put(hello+5,456);
   CHECK(receiver.receive(1,dog_wire::HELLO,hello,9,now)==ad::ACCEPTED);
   ai.species=species;ai.fresh=true;ai.roi_calibrated=cfg.roiReady();ai.roi_mode=cfg.selection;
   ai.config_valid=cfg.syntax_valid;ai.bbox_available=true;ai.decision_eligible=cfg.decisionAllowed();
 }
 void sample(float distance,bool valid=true){
   now+=500;approach.tick(now);approach.sample(valid,distance,now,now);buzzer.tick(now);
   ai.sequence=++seq;ai.stamp=now;
   ApproachEvidence a{123,456,now,now,approach.event(),approach.eventAt(),approach.valid(),approach.state()==ad::State::CONFIRMED,distance};
   const auto action=fusion.update(a,ai,now);
   if(action==ApproachAction::AUTO_CAT){
     ++auto_requests;roi_proven=ai.roi_mode==roi::Mode::ROI_ENABLED;
     FeedEvidence e;e.species="CAT";e.observations_fresh=e.near_confirmed_stable=e.telemetry_safe=true;
     const auto decision=arbiter.evaluate({"ROI_AUTO_CAT","AUTO_CAT","",35},e,now);
     CHECK(!decision.qualified&&!decision.actuator_execution&&decision.qualification_reason=="WEIGHT_NOT_CALIBRATED");
   }
   if(action==ApproachAction::DOG_WARNING){
     ++warnings;uint8_t p[21]{1};dog_wire::put(p+1,123);dog_wire::put(p+5,456);dog_wire::put(p+9,approach.event());
     dog_wire::put(p+13,approach.eventAt());dog_wire::put(p+17,approach.eventAt()+1500);
     CHECK(receiver.receive(2,dog_wire::WARNING,p,21,now)==ad::ACCEPTED);
   }
 }
 void approachNow(){for(int i=0;i<5;++i)sample(35);sample(19);sample(18);sample(19);}
};
int main(int argc,char** argv){
 test("CAT_inside_IN_ROI",[]{RoiSpecies s(roi::parseConfig(configured),640,480);CHECK(add(s,false,inside)==roi::Relation::IN_ROI&&s.species()=="CAT");});
 test("CAT_outside_OUTSIDE_ROI",[]{RoiSpecies s(roi::parseConfig(configured),640,480);CHECK(add(s,false,outside)==roi::Relation::OUTSIDE_ROI&&s.species()=="NONE");});
 test("DOG_inside_IN_ROI",[]{RoiSpecies s(roi::parseConfig(configured),640,480);CHECK(add(s,true,inside)==roi::Relation::IN_ROI&&s.species()=="DOG");});
 test("DOG_outside_OUTSIDE_ROI",[]{RoiSpecies s(roi::parseConfig(configured),640,480);CHECK(add(s,true,outside)==roi::Relation::OUTSIDE_ROI&&s.species()=="NONE");});
 test("CAT_DOG_inside_blocks_feeding_DOG_priority",[]{auto c=roi::parseConfig(configured);RoiSpecies s(c,640,480);add(s,false,inside);add(s,true,inside);CHECK(s.species()=="DOG");Episode e(c,s.species());e.approachNow();CHECK(e.auto_requests==0&&e.warnings==1);});
 test("touch_sliver_and_large_surrounding_box_not_IN_ROI",[]{auto c=roi::parseConfig(configured);CHECK(roi::evaluate(c,{.10,.35,.25,.65},640,480)==roi::Relation::OUTSIDE_ROI);
   CHECK(roi::evaluate(c,{.10,.35,.251,.65},640,480)==roi::Relation::OUTSIDE_ROI);CHECK(roi::evaluate(c,{0,0,1,1},640,480)==roi::Relation::OUTSIDE_ROI);});
 test("missing_ROI_FULL_FRAME_preserves_classification_no_tray_claim",[]{auto c=roi::parseConfig("{}");CHECK(c.selection==roi::Mode::FULL_FRAME&&c.decisionAllowed()&&!c.roiReady());RoiSpecies s(c,640,480);CHECK(add(s,false,outside)==roi::Relation::FULL_FRAME&&s.species()=="CAT");
   CHECK(roi::parseConfig("").decisionAllowed()&&roi::parseConfig(" \r\n\t").selection==roi::Mode::FULL_FRAME);
   CHECK(!roi::parseConfig("",roi::Mode::ROI_ENABLED).decisionAllowed());
   Episode e(c,s.species());e.approachNow();CHECK(e.auto_requests==1&&!e.roi_proven&&e.warnings==0);});
 test("missing_uncalibrated_ROI_ENABLED_BLOCK",[]{for(const char* value:{"{\"mode\":\"ROI_ENABLED\"}","{\"enabled\":true}","{\"enabled\":true,\"x1\":0.2,\"y1\":0.2,\"x2\":0.8,\"y2\":0.8}"}){
   auto c=roi::parseConfig(value);CHECK(!c.decisionAllowed());RoiSpecies s(c,640,480);CHECK(add(s,true,inside)==roi::Relation::BLOCKED&&s.species()=="UNKNOWN");Episode e(c,s.species());e.approachNow();CHECK(!e.auto_requests&&!e.warnings);}});
 test("invalid_coordinates_bbox_frames_fail_closed",[]{auto c=roi::parseConfig(configured);const double nan=std::numeric_limits<double>::quiet_NaN();
   for(const auto b:{roi::Box{-.1,.2,.5,.5},roi::Box{.2,.2,1.1,.5},roi::Box{.5,.2,.4,.5},roi::Box{.2,.2,.2,.3},roi::Box{nan,.2,.4,.5}}){RoiSpecies s(c,640,480);CHECK(add(s,false,b)==roi::Relation::INVALID&&s.species()=="UNKNOWN");}
   for(const auto dimensions:{std::pair<int,int>{0,480},{640,0},{-1,480},{640,20000}})CHECK(roi::evaluate(c,inside,dimensions.first,dimensions.second)==roi::Relation::INVALID);
   c.roi={.3,.3,.3,.7};CHECK(roi::evaluate(c,inside,640,480)==roi::Relation::BLOCKED);});
 test("original_pixel_and_letterbox_multi_resolution",[]{auto c=roi::parseConfig(configured);
   for(const auto d:{std::pair<int,int>{640,480},{1280,720},{480,640},{641,479}}){const int w=d.first,h=d.second;const roi::Box pixels{w*.35,h*.35,w*.65,h*.65};
     const auto normalized=roi::originalPixels(pixels,w,h);CHECK(normalized.valid&&roi::evaluate(c,normalized.box,w,h)==roi::Relation::IN_ROI);
     const auto t=roi::letterbox(w,h);CHECK(t.valid);
     const roi::Box network{pixels.x1*t.scale+t.pad_x,pixels.y1*t.scale+t.pad_y,pixels.x2*t.scale+t.pad_x,pixels.y2*t.scale+t.pad_y};
     const auto decoded=roi::letterboxedPixels(network,w,h);CHECK(decoded.valid&&roi::evaluate(c,decoded.box,w,h)==roi::Relation::IN_ROI);
     CHECK(std::fabs(decoded.box.x1-.35)<2.0/w&&std::fabs(decoded.box.x2-.65)<2.0/w&&std::fabs(decoded.box.y1-.35)<2.0/h&&std::fabs(decoded.box.y2-.65)<2.0/h);
   }
   const auto landscape=roi::letterbox(640,480);CHECK(landscape.scale==.5f&&landscape.pad_y==40&&landscape.pad_x==0);
   const auto decoded=roi::letterboxedPixels({80,100,160,160},640,480);CHECK(decoded.valid&&decoded.box.x1==.25&&decoded.box.y1==.25&&decoded.box.x2==.5&&decoded.box.y2==.5);
   CHECK(!roi::letterboxedPixels({0,0,20,20},640,480).valid);CHECK(roi::evaluate(c,{100,100,200,200},640,480)==roi::Relation::INVALID);
 });
 test("AI_stale_offline_future_timestamp_blocks",[]{auto c=roi::parseConfig(configured);for(const char* species:{"CAT","DOG","UNKNOWN"}){
   Episode e(c,species);e.ai.fresh=false;e.approachNow();CHECK(!e.auto_requests&&!e.warnings);}
   ApproachFusion f;ApproachEvidence a{123,456,1000,1000,1,1000,true,true,19};RoiAiEvidence ai{"CAT",true,true,1,2501};ai.roi_mode=roi::Mode::ROI_ENABLED;
   CHECK(f.update(a,ai,1000)==ApproachAction::NONE);ai.stamp=0;CHECK(f.update(a,ai,2000)==ApproachAction::NONE);});
 test("ROI_CAT_and_real_shared_approach_AUTO_CAT_DRY_RUN_no_servo",[]{auto c=roi::parseConfig(configured);Episode e(c,"CAT");e.approachNow();for(int i=0;i<2;++i)e.sample(18);CHECK(e.auto_requests==1&&e.roi_proven&&!e.warnings&&e.io.lows==0);});
 test("ROI_DOG_and_shared_approach_warning_logic_fake_IO_only",[]{Episode e(roi::parseConfig(configured),"DOG");e.approachNow();CHECK(e.warnings==1&&!e.auto_requests&&e.io.lows==1);e.buzzer.tick(e.now+200);e.buzzer.tick(e.now+400);e.buzzer.tick(e.now+600);CHECK(e.io.lows==2&&e.buzzer.completed()==1);});
 test("FULL_FRAME_still_requires_distance_temporal_and_NONE_blocks",[]{auto c=roi::parseConfig("{}");Episode e(c,"CAT");for(int i=0;i<10;++i)e.sample(19);CHECK(!e.auto_requests);Episode none(c,"NONE");none.approachNow();CHECK(!none.auto_requests&&!none.warnings);Episode far(c,"DOG");for(int i=0;i<20;++i)far.sample(35);CHECK(!far.warnings);});
 test("explicit_toggle_disabled_invalid_ROI_not_block_FULL_FRAME",[]{auto c=roi::parseConfig("{\"mode\":\"ROI_ENABLED\",\"enabled\":false,\"calibrated\":false,\"x1\":2,\"x2\":-1}");CHECK(c.selection==roi::Mode::FULL_FRAME&&c.decisionAllowed());
   CHECK(roi::parseConfig(configured,roi::Mode::FULL_FRAME).decisionAllowed());CHECK(!roi::parseConfig("{}",roi::Mode::ROI_ENABLED).decisionAllowed());});
 test("configuration_JSON_type_duplicate_escape_size_validation",[]{for(const char* json:{"{", "[]","{\"enabled\":\"false\"}","{\"mode\":\"BAD\"}","{\"enabled\":false,\"enabled\":true}","{\"enabeld\":true}","{\"x1\":NaN}","{\"x1\":1e309}","{\"enabled\":true,\"width\":1.5}","{\"x1\":01}","{} trailing"})CHECK(!roi::parseConfig(json).syntax_valid);
   CHECK(!roi::parseConfig(std::string(4097,' ')).syntax_valid);CHECK(roi::parseConfig("{\"review_id\":\"\\u0053YNTHETIC\"}").review_id=="SYNTHETIC");
   CHECK(!roi::parseConfig("{\"review_id\":\"\\ud800\"}").syntax_valid);CHECK(roi::parseConfig("{\"enabled\":false,\"x1\":null}").decisionAllowed());});
 test("legacy_missing_bbox_only_FULL_FRAME_never_fabricates_ROI",[]{CHECK(roi::evidenceAllowed(roi::Mode::FULL_FRAME,roi::Mode::FULL_FRAME,true,false,false,true));
   CHECK(!roi::evidenceAllowed(roi::Mode::ROI_ENABLED,roi::Mode::FULL_FRAME,true,false,false,true));CHECK(!roi::evidenceAllowed(roi::Mode::ROI_ENABLED,roi::Mode::ROI_ENABLED,true,true,false,true));
   CHECK(!roi::evidenceAllowed(roi::Mode::FULL_FRAME,roi::Mode::ROI_ENABLED,true,true,true,true));
   Episode e(roi::parseConfig("{}"),"CAT");e.ai.bbox_available=false;e.approachNow();CHECK(e.auto_requests==1&&!e.roi_proven);
   Episode enabled(roi::parseConfig(configured),"CAT");enabled.ai.bbox_available=false;enabled.approachNow();CHECK(!enabled.auto_requests&&!enabled.warnings);
 });
 test("invalid_DOG_bbox_never_leaves_valid_CAT_feed_eligible",[]{RoiSpecies s(roi::parseConfig(configured),640,480);add(s,false,inside);add(s,true,{-.1,.1,.9,.9});CHECK(s.species()=="UNKNOWN"&&!s.eligible());});
 test("same_normalized_ROI_supports_resolution_change",[]{auto c=roi::parseConfig(configured);c.reference_width=640;c.reference_height=480;for(const auto d:{std::pair<int,int>{320,240},{640,480},{1280,960},{1920,1080}})CHECK(roi::evaluate(c,inside,d.first,d.second)==roi::Relation::IN_ROI);});
 test("disabled_ROI_bad_calibration_metadata_does_not_block_FULL_FRAME",[]{auto c=roi::parseConfig("{\"enabled\":false,\"calibrated\":\"bad\",\"review_id\":null,\"camera_device\":12,\"width\":-1,\"height\":1.5,\"x1\":2}");CHECK(c.decisionAllowed()&&c.selection==roi::Mode::FULL_FRAME);RoiSpecies scene(c,640,480);add(scene,true,outside);CHECK(scene.species()=="DOG");});
 test("ROI_camera_binding_only_when_enabled",[]{auto c=roi::parseConfig(configured);c.camera_device="CAMERA_A";CHECK(c.compatibleCamera("CAMERA_A")&&!c.compatibleCamera("CAMERA_B"));c.selection=roi::Mode::FULL_FRAME;CHECK(c.compatibleCamera("CAMERA_B"));});
 test("bad_network_bounds_and_zero_resize_dimension_INVALID",[]{CHECK(!roi::letterboxedPixels({-1,100,160,160},640,480).valid);CHECK(!roi::letterboxedPixels({1,1,321,319},640,480).valid);CHECK(!roi::letterbox(16384,2,2,2).valid);});
 test("existing_hardware_constants_unchanged",[]{CHECK(ad::APPROACH_ENTER_CM==20&&ad::APPROACH_RELEASE_CM==30&&ad::MIN_VALID_APPROACH_CM==5);
   CHECK(ad::ENTER_CONFIRM_SAMPLES==3&&ad::ENTER_CONFIRM_WINDOW_MS==1500&&ad::RELEASE_CONFIRM_MS==2000);
   CHECK(ad::BUZZER_GPIO==2&&ad::BUZZER_ACTIVE_LOW&&ad::BUZZER_BEEP_COUNT==2&&ad::BUZZER_ON_MS==200&&ad::BUZZER_OFF_GAP_MS==200&&ad::BUZZER_COOLDOWN_MS==60000&&FEED_TARGET_GRAMS==35);});
 test("all_public_default_modes_are_FULL_FRAME",[]{CHECK(roi::Config{}.selection==roi::Mode::FULL_FRAME);CHECK(RoiAiEvidence{}.roi_mode==roi::Mode::FULL_FRAME);});
 test("bounded_config_parser_random_bad_input_no_crash",[]{uint32_t random=123;for(int n=0;n<500;++n){std::string s;for(int j=0;j<n%80;++j){random=random*1664525u+1013904223u;s+=static_cast<char>(32+(random%95));}auto c=roi::parseConfig(s);CHECK(!c.syntax_valid||c.selection==roi::Mode::FULL_FRAME||c.selection==roi::Mode::ROI_ENABLED);}});
 if(argc>=3)test("actual_default_config_file_is_FULL_FRAME",[&]{std::ifstream file(argv[2]);const std::string text((std::istreambuf_iterator<char>(file)),{});CHECK(file.good()||file.eof());auto c=roi::parseConfig(text);CHECK(c.syntax_valid&&c.selection==roi::Mode::FULL_FRAME&&c.decisionAllowed()&&!c.roiReady());});
 if(argc>=4)test("image_tool_JSON_export_parses_in_actual_Cpp_loader",[&]{auto c=roi::parseConfig(argv[3]);CHECK(c.roiReady()&&c.roi.x1==.25&&c.roi.y1==.25&&c.roi.x2==.75&&c.roi.y2==.75);});
 if(argc>=2){std::ofstream visual(argv[1]);
   for(const char* label:{"CAT_IN","CAT_OUT","DOG_IN","DOG_OUT","MIXED","EDGE_TOUCH","FULL_FRAME","UNCONFIGURED_ENABLED"}){
     std::string name=label;auto c=name=="FULL_FRAME"?roi::parseConfig("{}"):name=="UNCONFIGURED_ENABLED"?roi::parseConfig("{\"enabled\":true}"):roi::parseConfig(configured);
     const auto b=name=="CAT_OUT"||name=="DOG_OUT"?outside:name=="EDGE_TOUCH"?roi::Box{.1,.35,.25,.65}:inside;
     RoiSpecies scene(c,640,480);const bool dog=name.find("DOG")==0;auto relation=add(scene,dog,b);if(name=="MIXED")add(scene,true,inside);
     visual<<"{\"synthetic\":true,\"label\":\""<<name<<"\",\"mode\":\""<<roi::name(c.selection)<<"\",\"relation\":\""<<roi::name(relation)<<"\",\"classification\":\""<<scene.species()<<"\",\"bbox\":["<<b.x1<<','<<b.y1<<','<<b.x2<<','<<b.y2<<"]}\n";
   }
 }
 std::printf("ROI_OFFLINE_PASS cases=%u assertions=%u fake_clock=true synthetic_bbox=true hardware=false\n",cases,checks);
}
