#pragma once
// Shared by the POSIX executable and the portable CLI contract probe.
struct Options {
    std::string device="auto",usb_serial,db="jetson/data/events.db",log="evidence/esp32_bridge.jsonl";
    unsigned baud=115200,stale_ms=3000,reconnect_ms=2000,seconds=0;
    NearConfig near;
    bool dog_warning=false,live_serial=false;
    bool feed_link=false;
    std::string feed_outbox,feed_review,live_confirmation;
    FirmwarePolicy firmware_policy=FirmwarePolicy::KIT_QUAD_ONLY;
    food_roi::Mode roi_mode=food_roi::Mode::FULL_FRAME;
    WaterConfig water;
};
inline unsigned argument(const std::string& value,unsigned low,unsigned high){
    size_t end=0;auto n=std::stoul(value,&end);if(end!=value.size() || n<low || n>high)throw std::invalid_argument("numeric option out of range");return static_cast<unsigned>(n);
}
inline double distanceArgument(const std::string& value){size_t end=0;double n=std::stod(value,&end);if(end!=value.size() || !std::isfinite(n) || n<=0 || n>400)throw std::invalid_argument("distance option out of range");return n;}
inline Options options(int argc,char** argv){
    Options o;
    for(int i=1;i<argc;++i){std::string k=argv[i];if(i+1==argc)throw std::invalid_argument("option needs value");std::string v=argv[++i];
        if(k=="--device")o.device=v;else if(k=="--usb-serial")o.usb_serial=v;else if(k=="--db")o.db=v;
        else if(k=="--log")o.log=v;else if(k=="--baud")o.baud=argument(v,9600,230400);
        else if(k=="--stale-ms")o.stale_ms=argument(v,500,60000);else if(k=="--reconnect-ms")o.reconnect_ms=argument(v,100,30000);
        else if(k=="--seconds")o.seconds=argument(v,1,86400);
        else if(k=="--dog-warning")o.dog_warning=argument(v,0,1)!=0;
        else if(k=="--live-serial"){o.live_confirmation=v;o.live_serial=true;}
        else if(k=="--feed-link"){if(v!="OWNER_REVIEWED_V1")throw std::invalid_argument("explicit feed-link review required");o.feed_link=true;}
        else if(k=="--feed-outbox")o.feed_outbox=v;
        else if(k=="--feed-review")o.feed_review=v;
        else if(k=="--firmware-profile"){
            if(v=="diag_four_ultrasonic")o.firmware_policy=FirmwarePolicy::KIT_QUAD_ONLY;
            else if(v=="legacy_current_hardware")o.firmware_policy=FirmwarePolicy::LEGACY_CURRENT_HARDWARE;
            else if(v=="diag_manual_station")o.firmware_policy=FirmwarePolicy::MANUAL_STATION_READ_ONLY;
            else if(v=="diag_dual_station")o.firmware_policy=FirmwarePolicy::DUAL_STATION_READ_ONLY;
            else if(v=="feed_link_v1")o.firmware_policy=FirmwarePolicy::FEED_LINK_ONLY;
            else throw std::invalid_argument("explicit supported firmware profile required");
        }
        else if(k=="--roi-mode"){o.roi_mode=food_roi::mode(v);if(o.roi_mode==food_roi::Mode::INVALID)throw std::invalid_argument("ROI mode must be FULL_FRAME or ROI_ENABLED");}
        else if(k=="--near-cm")o.near.distance_cm=distanceArgument(v);
        else if(k=="--near-stable-ms")o.near.stable_ms=argument(v,100,10000);
        else if(k=="--water-low-cm")o.water.low_distance_cm=distanceArgument(v);
        else if(k=="--water-target-cm")o.water.target_distance_cm=distanceArgument(v);
        else throw std::invalid_argument("unknown option "+k);
    }
    if(o.baud!=9600 && o.baud!=57600 && o.baud!=115200 && o.baud!=230400)throw std::invalid_argument("unsupported baud");
    if(o.dog_warning)throw std::invalid_argument("DIAGNOSTIC_CANDIDATE_IS_READ_ONLY_NO_DOG_OR_ACTUATOR_TX");
    if(o.feed_link && (o.feed_outbox.empty() || o.feed_review.empty() ||
       (o.firmware_policy!=FirmwarePolicy::FEED_LINK_ONLY && o.firmware_policy!=FirmwarePolicy::DUAL_STATION_READ_ONLY)))throw std::invalid_argument("feed-link requires explicit compatible profile/outbox/review");
    if(o.live_serial && o.live_confirmation!=(o.feed_link?"OWNER_APPROVED_SINGLE_OWNER_FEED_LINK":"OWNER_SUPERVISED_READ_ONLY"))throw std::invalid_argument("serial access scope mismatch");
    if((o.water.low_distance_cm || o.water.target_distance_cm) && !o.water.configured())throw std::invalid_argument("water requires reviewed LOW > TARGET > 0 geometry");
    return o;
}
