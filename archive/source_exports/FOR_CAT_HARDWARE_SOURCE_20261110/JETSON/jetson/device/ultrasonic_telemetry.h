#pragma once
// Included inside forcat namespace after JSON helpers. Optional ASCII extension;
// legacy schema, safety checks, framing bound and UART/binary protocol unchanged.
inline void parseUltrasonic(json_object* root,json_object* normalized,uint32_t uptime) {
    json_object* channels=nullptr;json_object* version=nullptr;
    const bool present=json_object_object_get_ex(root,"ultrasonic",&channels);
    const bool versioned=json_object_object_get_ex(root,"ultrasonic_schema_version",&version);
    if(!present && !versioned)return;
    if(!present || !versioned || counter(root,"ultrasonic_schema_version")!=1 || !channels ||
       !json_object_is_type(channels,json_type_object) || json_object_object_length(channels)!=4)
        throw std::invalid_argument("ultrasonic extension schema");
    const char* ids[]={"HC_SR04_1","JSN_SR04T_1","HC_SR04_2","JSN_SR04T_2"};
    const char* types[]={"HC-SR04","JSN-SR04T","HC-SR04","JSN-SR04T"};
    const char* roles[]={"CAT_APPROACH","WATER_LEVEL","TBD","TBD"};
    const unsigned trig[]={12,14,16,18},echo[]={13,15,17,10};
    auto out=json_object_new_object();json_object_object_add(normalized,"ultrasonic",out);
    integer(normalized,"ultrasonic_schema_version",1);
    for(unsigned i=0;i<4;++i) {
        auto s=field(channels,ids[i]);
        if(text(s,"type")!=types[i] || text(s,"role")!=roles[i] || counter(s,"trigger_gpio")!=trig[i] || counter(s,"echo_gpio")!=echo[i])
            throw std::invalid_argument("ultrasonic identity/pin mismatch");
        const bool enabled=boolean(s,"enabled"),configured=boolean(s,"configured"),wired=boolean(s,"wired");
        const bool valid=boolean(s,"valid"),timeout=boolean(s,"timeout"),stale=boolean(s,"stale");
        const auto state=text(s,"state");
        if(!std::set<std::string>{"HEALTHY","TIMEOUT","STALE","UNKNOWN","NOT_WIRED","NOT_CONFIGURED","DISABLED"}.count(state))
            throw std::invalid_argument("ultrasonic state");
        double distance=0,last_distance=0;
        const bool value=nullableNumber(s,"distance_cm",distance),history=nullableNumber(s,"last_valid_distance_cm",last_distance);
        auto update=field(s,"last_update"),age=field(s,"sample_age_ms"),last=field(s,"last_valid_update");
        if((update==nullptr)!=(age==nullptr) || (history!=(last!=nullptr)))throw std::invalid_argument("ultrasonic timestamp pair");
        if(update && static_cast<uint32_t>(uptime-counter(s,"last_update"))!=counter(s,"sample_age_ms"))throw std::invalid_argument("ultrasonic age mismatch");
        if(last && static_cast<uint32_t>(uptime-counter(s,"last_valid_update"))>0x7fffffffu)throw std::invalid_argument("ultrasonic future history");
        if(valid!=value || (value && (distance<=0 || distance>400)) || (history && (last_distance<=0 || last_distance>400)))throw std::invalid_argument("ultrasonic distance/validity");
        if(valid && (!enabled || !configured || !wired || timeout || stale || !age || counter(s,"sample_age_ms")>2000 || state!="HEALTHY"))throw std::invalid_argument("ultrasonic invalid healthy value");
        if((state=="HEALTHY")!=valid || (state=="TIMEOUT" && !timeout) || (state=="STALE" && !stale) || (state=="DISABLED" && enabled))throw std::invalid_argument("ultrasonic state/flags");
        counter(s,"timeout_count");
        if(i<2) {
            auto legacy=field(root,"current_hardware");double old_distance=0;
            const bool old_valid=boolean(legacy,i==0?"approach_distance_valid":"operational_water_distance_valid");
            const bool old_value=nullableNumber(root,i==0?"approach_distance_cm":"water_distance_cm",old_distance);
            if(old_valid!=valid || old_value!=value || (valid && std::fabs(old_distance-distance)>.001))throw std::invalid_argument("ultrasonic legacy alias mismatch");
        }
        json_object_object_add(out,ids[i],json_object_get(s));
    }
}
