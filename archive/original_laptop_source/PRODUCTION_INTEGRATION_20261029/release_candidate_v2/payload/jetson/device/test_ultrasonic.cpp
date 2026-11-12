#include "telemetry.h"
#include <fstream>
#include <iostream>
#include <iterator>
using namespace forcat;
unsigned checks=0;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("u4 check "+std::to_string(checks));}
int main(int argc,char** argv){
 try{
  if(argc!=2)return 2;
  std::ifstream in(argv[1]);std::string fixture((std::istreambuf_iterator<char>(in)),{});
  auto old=parseTelemetry(fixture);json_object* absent=nullptr;check(!json_object_object_get_ex(old.normalized.get(),"ultrasonic",&absent));
  auto root=own(json_tokener_parse(fixture.c_str()));integer(root.get(),"ultrasonic_schema_version",1);
  auto channels=json_object_new_object();json_object_object_add(root.get(),"ultrasonic",channels);
  const char* ids[]={"HC_SR04_1","JSN_SR04T_1","HC_SR04_2","JSN_SR04T_2"};
  const int trig[]={12,14,16,18},echo[]={13,15,17,10};
  for(unsigned i=0;i<4;++i){auto s=json_object_new_object();json_object_object_add(channels,ids[i],s);
   put(s,"type",i%2?"JSN-SR04T":"HC-SR04");put(s,"role",i==0?"CAT_APPROACH":i==1?"WATER_LEVEL":"TBD");integer(s,"trigger_gpio",trig[i]);integer(s,"echo_gpio",echo[i]);
   for(auto k:{"enabled","configured","wired","valid"})put(s,k,true);
   put(s,"timeout",false);put(s,"stale",false);put(s,"state","HEALTHY");number(s,"distance_cm",true,30+i*10);
   integer(s,"sample_age_ms",0);integer(s,"last_update",1000);integer(s,"last_valid_update",1000);number(s,"last_valid_distance_cm",true,30+i*10);integer(s,"timeout_count",0);
  }
  number(root.get(),"approach_distance_cm",true,30);number(root.get(),"water_distance_cm",true,40);
  auto normalized=parseTelemetry(encode(root.get()));auto u=field(normalized.normalized.get(),"ultrasonic");
  for(unsigned i=0;i<4;++i){double v=0;check(nullableNumber(field(u,ids[i]),"distance_cm",v)&&v==30+i*10);}
  const auto valid_json=encode(root.get());
  auto rejects=[&](const std::string& value){bool caught=false;try{parseTelemetry(value);}catch(const std::exception&){caught=true;}check(caught);};
  for(auto bad:{"{\"ultrasonic\":null}","{broken"})rejects(bad);
  auto mutate=[&](const char* key,json_object* value){auto r=own(json_tokener_parse(valid_json.c_str()));json_object_object_add(field(field(r.get(),"ultrasonic"),"HC_SR04_2"),key,value);rejects(encode(r.get()));};
  mutate("distance_cm",json_object_new_double(0));mutate("distance_cm",nullptr);mutate("enabled",json_object_new_boolean(false));mutate("timeout",json_object_new_boolean(true));
  mutate("echo_gpio",json_object_new_int(6));mutate("sample_age_ms",json_object_new_int(1));mutate("last_valid_update",nullptr);mutate("state",json_object_new_string("PHYSICAL_PASS"));
  integer(root.get(),"ultrasonic_schema_version",2);rejects(encode(root.get()));
  auto missing=own(json_tokener_parse(valid_json.c_str()));json_object_object_del(field(missing.get(),"ultrasonic"),"HC_SR04_2");rejects(encode(missing.get()));
  auto failed=own(json_tokener_parse(valid_json.c_str()));auto s=field(field(failed.get(),"ultrasonic"),"HC_SR04_2");
  put(s,"valid",false);number(s,"distance_cm",false,0);put(s,"timeout",true);put(s,"state","TIMEOUT");integer(s,"timeout_count",2);
  auto t=parseTelemetry(encode(failed.get()));check(field(field(field(t.normalized.get(),"ultrasonic"),"HC_SR04_2"),"distance_cm")==nullptr);
  double retained=0;check(nullableNumber(field(field(t.normalized.get(),"ultrasonic"),"HC_SR04_2"),"last_valid_distance_cm",retained)&&retained==50);
  std::cout<<"ULTRASONIC4 SOFTWARE_READY "<<checks<<" checks; legacy preserved, no GPIO\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
