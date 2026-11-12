#ifndef FOR_CAT_BEHAVIOR_SHADOW_H
#define FOR_CAT_BEHAVIOR_SHADOW_H

// Offline/shadow only. No OpenCV, TensorRT, database, serial, or actuator dependency.
// One owner thread per Pipeline; timestamps are monotonic milliseconds, not UTC.
#include <cstddef>
#include <cstdint>
#include <deque>
#include <string>
#include <vector>

namespace behavior_shadow {
using Millis = std::int64_t;
template<class T> struct Maybe {
    bool present = false;
    T value{};
    Maybe() = default;
    explicit Maybe(T v) : present(true), value(v) {}
};
struct Box { double x1 = 0, y1 = 0, x2 = 0, y2 = 0; };
struct Point { double x = 0, y = 0; };
bool valid_box(const Box& b);
double intersection_over_union(const Box& a, const Box& b);
Point bbox_bottom_center(const Box& b);
enum class Object { Cat, Dog, Other };
struct Detection { Object object = Object::Other; double confidence = 0; Box box; };
struct TrackPoint { Millis timestamp_ms = 0; Box box; };
struct Track {
    std::uint64_t id = 0;
    Box box;
    Millis created_ms = 0, last_seen_ms = 0, age_ms = 0;
    std::uint64_t misses = 0;
    bool observed = false;
    std::deque<TrackPoint> history;
};
struct TrackerConfig {
    double min_confidence = 0.5, min_iou = 0.15, max_centroid_distance = 0.15;
    Millis ttl_ms = 1500;
    std::size_t history_capacity = 32;
};
struct GeometryConfig {
    Box food_roi, water_roi;
    Maybe<Point> approach_line_start, approach_line_end;
    double near_distance = 0.03, exit_distance = 0.06, min_body_overlap = 0.2;
    double min_motion_per_second = 0.02;
    Millis motion_window_ms = 1000;
};
struct TemporalConfig {
    Millis confirm_ms = 1000, dropout_ms = 800, min_state_ms = 1000;
    Millis max_observation_gap_ms = 500, max_behavior_age_ms = 250;
    double min_behavior_confidence = 0.7;
};
struct Config { TrackerConfig tracker; GeometryConfig geometry; TemporalConfig temporal; };
void validate_config(const Config& config);

class SingleCatTracker {
public:
    explicit SingleCatTracker(TrackerConfig config);
    const Maybe<Track>& update(Millis now, const std::vector<Detection>& detections);
    const Maybe<Track>& track() const { return track_; }
    bool ambiguous() const { return ambiguous_; }
private:
    TrackerConfig config_;
    Maybe<Track> track_;
    Maybe<Millis> previous_time_;
    std::uint64_t next_id_ = 1;
    bool ambiguous_ = false;
};

enum class Roi { None, Food, Water, Ambiguous };
enum class GeometryState { Far, NearFood, NearWater, ApproachingFood, ApproachingWater, Leaving, Ambiguous };
struct GeometryObservation {
    Roi roi = Roi::None;
    GeometryState state = GeometryState::Far;
    bool near = false;
    Point reference; // bbox_bottom_center, never a head location
    double food_distance = 0, water_distance = 0; // normalized image units, not cm
};
GeometryObservation observe_geometry(const Track& track, const GeometryConfig& config,
                                     Roi hysteresis_context = Roi::None);

enum class Behavior { Eating, Drinking, Idle, Unknown, Unsure };
struct BehaviorSample {
    Behavior label = Behavior::Unknown;
    double confidence = 0;
    Millis timestamp_ms = 0;
    Maybe<std::uint64_t> track_id;
};
enum class State { NoCat, Observing, ConfirmingEating, ConfirmingDrinking, Eating, Drinking };
enum class EventType { EatingStart, EatingEnd, DrinkingStart, DrinkingEnd };
enum class EndReason { None, EvidenceTimeout, ObservationGap, TrackLost };
struct ConfidenceSummary {
    std::uint64_t samples = 0;
    double mean = 0, minimum = 0, maximum = 0;
    void add(double confidence);
};
struct Metadata { std::string trial_id, food_id; }; // empty = unspecified; not preference labels
struct Event {
    EventType type = EventType::EatingStart;
    std::uint64_t track_id = 0, session_id = 0;
    Millis emitted_ms = 0, start_ms = 0;
    Maybe<Millis> end_ms, duration_ms;
    Roi roi = Roi::None;
    EndReason reason = EndReason::None;
    ConfidenceSummary confidence;
    Maybe<double> weight_before, weight_after, consumed_grams;
    Metadata metadata;
    bool shadow_only = true;
};
struct Update {
    Maybe<Track> track;
    GeometryObservation geometry;
    State state = State::NoCat;
    bool ambiguous = false, behavior_accepted = false;
    std::vector<Event> events; // returned to caller; never accumulated in Pipeline
};

class Pipeline {
public:
    explicit Pipeline(Config config, Metadata metadata = {});
    Update update(Millis now, const std::vector<Detection>& detections,
                  const Maybe<BehaviorSample>& behavior = {});
private:
    Config config_;
    Metadata metadata_;
    SingleCatTracker tracker_;
    Maybe<Millis> previous_time_;
    State state_ = State::NoCat;
    struct Evidence {
        Behavior label = Behavior::Unknown;
        std::uint64_t track_id = 0;
        Millis first_ms = 0, last_ms = 0;
        ConfidenceSummary confidence;
    };
    Maybe<Evidence> candidate_;
    Maybe<Event> active_;
    Millis last_positive_ms_ = 0;
    std::uint64_t next_session_id_ = 1;
    void finish(Millis now, EndReason reason, std::vector<Event>& events);
};

// Strict bounded JSON configuration adapter; null template ROIs fail closed.
// Synthetic coordinates require explicit opt-in (offline fixtures/demo only).
Config load_config_json(const std::string& json, bool allow_synthetic = false);
std::string event_json(const Event& event);
const char* name(State value);
const char* name(Roi value);
const char* name(GeometryState value);
const char* name(EventType value);
const char* name(EndReason value);
} // namespace behavior_shadow
#endif
