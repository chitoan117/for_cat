#pragma once
#include <json-c/json.h>
#include <json-c/json_tokener.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace forcat {
using Json=std::shared_ptr<json_object>;
inline Json own(json_object* p) {return Json(p,[](json_object* x){if(x)json_object_put(x);});}
inline json_object* field(json_object* o,const char* k) {
    json_object* v=nullptr;
    if(!o || !json_object_is_type(o,json_type_object) || !json_object_object_get_ex(o,k,&v))
        throw std::invalid_argument(std::string("missing field: ")+k);
    return v;
}
inline bool boolean(json_object* o,const char* k) {
    auto v=field(o,k);if(!v || !json_object_is_type(v,json_type_boolean)) throw std::invalid_argument(k);
    return json_object_get_boolean(v)!=0;
}
inline std::string text(json_object* o,const char* k) {
    auto v=field(o,k);if(!v || !json_object_is_type(v,json_type_string))throw std::invalid_argument(k);
    return json_object_get_string(v);
}
inline uint32_t counter(json_object* o,const char* k) {
    auto v=field(o,k);
    if(!v || !json_object_is_type(v,json_type_int) || json_object_get_int64(v)<0 ||
       json_object_get_int64(v)>UINT32_MAX)throw std::invalid_argument(k);
    return static_cast<uint32_t>(json_object_get_int64(v));
}
inline bool nullableNumber(json_object* o,const char* k,double& out) {
    auto v=field(o,k);if(!v)return false;
    if((!json_object_is_type(v,json_type_int) && !json_object_is_type(v,json_type_double)) ||
       !std::isfinite(json_object_get_double(v)))throw std::invalid_argument(k);
    out=json_object_get_double(v);return true;
}
inline void put(json_object* o,const char* k,const std::string& v) {json_object_object_add(o,k,json_object_new_string(v.c_str()));}
inline void put(json_object* o,const char* k,const char* v) {put(o,k,std::string(v));}
inline void put(json_object* o,const char* k,bool v) {json_object_object_add(o,k,json_object_new_boolean(v));}
inline void integer(json_object* o,const char* k,int64_t v) {json_object_object_add(o,k,json_object_new_int64(v));}
inline void number(json_object* o,const char* k,bool valid,double v) {json_object_object_add(o,k,valid?json_object_new_double(v):nullptr);}
inline void copy(json_object* to,const char* k,json_object* from,const char* source) {
    auto v=field(from,source);json_object_object_add(to,k,v?json_object_get(v):nullptr);
}
inline std::string encode(json_object* o) {return json_object_to_json_string_ext(o,JSON_C_TO_STRING_PLAIN);}
#include "ultrasonic_telemetry.h"

// json-c's permissive duplicate-key overwrite is unsuitable for safety telemetry.
// Inspect decoded object keys before normal parsing; arrays and escaped keys work.
inline void rejectDuplicateKeys(const std::string& s) {
    struct Scope {bool object;bool key;std::set<std::string> names;};
    std::vector<Scope> scopes;
    for(size_t i=0;i<s.size();++i) {
        char c=s[i];
        if(c=='"') {
            const size_t start=i++;
            for(;i<s.size();++i) {if(s[i]=='\\'){++i;continue;}if(s[i]=='"')break;}
            if(i>=s.size())throw std::invalid_argument("unterminated string");
            if(!scopes.empty() && scopes.back().object && scopes.back().key) {
                auto key=own(json_tokener_parse(s.substr(start,i-start+1).c_str()));
                if(!key || !json_object_is_type(key.get(),json_type_string) ||
                   !scopes.back().names.insert(json_object_get_string(key.get())).second)
                    throw std::invalid_argument("duplicate JSON key");
                scopes.back().key=false;
            }
        } else if(c=='{' || c=='[') {
            if(scopes.size()>=16)throw std::invalid_argument("JSON depth limit");
            scopes.push_back({c=='{',c=='{',{}});
        } else if(c=='}' || c==']') {
            if(scopes.empty())throw std::invalid_argument("bad JSON scope");
            scopes.pop_back();
        } else if(c==',' && !scopes.empty() && scopes.back().object) scopes.back().key=true;
    }
}
struct UnsafeTelemetry:std::runtime_error {using std::runtime_error::runtime_error;};
#include "manual_telemetry.h"
struct Telemetry {
    Json normalized;
    uint32_t uptime=0,button_count=0;
    bool has_button=false;
};
constexpr size_t TELEMETRY_MAX_LINE=8192;
enum class FirmwarePolicy { KIT_QUAD_ONLY, LEGACY_CURRENT_HARDWARE, MANUAL_STATION_READ_ONLY };
inline bool healthKnown(const std::string& s) {
    static const std::set<std::string> values={"NOT_CONFIGURED","NOT_CONNECTED","NOT_CALIBRATED","INITIALIZING","HEALTHY","DEGRADED","FAULT"};
    return values.count(s)!=0;
}
inline Telemetry parseTelemetry(const std::string& line,FirmwarePolicy policy=FirmwarePolicy::KIT_QUAD_ONLY) {
    if(line.empty() || line.size()>TELEMETRY_MAX_LINE || line.find('\0')!=std::string::npos)throw std::invalid_argument("line bound");
    rejectDuplicateKeys(line);
    auto tok=json_tokener_new_ex(16);
    json_tokener_set_flags(tok,JSON_TOKENER_STRICT);
    auto root=own(json_tokener_parse_ex(tok,line.c_str(),static_cast<int>(line.size())));
    const auto error=json_tokener_get_error(tok);const auto end=tok->char_offset;json_tokener_free(tok);
    if(error!=json_tokener_success || !root || !json_object_is_type(root.get(),json_type_object) ||
       line.find_first_not_of(" \t\r\n",static_cast<size_t>(end))!=std::string::npos)throw std::invalid_argument("malformed JSON");
    auto r=root.get();const auto mode=text(r,"mode");
    const bool manual=mode=="diag_manual_station";
    if((manual && policy!=FirmwarePolicy::MANUAL_STATION_READ_ONLY) ||
       (!manual && (mode!="diag_current_hardware" || policy==FirmwarePolicy::MANUAL_STATION_READ_ONLY)))
        throw std::invalid_argument("unsupported firmware mode for explicit profile");
    if(!boolean(r,"hx711_installed"))throw std::invalid_argument("current profile must acquire installed HX711");
    auto current=field(r,"current_hardware");
    // Unsafe state is separately latched by the bridge and closes serial. No TX.
    if(manual)validateManualStation(r,current);
    else {
    if(counter(r,"actuator_outputs_enabled")!=0 || boolean(r,"physical_pump_on") ||
       boolean(current,"servo_armed") || boolean(current,"pump_armed") ||
       boolean(current,"auto_feed") || boolean(current,"auto_water"))throw UnsafeTelemetry("ACTUATOR_SAFETY_VIOLATION");
    if(text(current,"servo_state")!="PWM_NOT_ATTACHED_CLOSE_PHYSICAL_UNVERIFIED" ||
        text(current,"pump_state")!="OUTPUT_NOT_ENABLED_PHYSICAL_OFF_UNVERIFIED")throw UnsafeTelemetry("UNEXPECTED_ACTUATOR_MODE");
    }
    if(boolean(r,"hardware_verified"))throw std::invalid_argument("unreviewed validation claim");
    // The released image genuinely emits this legacy wire mode. Identify its
    // actual diagnostic profile separately; NEVER rewrite a HX/reference mode.
    json_object* profile_field=nullptr;
    const bool has_profile=json_object_object_get_ex(r,"kit_profile",&profile_field);
    const bool kit=manual || has_profile || policy==FirmwarePolicy::KIT_QUAD_ONLY;
    if(kit && !manual){
        if(text(r,"kit_profile")!="diag_four_ultrasonic" || text(r,"kit_firmware_id")!="FORCAT_PHYSICAL_KIT_20261029_V1" ||
           counter(r,"telemetry_schema_version")!=2 || counter(r,"ultrasonic_schema_version")!=1 ||
           text(r,"rtc_type")!="NONE" || boolean(current,"rtc_detected") || boolean(r,"voltage_physically_verified"))
            throw std::invalid_argument("unrecognized quad diagnostic identity/schema");
        if(!field(r,"ultrasonic") || !field(r,"weight") || !field(current,"manual_button_request_count"))
            throw std::invalid_argument("quad diagnostic required sensors");
        json_object* manual=nullptr;
        if(json_object_object_get_ex(r,"manual_buzzer_capability",&manual))throw UnsafeTelemetry("UNEXPECTED_BUZZER_CAPABILITY_IN_SENSOR_ONLY_IMAGE");
    }
    Telemetry result;result.uptime=counter(r,"monotonic_ms");
    auto n=own(json_object_new_object());result.normalized=n;
    put(n.get(),"mode",mode);integer(n.get(),"monotonic_ms",result.uptime);
    put(n.get(),"wire_mode",mode);put(n.get(),"diagnostic_profile",manual?"diag_manual_station":kit?"diag_four_ultrasonic":"legacy_current_hardware");
    put(n.get(),"diagnostic_claim_is_physical_acceptance",false);
    auto sensors=json_object_new_object();json_object_object_add(n.get(),"sensors",sensors);
    for(auto pair: {std::pair<const char*,const char*>{"oled","oled_health"},{"hx711","weight_health"},
                    {"approach","approach_health"},{"water_operational","water_health"}}) {
        auto h=text(r,pair.second);if(!healthKnown(h))throw std::invalid_argument("unknown health");
        auto sensor=json_object_new_object();json_object_object_add(sensors,pair.first,sensor);
        put(sensor,"health",h);put(sensor,"configured",h!="NOT_CONFIGURED");
        put(sensor,"physical_verification","NOT_EVALUATED_BY_BRIDGE");
    }
    auto oled=field(sensors,"oled");
    const auto address=text(current,"oled_address");
    if(address!="0x3c" || (kit && boolean(current,"rtc_detected")))throw std::invalid_argument("OLED/RTC contract");
    put(oled,"address",address);put(oled,"initialized",boolean(current,"oled_initialized"));
    auto pir=json_object_new_object();json_object_object_add(sensors,"pir",pir);
    const bool configured=boolean(r,"motion_input_configured");put(pir,"configured",configured);
    if(configured)put(pir,"motion",boolean(r,"motion"));else if(field(r,"motion"))throw std::invalid_argument("unconfigured PIR value");
    else json_object_object_add(pir,"motion",nullptr);
    const auto transitions=counter(current,"pir_transition_count");
    integer(pir,"transition_count",transitions);
    auto pir_stamp=field(current,"pir_last_transition_ms");
    if((transitions==0)!=(pir_stamp==nullptr))throw std::invalid_argument("PIR timestamp/count mismatch");
    if(pir_stamp)counter(current,"pir_last_transition_ms");
    copy(pir,"last_transition_ms",current,"pir_last_transition_ms");
    put(pir,"physical_verification","NOT_EVALUATED_BY_BRIDGE");
    json_object* qualified=nullptr;
    if(json_object_object_get_ex(r,"motion_valid",&qualified)){
        const bool valid=boolean(r,"motion_valid");const auto quality=text(r,"motion_quality");
        if(!std::set<std::string>{"VALID","WARMING_UP","SETTLING","NOT_CONFIGURED"}.count(quality) ||
           valid!=(quality=="VALID") || (valid && !configured))throw std::invalid_argument("qualified PIR state");
        auto stable=field(r,"motion_stable");
        if(valid)put(pir,"motion_stable",boolean(r,"motion_stable"));
        else if(stable)throw std::invalid_argument("unqualified PIR value");
        else json_object_object_add(pir,"motion_stable",nullptr);
        put(pir,"motion_valid",valid);put(pir,"motion_quality",quality);put(pir,"qualified_fields_available",true);
    }else {if(kit)throw std::invalid_argument("quad diagnostic requires qualified PIR fields");put(pir,"qualified_fields_available",false);}
    for(auto role: {"approach","water_operational"}) {
        const bool approach=std::string(role)=="approach";
        auto sensor=field(sensors,role);
        const bool valid=boolean(current,approach?"approach_distance_valid":"operational_water_distance_valid");
        double distance=0;const bool present=nullableNumber(r,approach?"approach_distance_cm":"water_distance_cm",distance);
        if(valid!=present || (valid && (distance<=0 || distance>400)))throw std::invalid_argument("distance/validity mismatch");
        put(sensor,"distance_valid",valid);number(sensor,"distance_cm",valid,distance);
        integer(sensor,"timeout_count",counter(current,approach?"approach_timeout_count":"operational_water_timeout_count"));
        const bool ack=boolean(r,approach?"approach_echo_ack":"water_echo_ack");
        if(valid && !ack)throw std::invalid_argument("unacknowledged channel has valid distance");
        put(sensor,"echo_ack",ack);
    }
    auto hx=field(sensors,"hx711");double raw=0;const bool raw_valid=nullableNumber(r,"raw_counts",raw);
    if(raw_valid && (raw<=-8388608 || raw>=8388607 || raw==0 || raw==-1))throw std::invalid_argument("HX invalid signed24 raw sentinel/range");
    number(hx,"raw_counts",raw_valid,raw);put(hx,"raw_available",raw_valid);
    put(hx,"firmware_calibrated",boolean(current,"weight_calibrated"));
    // Tonight's canonical gram calibration is DEFERRED. No raw->gram conversion.
    json_object_object_add(hx,"grams",nullptr);put(hx,"gram_calibration","DEFERRED_PENDING_PHYSICAL_REFERENCE");
    // Read-only observation; do NOT authorize feed or migrate host calibration.
    json_object* fw_weight=nullptr;
    if(json_object_object_get_ex(r,"weight",&fw_weight)){
        if(kit && !boolean(fw_weight,"installed"))throw std::invalid_argument("quad diagnostic missing HX installation");
        const bool valid=boolean(fw_weight,"valid");double grams=0;
        const bool present=nullableNumber(fw_weight,"value_grams",grams);
        if(valid!=present || (present && std::fabs(grams)>1000))throw std::invalid_argument("firmware weight observation");
        bool recent=false;
        if(valid){
            if(!boolean(fw_weight,"installed") || !boolean(current,"weight_calibrated") || counter(fw_weight,"calibration_version")!=1 || text(fw_weight,"calibration_id").empty())throw std::invalid_argument("firmware weight calibration context");
            recent=static_cast<uint32_t>(result.uptime-counter(fw_weight,"sampled_at_ms"))<=1500;
        }
        put(hx,"firmware_observation_valid",valid && recent);number(hx,"firmware_value_grams",valid && recent,grams);
        integer(hx,"firmware_age_at_frame_ms",valid?static_cast<uint32_t>(result.uptime-counter(fw_weight,"sampled_at_ms")):0);
        if(valid)copy(hx,"firmware_calibration_id",fw_weight,"calibration_id");
        else json_object_object_add(hx,"firmware_calibration_id",nullptr);
        put(hx,"firmware_measurement_authority","OBSERVATION_ONLY_NOT_FEED_AUTHORITY");
    }
    json_object* kit_id=nullptr;
    if(json_object_object_get_ex(r,"kit_firmware_id",&kit_id)){
        const auto id=text(r,"kit_firmware_id");if(id.empty() || id.size()>128)throw std::invalid_argument("kit identity bound");
        put(n.get(),"kit_firmware_id",id);copy(n.get(),"kit_profile",r,"kit_profile");
    }
    auto safety=json_object_new_object();json_object_object_add(n.get(),"safety",safety);
    for(auto key:{"servo_armed","pump_armed","auto_feed","auto_water"})put(safety,key,boolean(current,key));
    copy(safety,"servo_state",current,"servo_state");copy(safety,"pump_state",current,"pump_state");
    integer(safety,"actuator_outputs_enabled",0);put(safety,"actuator_execution",false);
    auto buzzer=json_object_new_object();json_object_object_add(sensors,"buzzer",buzzer);
    integer(buzzer,"gpio",2);put(buzzer,"polarity","ACTIVE_LOW");put(buzzer,"capability",false);
    put(buzzer,"state","UNAVAILABLE_SENSOR_ONLY_IMAGE");put(buzzer,"state_is_wire_observation",false);
    put(buzzer,"physical_off_verified",false);
    if(manual)normalizeManualStation(r,n.get(),safety,sensors);
    for(auto role:{"food_reservoir","water_reservoir"}) {
        auto sensor=json_object_new_object();json_object_object_add(sensors,role,sensor);
        put(sensor,"health","NOT_WIRED");put(sensor,"configured",false);
        json_object_object_add(sensor,"percent",nullptr);
    }
    json_object* optional=nullptr;
    result.has_button=json_object_object_get_ex(current,"manual_button_request_count",&optional);
    if(kit && !result.has_button)throw std::invalid_argument("quad diagnostic requires GPIO21 button");
    if(result.has_button) {
        result.button_count=counter(current,"manual_button_request_count");
        if(result.button_count!=counter(current,"button_press_count") || counter(current,"button_gpio")!=21 ||
           counter(current,"button_debounce_ms")<30 || counter(current,"button_debounce_ms")>50 ||
           !boolean(current,"button_actuator_blocked"))throw std::invalid_argument("button contract");
        auto button=json_object_new_object();json_object_object_add(sensors,"button",button);
        const auto h=text(r,"button_health");if(!healthKnown(h))throw std::invalid_argument("button health");put(button,"health",h);
        integer(button,"request_count",result.button_count);
        for(auto key:{"button_raw_level","button_debounced_level"}) {
            auto value=counter(current,key);if(value>1)throw std::invalid_argument("button level");integer(button,key,value);
        }
        const bool pressed=boolean(current,"button_pressed");put(button,"pressed",pressed);
        if(pressed==(counter(current,"button_debounced_level")!=0))throw std::invalid_argument("button active LOW mismatch");
        copy(button,"last_press_ms",current,"button_last_press_ms");
        auto stamp=field(current,"button_last_press_ms");
        if((result.button_count==0)!=(stamp==nullptr))throw std::invalid_argument("button timestamp/count mismatch");
        if(stamp)counter(current,"button_last_press_ms");
        if(stamp && static_cast<uint32_t>(result.uptime-counter(current,"button_last_press_ms"))>0x7fffffffu)throw std::invalid_argument("button future timestamp");
        put(button,"physical_verification","NOT_YET_VERIFIED");
        put(button,"state_source","TELEMETRY");integer(button,"state_device_ms",result.uptime);
    }
    parseUltrasonic(r,n.get(),result.uptime);
    return result;
}
class LineFramer {
    std::string line_;bool dropping_=false;
public:
    uint64_t oversized=0;
    template<class F> void feed(const char* data,size_t count,F emit) {
        for(size_t i=0;i<count;++i) {
            char c=data[i];if(c=='\n' || c=='\r') {
                if(!dropping_ && !line_.empty())emit(line_);
                line_.clear();dropping_=false;
            } else if(!dropping_) {
                if(line_.size()==TELEMETRY_MAX_LINE){line_.clear();dropping_=true;++oversized;}
                else line_.push_back(c);
            }
        }
    }
    void clear() {line_.clear();dropping_=false;}
};
} // namespace forcat
