#ifndef FOR_CAT_GEOMETRY_VALIDATION_H
#define FOR_CAT_GEOMETRY_VALIDATION_H
#include "behavior_shadow.h"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <locale>
#include <sstream>
#include <stdexcept>

// Additive IO/measurement helpers. The validated tracker/geometry/FSM are unchanged.
namespace geometry_validation {
using namespace behavior_shadow;
struct Dimensions { int width = 0, height = 0; };
struct Pixels { int x1 = 0, y1 = 0, x2 = 0, y2 = 0; }; // exclusive right/bottom
inline void require(bool ok, const char* message) { if (!ok) throw std::invalid_argument(message); }
inline void dimensions(Dimensions d) {
    require(d.width >= 2 && d.height >= 2 && d.width <= 16384 && d.height <= 16384, "invalid original-frame dimensions");
}
inline Box normalized(Pixels p, Dimensions d) {
    dimensions(d);
    require(p.x1 >= 0 && p.y1 >= 0 && p.x2 <= d.width && p.y2 <= d.height && p.x1 < p.x2 && p.y1 < p.y2,
            "pixel box must be inside original frame with positive area");
    return {static_cast<double>(p.x1)/d.width,static_cast<double>(p.y1)/d.height,
            static_cast<double>(p.x2)/d.width,static_cast<double>(p.y2)/d.height};
}
inline Pixels rendered(Box b, Dimensions d) {
    dimensions(d); require(valid_box(b), "invalid normalized render box");
    // Snap tiny arithmetic noise at integer boundaries, then enclose the ROI.
    const auto low = [](double n) { return static_cast<int>(std::floor(n + 1e-9)); };
    const auto high = [](double n) { return static_cast<int>(std::ceil(n - 1e-9)); };
    return {low(b.x1*d.width),low(b.y1*d.height),high(b.x2*d.width),high(b.y2*d.height)};
}
inline void same_dimensions(Dimensions actual, Dimensions calibrated) {
    dimensions(actual); dimensions(calibrated);
    require(actual.width == calibrated.width && actual.height == calibrated.height,
            "frame dimensions differ from calibration; review/recalibrate the original view");
}
inline double body_overlap(Box body, Box roi) {
    require(valid_box(body) && valid_box(roi), "invalid overlap box");
    return std::max(0.0,std::min(body.x2,roi.x2)-std::max(body.x1,roi.x1)) *
           std::max(0.0,std::min(body.y2,roi.y2)-std::max(body.y1,roi.y1)) /
           ((body.x2-body.x1)*(body.y2-body.y1));
}
inline std::string quote(const std::string& value) {
    std::ostringstream out; out.imbue(std::locale::classic()); out << '"';
    for (char raw : value) {
        const auto c = static_cast<unsigned char>(raw);
        if (c == '"' || c == '\\') out << '\\' << raw;
        else if (c < 32) out << "\\u00" << std::hex << std::setfill('0') << std::setw(2) << static_cast<unsigned>(c) << std::dec;
        else out << raw;
    }
    out << '"'; return out.str();
}
inline std::string box_json(Box b) {
    std::ostringstream s; s.imbue(std::locale::classic()); s << std::setprecision(17);
    s << "{\"x1\":" << b.x1 << ",\"y1\":" << b.y1 << ",\"x2\":" << b.x2 << ",\"y2\":" << b.y2 << '}'; return s.str();
}
inline std::string config_json(const Config& c, bool synthetic) {
    validate_config(c);
    std::ostringstream s; s.imbue(std::locale::classic()); s << std::setprecision(17);
    s << "{\n\"schema_version\":2,\"status\":" << quote(synthetic ? "SYNTHETIC_TEST_ONLY" : "CONFIGURED")
      << ",\n\"coordinate_system\":\"normalized_original_camera_frame\",\"food_bowl_color\":\"RED\",\"water_bowl_color\":\"BLUE\","
      << "\"approach_reference\":\"BLUE_FLOOR_LINE\",\n\"food_roi\":" << box_json(c.geometry.food_roi)
      << ",\n\"water_roi\":" << box_json(c.geometry.water_roi) << ",\n\"approach_line\":";
    if (c.geometry.approach_line_start.present)
        s << box_json({c.geometry.approach_line_start.value.x,c.geometry.approach_line_start.value.y,
                       c.geometry.approach_line_end.value.x,c.geometry.approach_line_end.value.y});
    else s << "null";
    s << ",\n\"tracker\":{\"min_confidence\":" << c.tracker.min_confidence << ",\"min_iou\":" << c.tracker.min_iou
      << ",\"max_centroid_distance\":" << c.tracker.max_centroid_distance << ",\"ttl_ms\":" << c.tracker.ttl_ms
      << ",\"history_capacity\":" << c.tracker.history_capacity << "},\n\"geometry\":{\"near_distance\":" << c.geometry.near_distance
      << ",\"exit_distance\":" << c.geometry.exit_distance << ",\"min_body_overlap\":" << c.geometry.min_body_overlap
      << ",\"min_motion_per_second\":" << c.geometry.min_motion_per_second << ",\"motion_window_ms\":" << c.geometry.motion_window_ms
      << "},\n\"temporal\":{\"confirm_ms\":" << c.temporal.confirm_ms << ",\"dropout_ms\":" << c.temporal.dropout_ms
      << ",\"min_state_ms\":" << c.temporal.min_state_ms << ",\"max_observation_gap_ms\":" << c.temporal.max_observation_gap_ms
      << ",\"max_behavior_age_ms\":" << c.temporal.max_behavior_age_ms << ",\"min_behavior_confidence\":" << c.temporal.min_behavior_confidence
      << "},\n\"notes\":\"Human-specified original-frame ROIs; review overlay. Geometry is not behavior. Thresholds unchanged unless supplied by base config.\"\n}\n";
    return s.str();
}

// Prefer strictly increasing media PTS; lock to anchored frame/FPS fallback once
// timestamps fail. No wall-clock inference speed enters recorded-video geometry.
class VideoClock {
public:
    explicit VideoClock(double fps) : fps_(fps) {}
    Millis next(double pts_ms) {
        const bool valid = std::isfinite(pts_ms) && pts_ms >= 0 && pts_ms <= 1e12;
        Millis stamp = valid ? static_cast<Millis>(std::llround(pts_ms)) : 0;
        if (!fallback_ && (!valid || (index_ > 0 && stamp <= last_))) {
            require(std::isfinite(fps_) && fps_ > 0 && fps_ <= 1000, "invalid media PTS and no usable FPS fallback");
            fallback_ = true; base_index_ = index_ == 0 ? 0 : index_-1; base_time_ = index_ == 0 ? 0 : last_;
        }
        if (fallback_) {
            const double delta = static_cast<double>(index_ - base_index_) * 1000 / fps_;
            require(delta <= 1e12 && base_time_ <= 1000000000000LL - static_cast<Millis>(std::llround(delta)), "media duration exceeds budget");
            stamp = base_time_ + static_cast<Millis>(std::llround(delta)); ++fallback_frames_;
        }
        require(index_ == 0 || stamp > last_, "non-increasing media milliseconds");
        require(index_ < 1000000, "decoded-frame budget exceeded");
        ++index_; last_ = stamp; return stamp;
    }
    std::uint64_t fallback_frames() const { return fallback_frames_; }
private:
    double fps_;
    bool fallback_ = false;
    std::uint64_t index_ = 0, base_index_ = 0, fallback_frames_ = 0;
    Millis base_time_ = 0, last_ = 0;
};
struct Distribution {
    std::vector<double> values;
    void add(double n) {
        require(std::isfinite(n) && n >= 0 && values.size() < 100000, "distance statistics budget/input invalid");
        values.push_back(n);
    }
    std::string json() const {
        if (values.empty()) return "{\"count\":0,\"min\":null,\"median\":null,\"p95\":null}";
        auto v = values; std::sort(v.begin(),v.end()); const auto n = v.size();
        const double median = n % 2 == 0 ? (v[n/2-1]+v[n/2])/2 : v[n/2];
        const auto p95 = static_cast<std::size_t>(std::ceil(static_cast<double>(n)*0.95))-1;
        std::ostringstream s; s.imbue(std::locale::classic()); s << std::setprecision(17);
        s << "{\"count\":" << n << ",\"min\":" << v[0] << ",\"median\":" << median << ",\"p95\":" << v[p95] << '}'; return s.str();
    }
};
inline std::string artifact_name(const std::string& tag) {
    const std::vector<std::string> allowed{"first_cat","nearest_food","nearest_water","approaching_food","approaching_water",
        "leaving","ambiguous","track_lost","reacquired"};
    require(std::find(allowed.begin(),allowed.end(),tag) != allowed.end(), "unknown evidence tag");
    return tag + ".jpg";
}
} // namespace geometry_validation
#endif
