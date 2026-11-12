#include "feed_policy.h"
#include "telemetry.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
using namespace forcat;
unsigned checks=0;
void check(bool condition){++checks;if(!condition)throw std::runtime_error("check "+std::to_string(checks));}
int main(int argc,char** argv){
 try{
    if(argc!=2)throw std::invalid_argument("fixture required");
    std::ifstream in(argv[1]);std::string fixture((std::istreambuf_iterator<char>(in)),{});
    auto t=parseTelemetry(fixture);check(t.uptime==1000);check(t.has_button);check(t.button_count==0);
    check(text(field(t.normalized.get(),"safety"),"servo_state")=="PWM_NOT_ATTACHED_CLOSE_PHYSICAL_UNVERIFIED");
    check(field(field(field(t.normalized.get(),"sensors"),"hx711"),"grams")==nullptr);
    check(text(field(field(t.normalized.get(),"sensors"),"approach"),"health")=="NOT_CALIBRATED");
    auto invalid=[&](const std::string& value){bool rejected=false;try{parseTelemetry(value);}catch(const std::exception&){rejected=true;}check(rejected);};
    invalid(fixture+" trailing");invalid("{\"mode\":1,\"mode\":2}");invalid("{\"mode\":1,\"mo\\u0064e\":2}");
    invalid(std::string(4097,'x'));invalid("{\"mode\":NaN}");invalid("{broken");
    auto object=own(json_tokener_parse(fixture.c_str()));auto current=field(object.get(),"current_hardware");
    put(current,"servo_armed",true);invalid(encode(object.get()));put(current,"servo_armed",false);
    put(current,"button_pressed",true);invalid(encode(object.get()));put(current,"button_pressed",false);
    put(current,"approach_distance_valid",false);invalid(encode(object.get()));
    LineFramer frame;std::vector<std::string> lines;
    const std::string bytes="first\r\nsecond\n";
    for(char c:bytes)frame.feed(&c,1,[&](const std::string& s){lines.push_back(s);});
    check(lines.size()==2 && lines[0]=="first" && lines[1]=="second");
    std::string large(5000,'x');large+="\nrecovered\n";
    frame.feed(large.data(),large.size(),[&](const std::string& s){lines.push_back(s);});
    check(frame.oversized==1 && lines.back()=="recovered");
    FeedEvidence good;good.weight_calibrated=true;good.telemetry_safe=true;good.near_confirmed_stable=true;
    good.observations_fresh=true;good.species="CAT";
    for(const auto& source:{"AUTO_CAT","MANUAL"}){
        FeedArbiter a(100);auto d=a.evaluate({source,source,"BUTTON",35},good,1000);
        check(d.qualified && !d.actuator_execution && d.reason=="UNATTENDED_SAFE_MODE");
    }
    FeedArbiter a(100);
    auto d=a.evaluate({"schedule","SCHEDULED","",35},good,1000);check(d.qualification_reason=="TIME_INVALID");
    good.time_valid=true;d=a.evaluate({"schedule2","SCHEDULED","",35},good,1000);check(d.qualified && !d.actuator_execution);
    d=a.evaluate({"schedule2","SCHEDULED","",35},good,2000);check(d.qualification_reason=="DUPLICATE_REQUEST");
    d=a.evaluate({"cooldown","MANUAL","APP",35},good,1050);check(d.qualification_reason=="COOLDOWN");
    good.busy=true;d=a.evaluate({"busy","MANUAL","KIOSK",35},good,2000);check(d.qualification_reason=="DISPENSE_BUSY");good.busy=false;
    good.weight_calibrated=false;d=a.evaluate({"uncal","MANUAL","BUTTON",35},good,2000);check(d.qualification_reason=="WEIGHT_NOT_CALIBRATED");good.weight_calibrated=true;
    for(const auto& species:{"DOG","NONE"}){good.species=species;d=a.evaluate({species,"AUTO_CAT","",35},good,3000);check(d.qualification_reason=="AUTO_CAT_EVIDENCE_REQUIRED");}
    good.species="CAT";good.near_confirmed_stable=false;d=a.evaluate({"far","AUTO_CAT","",35},good,3000);check(!d.qualified);
    d=a.evaluate({"oldtarget","MANUAL","BUTTON",40},good,3000);check(d.qualification_reason=="INVALID_REQUEST_OR_TARGET");
    d=a.evaluate({"nan","MANUAL","BUTTON",std::numeric_limits<double>::quiet_NaN()},good,3000);check(!d.qualified);
    d=a.evaluate({"water-ai","DRINKING","",35},good,3000);check(d.qualification_reason=="INVALID_SOURCE" && !d.actuator_execution);
    TimeGate clock;check(!clock.update(1760000000000LL,1000,false));check(clock.update(1760000001000LL,2000,true));
    check(!clock.update(1760001001000LL,3000,true));check(clock.update(1760001002000LL,4000,true));
    check(!clock.update(0,5000,true));
    std::cout<<"C++ policy/parser/framing: "<<checks<<" checks PASS (synthetic; actuator_execution=false)\n";
    return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
