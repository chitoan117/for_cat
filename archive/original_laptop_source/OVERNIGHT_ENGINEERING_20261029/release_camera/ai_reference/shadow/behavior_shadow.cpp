#include "behavior_shadow.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>

namespace behavior_shadow {
namespace {
void require(bool ok, const char* message) { if (!ok) throw std::invalid_argument(message); }
bool unit(double n) { return std::isfinite(n) && n >= 0 && n <= 1; }
double area(const Box& b) { return (b.x2 - b.x1) * (b.y2 - b.y1); }
double intersection(const Box& a, const Box& b) {
    return std::max(0.0, std::min(a.x2, b.x2) - std::max(a.x1, b.x1)) *
           std::max(0.0, std::min(a.y2, b.y2) - std::max(a.y1, b.y1));
}
Point center(const Box& b) { return {(b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2}; }
double distance(Point a, Point b) { return std::hypot(a.x - b.x, a.y - b.y); }
double distance_to_box(Point p, const Box& b) {
    return std::hypot(std::max({b.x1 - p.x, 0.0, p.x - b.x2}),
                      std::max({b.y1 - p.y, 0.0, p.y - b.y2}));
}
void validate_tracker(const TrackerConfig& c) {
    require(unit(c.min_confidence) && c.min_confidence > 0, "invalid detector confidence");
    require(unit(c.min_iou) && c.min_iou > 0, "invalid IoU gate");
    require(unit(c.max_centroid_distance) && c.max_centroid_distance > 0, "invalid centroid gate");
    require(c.ttl_ms > 0 && c.ttl_ms <= 600000, "invalid tracker TTL");
    require(c.history_capacity >= 2 && c.history_capacity <= 512, "history capacity must be 2..512");
}
void validate_detections(const std::vector<Detection>& detections) {
    require(detections.size() <= 1024, "detection input budget exceeded");
    for (const auto& d : detections) {
        require(d.object == Object::Cat || d.object == Object::Dog || d.object == Object::Other,
                "invalid object type");
        require(unit(d.confidence) && valid_box(d.box), "invalid detection confidence/bbox");
    }
}
Roi behavior_roi(Behavior b) { return b == Behavior::Eating ? Roi::Food : Roi::Water; }
State active_state(Behavior b) { return b == Behavior::Eating ? State::Eating : State::Drinking; }
State candidate_state(Behavior b) {
    return b == Behavior::Eating ? State::ConfirmingEating : State::ConfirmingDrinking;
}
Millis bounded_deadline(Millis start, Millis delta) {
    return start > std::numeric_limits<Millis>::max() - delta ? std::numeric_limits<Millis>::max() : start + delta;
}
} // namespace

bool valid_box(const Box& b) {
    return unit(b.x1) && unit(b.y1) && unit(b.x2) && unit(b.y2) && b.x1 < b.x2 && b.y1 < b.y2 && area(b) > 0;
}
double intersection_over_union(const Box& a, const Box& b) {
    require(valid_box(a) && valid_box(b), "invalid IoU boxes");
    const double overlap = intersection(a, b);
    return overlap / (area(a) + area(b) - overlap);
}
Point bbox_bottom_center(const Box& b) { return {(b.x1 + b.x2) / 2, b.y2}; }
void validate_config(const Config& c) {
    validate_tracker(c.tracker);
    const auto& g = c.geometry;
    require(valid_box(g.food_roi) && valid_box(g.water_roi), "food/water ROI must have normalized positive area");
    require(intersection(g.food_roi, g.water_roi) == 0, "food/water ROI overlap is ambiguous");
    require(unit(g.near_distance) && unit(g.exit_distance) && g.exit_distance >= g.near_distance,
            "invalid ROI hysteresis distances");
    require(unit(g.min_body_overlap) && g.min_body_overlap > 0, "invalid minimum body overlap");
    require(unit(g.min_motion_per_second) && g.min_motion_per_second > 0, "invalid motion threshold");
    require(g.motion_window_ms > 0 && g.motion_window_ms <= 600000, "invalid motion window");
    require(g.approach_line_start.present == g.approach_line_end.present, "incomplete approach line");
    if (g.approach_line_start.present) {
        const auto a = g.approach_line_start.value, b = g.approach_line_end.value;
        require(unit(a.x) && unit(a.y) && unit(b.x) && unit(b.y) && distance(a,b) > 0,
                "invalid normalized approach line");
    }
    const auto& t = c.temporal;
    for (auto ms : {t.confirm_ms, t.dropout_ms, t.min_state_ms, t.max_observation_gap_ms, t.max_behavior_age_ms})
        require(ms > 0 && ms <= 600000, "temporal durations must be 1..600000 ms");
    require(t.max_observation_gap_ms <= c.tracker.ttl_ms, "observation gap exceeds tracker TTL");
    require(unit(t.min_behavior_confidence) && t.min_behavior_confidence > 0, "invalid behavior confidence");
}

SingleCatTracker::SingleCatTracker(TrackerConfig config) : config_(config) { validate_tracker(config_); }
const Maybe<Track>& SingleCatTracker::update(Millis now, const std::vector<Detection>& detections) {
    require(now >= 0 && (!previous_time_.present || now > previous_time_.value), "tracker timestamps must increase");
    validate_detections(detections); // reject malformed input before mutating state
    previous_time_ = Maybe<Millis>(now);
    if (track_.present && now - track_.value.last_seen_ms > config_.ttl_ms) track_ = {};
    const Detection* cat = nullptr;
    std::size_t count = 0;
    for (const auto& d : detections) if (d.object == Object::Cat && d.confidence >= config_.min_confidence) {
        cat = &d; ++count;
    }
    ambiguous_ = count > 1;
    bool match = count == 1;
    if (match && track_.present) {
        match = intersection_over_union(track_.value.box, cat->box) >= config_.min_iou ||
                distance(center(track_.value.box), center(cat->box)) <= config_.max_centroid_distance;
    }
    if (match) {
        if (!track_.present) {
            if (next_id_ == std::numeric_limits<std::uint64_t>::max()) throw std::overflow_error("track IDs exhausted");
            Track fresh;
            fresh.id = next_id_++;
            fresh.created_ms = now;
            track_ = Maybe<Track>(std::move(fresh));
        }
        auto& t = track_.value;
        t.box = cat->box; t.last_seen_ms = now; t.misses = 0; t.observed = true;
        t.history.push_back({now, cat->box});
        while (t.history.size() > config_.history_capacity) t.history.pop_front();
    } else if (track_.present) {
        auto& t = track_.value;
        t.observed = false;
        if (t.misses != std::numeric_limits<std::uint64_t>::max()) ++t.misses;
    }
    if (track_.present) track_.value.age_ms = now - track_.value.created_ms;
    return track_;
}

GeometryObservation observe_geometry(const Track& t, const GeometryConfig& c, Roi context) {
    GeometryObservation result;
    if (!t.observed) return result;
    result.reference = bbox_bottom_center(t.box);
    result.food_distance = distance_to_box(result.reference, c.food_roi);
    result.water_distance = distance_to_box(result.reference, c.water_roi);
    const bool food = result.food_distance <= (context == Roi::Food ? c.exit_distance : c.near_distance) ||
                      intersection(t.box, c.food_roi) / area(t.box) >= c.min_body_overlap;
    const bool water = result.water_distance <= (context == Roi::Water ? c.exit_distance : c.near_distance) ||
                       intersection(t.box, c.water_roi) / area(t.box) >= c.min_body_overlap;
    if (food && water) { result.roi = Roi::Ambiguous; result.state = GeometryState::Ambiguous; return result; }
    result.near = food || water;
    result.roi = food ? Roi::Food : (water ? Roi::Water : Roi::None);
    result.state = food ? GeometryState::NearFood : (water ? GeometryState::NearWater : GeometryState::Far);
    const TrackPoint* previous = nullptr;
    for (const auto& p : t.history) {
        if (p.timestamp_ms < t.last_seen_ms && t.last_seen_ms - p.timestamp_ms <= c.motion_window_ms) {
            previous = &p; break;
        }
    }
    if (!previous) return result;
    const Point old = bbox_bottom_center(previous->box);
    const double seconds = static_cast<double>(t.last_seen_ms - previous->timestamp_ms) / 1000;
    const Roi target = food ? Roi::Food : (water ? Roi::Water :
        (result.food_distance < result.water_distance ? Roi::Food : Roi::Water));
    const Box& roi = target == Roi::Food ? c.food_roi : c.water_roi;
    const double speed = (distance_to_box(old, roi) - distance_to_box(result.reference, roi)) / seconds;
    if (speed >= c.min_motion_per_second) {
        result.state = target == Roi::Food ? GeometryState::ApproachingFood : GeometryState::ApproachingWater;
    } else {
        const double food_away = (result.food_distance - distance_to_box(old, c.food_roi)) / seconds;
        const double water_away = (result.water_distance - distance_to_box(old, c.water_roi)) / seconds;
        if ((distance_to_box(old, c.food_roi) <= c.exit_distance && food_away >= c.min_motion_per_second) ||
            (distance_to_box(old, c.water_roi) <= c.exit_distance && water_away >= c.min_motion_per_second))
            result.state = GeometryState::Leaving;
    }
    return result;
}

void ConfidenceSummary::add(double confidence) {
    if (samples == std::numeric_limits<std::uint64_t>::max()) throw std::overflow_error("confidence count exhausted");
    ++samples;
    mean += (confidence - mean) / static_cast<double>(samples);
    minimum = samples == 1 ? confidence : std::min(minimum, confidence);
    maximum = samples == 1 ? confidence : std::max(maximum, confidence);
}
Pipeline::Pipeline(Config config, Metadata metadata)
    : config_(config), metadata_(std::move(metadata)), tracker_(config.tracker) {
    validate_config(config_);
    require(metadata_.trial_id.size() <= 128 && metadata_.food_id.size() <= 128, "metadata budget exceeded");
    for (const auto& id : {metadata_.trial_id, metadata_.food_id})
        for (char c : id) require(c >= 0x20 && c <= 0x7e, "metadata IDs must be printable ASCII");
}
void Pipeline::finish(Millis now, EndReason reason, std::vector<Event>& events) {
    Event e = active_.value;
    e.type = e.roi == Roi::Food ? EventType::EatingEnd : EventType::DrinkingEnd;
    e.reason = reason;
    const Millis deadline = std::max(bounded_deadline(e.start_ms, config_.temporal.min_state_ms),
                                    bounded_deadline(last_positive_ms_, config_.temporal.dropout_ms));
    const Millis end = std::min(now, deadline);
    e.emitted_ms = now; e.end_ms = Maybe<Millis>(end); e.duration_ms = Maybe<Millis>(end - e.start_ms);
    events.push_back(e);
    active_ = {}; candidate_ = {};
}
Update Pipeline::update(Millis now, const std::vector<Detection>& detections, const Maybe<BehaviorSample>& input) {
    require(now >= 0 && (!previous_time_.present || now > previous_time_.value), "pipeline timestamps must increase");
    validate_detections(detections);
    if (input.present) {
        const auto& s = input.value;
        require(unit(s.confidence) && s.timestamp_ms >= 0 && s.timestamp_ms <= now, "invalid behavior timestamp/confidence");
        require(s.label == Behavior::Eating || s.label == Behavior::Drinking || s.label == Behavior::Idle ||
                s.label == Behavior::Unknown || s.label == Behavior::Unsure, "invalid behavior label");
        require(!s.track_id.present || s.track_id.value != 0, "track ID zero is invalid");
    }
    const bool gap = previous_time_.present && now - previous_time_.value > config_.temporal.max_observation_gap_ms;
    Update out;
    out.track = tracker_.update(now, detections);
    out.ambiguous = tracker_.ambiguous();
    if (active_.present && (!out.track.present || active_.value.track_id != out.track.value.id)) {
        finish(now, EndReason::TrackLost, out.events);
    } else if (active_.present && gap) {
        finish(now, EndReason::ObservationGap, out.events);
    }
    if (gap || !out.track.present || (candidate_.present && candidate_.value.track_id != out.track.value.id)) candidate_ = {};
    Roi context = active_.present ? active_.value.roi :
                  (candidate_.present ? behavior_roi(candidate_.value.label) : Roi::None);
    if (out.track.present && !out.ambiguous) out.geometry = observe_geometry(out.track.value, config_.geometry, context);
    if (out.ambiguous) { out.geometry.roi = Roi::Ambiguous; out.geometry.state = GeometryState::Ambiguous; }
    Behavior label = Behavior::Unknown;
    double confidence = 0;
    if (input.present && out.track.present && out.track.value.observed && !out.ambiguous) {
        const auto& s = input.value;
        out.behavior_accepted = now - s.timestamp_ms <= config_.temporal.max_behavior_age_ms &&
            (!previous_time_.present || s.timestamp_ms > previous_time_.value) &&
            s.timestamp_ms >= out.track.value.created_ms &&
            (!s.track_id.present || s.track_id.value == out.track.value.id) &&
            s.confidence >= config_.temporal.min_behavior_confidence;
        if (out.behavior_accepted) { label = s.label; confidence = s.confidence; }
    }
    const bool positive = (label == Behavior::Eating || label == Behavior::Drinking) && out.geometry.near &&
                          out.geometry.roi == behavior_roi(label);
    if (active_.present) {
        if (now - last_positive_ms_ > config_.temporal.dropout_ms &&
            now - active_.value.start_ms >= config_.temporal.min_state_ms) {
            finish(now, EndReason::EvidenceTimeout, out.events);
        } else if (positive && active_.value.roi == behavior_roi(label)) {
            last_positive_ms_ = now; active_.value.confidence.add(confidence);
        }
    }
    if (!active_.present) {
        if (candidate_.present && (now - candidate_.value.last_ms > config_.temporal.dropout_ms ||
            (out.behavior_accepted && (label == Behavior::Idle ||
                ((label == Behavior::Eating || label == Behavior::Drinking) &&
                 (!positive || label != candidate_.value.label)))))) candidate_ = {};
        if (positive) {
            if (!candidate_.present || candidate_.value.label != label) {
                Evidence e; e.label = label; e.track_id = out.track.value.id; e.first_ms = now;
                candidate_ = Maybe<Evidence>(e);
            }
            auto& c = candidate_.value;
            c.last_ms = now; c.confidence.add(confidence);
            if (now - c.first_ms >= config_.temporal.confirm_ms) {
                if (next_session_id_ == std::numeric_limits<std::uint64_t>::max()) throw std::overflow_error("session IDs exhausted");
                Event e;
                e.type = label == Behavior::Eating ? EventType::EatingStart : EventType::DrinkingStart;
                e.track_id = c.track_id; e.session_id = next_session_id_++;
                e.emitted_ms = now; e.start_ms = now; e.roi = behavior_roi(label);
                e.confidence = c.confidence; e.metadata = metadata_;
                active_ = Maybe<Event>(e); last_positive_ms_ = now;
                out.events.push_back(e); candidate_ = {};
            }
        }
    }
    if (active_.present) state_ = active_.value.roi == Roi::Food ? active_state(Behavior::Eating) : active_state(Behavior::Drinking);
    else if (candidate_.present) state_ = candidate_state(candidate_.value.label);
    else state_ = out.track.present ? State::Observing : State::NoCat;
    out.state = state_; previous_time_ = Maybe<Millis>(now);
    return out;
}

const char* name(State v) {
    switch (v) {
    case State::NoCat: return "NO_CAT"; case State::Observing: return "OBSERVING";
    case State::ConfirmingEating: return "CONFIRMING_EATING"; case State::ConfirmingDrinking: return "CONFIRMING_DRINKING";
    case State::Eating: return "EATING"; case State::Drinking: return "DRINKING";
    } return "INVALID";
}
const char* name(Roi v) {
    switch (v) { case Roi::None: return "NONE"; case Roi::Food: return "FOOD_ROI";
    case Roi::Water: return "WATER_ROI"; case Roi::Ambiguous: return "AMBIGUOUS"; } return "INVALID";
}
const char* name(GeometryState v) {
    switch (v) { case GeometryState::Far: return "FAR"; case GeometryState::NearFood: return "NEAR_FOOD";
    case GeometryState::NearWater: return "NEAR_WATER"; case GeometryState::ApproachingFood: return "APPROACHING_FOOD";
    case GeometryState::ApproachingWater: return "APPROACHING_WATER"; case GeometryState::Leaving: return "LEAVING";
    case GeometryState::Ambiguous: return "AMBIGUOUS"; } return "INVALID";
}
const char* name(EventType v) {
    switch (v) { case EventType::EatingStart: return "EATING_START"; case EventType::EatingEnd: return "EATING_END";
    case EventType::DrinkingStart: return "DRINKING_START"; case EventType::DrinkingEnd: return "DRINKING_END"; } return "INVALID";
}
const char* name(EndReason v) {
    switch (v) { case EndReason::None: return "NONE"; case EndReason::EvidenceTimeout: return "EVIDENCE_TIMEOUT";
    case EndReason::ObservationGap: return "OBSERVATION_GAP"; case EndReason::TrackLost: return "TRACK_LOST"; } return "INVALID";
}
} // namespace behavior_shadow
