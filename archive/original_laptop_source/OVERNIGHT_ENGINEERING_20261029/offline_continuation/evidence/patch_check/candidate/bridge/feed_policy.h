#pragma once
#include <cmath>
#include <cstdint>
#include <map>
#include <string>

namespace forcat {
constexpr double FEED_TARGET_GRAMS = 35.0;
struct FeedRequest {
    std::string id, source, manual_source;
    double target_grams = FEED_TARGET_GRAMS;
    int64_t requested_at_unix_ms = 0; // Jetson timestamp; TIME_VALID gates SCHEDULED only.
};
struct FeedEvidence {
    bool time_valid=false, weight_calibrated=false, telemetry_safe=false;
    bool busy=false, near_confirmed_stable=false, observations_fresh=false;
    std::string species="NONE";
};
struct FeedDecision {
    bool qualified=false;
    static constexpr bool actuator_execution=false; // No transport/actuator exists in this policy.
    std::string reason="UNATTENDED_SAFE_MODE", qualification_reason;
};
class FeedArbiter {
    std::map<std::string, std::string> seen_;
    bool have_last_=false;
    uint64_t last_=0, cooldown_;
public:
    explicit FeedArbiter(uint64_t cooldown_ms=60000):cooldown_(cooldown_ms) {}
    FeedDecision evaluate(const FeedRequest& r,const FeedEvidence& e,uint64_t now) {
        FeedDecision d;
        if(r.id.empty() || r.id.size()>96 || !std::isfinite(r.target_grams) || r.target_grams!=FEED_TARGET_GRAMS)
            d.qualification_reason="INVALID_REQUEST_OR_TARGET";
        else if(r.source!="AUTO_CAT" && r.source!="SCHEDULED" && r.source!="MANUAL")
            d.qualification_reason="INVALID_SOURCE";
        else if(r.source=="MANUAL" && r.manual_source!="BUTTON" && r.manual_source!="KIOSK" && r.manual_source!="APP")
            d.qualification_reason="INVALID_MANUAL_SOURCE";
        else if(seen_.count(r.id)) d.qualification_reason="DUPLICATE_REQUEST";
        else if(seen_.size()>=4096) d.qualification_reason="REQUEST_LEDGER_FULL";
        else {
            // No eviction/ID reuse in a running arbiter. Diagnostic restart is not
            // durable production duplicate protection; that integration remains blocked.
            seen_.emplace(r.id,r.source+":"+r.manual_source);
            if(r.source=="SCHEDULED" && !e.time_valid) d.qualification_reason="TIME_INVALID";
            else if(r.source=="AUTO_CAT" && (e.species!="CAT" || !e.near_confirmed_stable || !e.observations_fresh))
                d.qualification_reason="AUTO_CAT_EVIDENCE_REQUIRED";
            else if(!e.weight_calibrated) d.qualification_reason="WEIGHT_NOT_CALIBRATED";
            else if(!e.telemetry_safe) d.qualification_reason="TELEMETRY_UNSAFE_OR_STALE";
            else if(e.busy) d.qualification_reason="DISPENSE_BUSY";
            else if(have_last_ && (now<last_ || now-last_<(r.source=="AUTO_CAT" && cooldown_<7200000?7200000:cooldown_))) d.qualification_reason="COOLDOWN";
            else {d.qualified=true;d.qualification_reason="QUALIFIED_DRY_RUN";have_last_=true;last_=now;}
        }
        return d;
    }
};
class TimeGate {
    bool observed_=false, valid_=false;
    int64_t previous_wall_=0;
    uint64_t previous_mono_=0;
public:
    bool update(int64_t wall_ms,uint64_t mono_ms,bool synchronized) {
        bool jump=false;
        if(observed_) jump=mono_ms<previous_mono_ ||
            std::llabs((wall_ms-previous_wall_)-static_cast<int64_t>(mono_ms-previous_mono_))>5000;
        valid_=synchronized && wall_ms>=1735689600000LL && wall_ms<4102444800000LL && !jump;
        observed_=true;previous_wall_=wall_ms;previous_mono_=mono_ms;
        return valid_;
    }
    bool valid() const {return valid_;}
};
} // namespace forcat
