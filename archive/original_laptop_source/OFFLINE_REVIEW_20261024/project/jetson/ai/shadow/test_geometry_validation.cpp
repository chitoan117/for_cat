#include "geometry_validation.h"
#include <atomic>
#include <functional>
#include <iostream>
#include <limits>
#include <thread>
namespace gv = geometry_validation;
using namespace behavior_shadow;
namespace {
unsigned named_cases = 0;
std::atomic<unsigned> checks{0};
void check(bool value) { ++checks; if (!value) throw std::runtime_error("geometry IO assertion failed"); }
void rejects(const std::function<void()>& fn) { bool bad = false; try { fn(); } catch (const std::invalid_argument&) { bad = true; } check(bad); }
void test(const char* name,const std::function<void()>& fn) { fn(); ++named_cases; std::cout << "PASS " << name << '\n'; }
Config config() { Config c; c.geometry.food_roi = {0.1,0.1,0.35,0.4}; c.geometry.water_roi = {0.65,0.1,0.9,0.4}; return c; }
}
int main() {
    try {
        test("pixel_to_normalized_original",[] {
            const auto b = gv::normalized({64,48,224,192},{640,480}); check(b.x1 == 0.1 && b.y2 == 0.4);
            const auto all = gv::normalized({0,0,640,480},{640,480}); check(all.x2 == 1 && all.y2 == 1);
        });
        test("normalized_to_exclusive_pixel_render",[] {
            const auto p = gv::rendered({0.1,0.1,0.35,0.4},{640,480}); check(p.x1 == 64 && p.x2 == 224 && p.y2 == 192);
            const auto edge = gv::rendered({0,0,1,1},{640,480}); check(edge.x2 == 640 && edge.y2 == 480);
        });
        test("invalid_dimensions_and_pixel_bounds",[] {
            for (auto d : {gv::Dimensions{0,480},gv::Dimensions{640,-1},gv::Dimensions{1,1},gv::Dimensions{16385,480}})
                rejects([&] { gv::normalized({0,0,1,1},d); });
            for (auto p : {gv::Pixels{-1,0,4,4},gv::Pixels{4,0,4,4},gv::Pixels{0,0,641,480}})
                rejects([&] { gv::normalized(p,{640,480}); });
        });
        test("dimension_change_requires_recalibration",[] {
            gv::same_dimensions({640,480},{640,480}); check(true);
            rejects([] { gv::same_dimensions({1280,960},{640,480}); });
            rejects([] { gv::same_dimensions({480,640},{640,480}); });
        });
        test("config_roundtrip_food_water_semantics",[] {
            const auto c = config(); const auto json = gv::config_json(c,false); const auto read = load_config_json(json);
            check(read.geometry.food_roi.x1 == c.geometry.food_roi.x1 && read.geometry.water_roi.x1 == c.geometry.water_roi.x1);
            check(json.find("\"food_bowl_color\":\"RED\"") != std::string::npos && json.find("\"water_bowl_color\":\"BLUE\"") != std::string::npos);
            rejects([&] { load_config_json(gv::config_json(c,true)); });
            check(load_config_json(gv::config_json(c,true),true).tracker.ttl_ms == c.tracker.ttl_ms);
        });
        test("body_overlap_and_boundary",[] {
            check(gv::body_overlap({0.1,0.1,0.2,0.2},{0.1,0.1,0.2,0.2}) == 1);
            check(gv::body_overlap({0.1,0.1,0.2,0.2},{0.2,0.1,0.3,0.2}) == 0);
            rejects([] { gv::body_overlap({0,0,0,0},{0,0,1,1}); });
        });
        test("media_pts_not_processing_clock",[] {
            gv::VideoClock clock(30); check(clock.next(0) == 0); check(clock.next(33.3) == 33); check(clock.next(1000) == 1000);
            check(clock.fallback_frames() == 0);
        });
        test("duplicate_backward_pts_anchored_fallback",[] {
            gv::VideoClock clock(25); check(clock.next(100) == 100); check(clock.next(140) == 140);
            check(clock.next(140) == 180); check(clock.next(0) == 220); check(clock.next(5000) == 260);
            check(clock.fallback_frames() == 3);
        });
        test("invalid_fps_only_rejected_when_needed",[] {
            gv::VideoClock clock(0); check(clock.next(0) == 0); check(clock.next(50) == 50); rejects([&] { clock.next(0); });
            gv::VideoClock nan(std::numeric_limits<double>::quiet_NaN()); rejects([&] { nan.next(-1); });
        });
        test("distance_distribution_null_and_quantiles",[] {
            gv::Distribution d; check(d.json().find("\"median\":null") != std::string::npos);
            for (double n : {4.,1.,3.,2.}) d.add(n);
            check(d.json().find("\"median\":2.5") != std::string::npos && d.json().find("\"p95\":4") != std::string::npos);
            rejects([&] { d.add(std::numeric_limits<double>::infinity()); });
        });
        test("artifact_names_and_json_escaping",[] {
            check(gv::artifact_name("nearest_food") == "nearest_food.jpg"); rejects([] { gv::artifact_name("../source"); });
            check(gv::quote("a\n\"b") == "\"a\\u000a\\\"b\"");
        });
        test("tracker_continuity_geometry_no_behavior",[] {
            const auto c = config(); SingleCatTracker tracker(c.tracker);
            const std::vector<Detection> detections{{Object::Cat,0.9,c.geometry.food_roi}};
            const auto first = tracker.update(0,detections).value.id; tracker.update(100,{});
            const auto t = tracker.update(200,detections);
            check(t.value.id == first && observe_geometry(t.value,c.geometry).roi == Roi::Food);
            // API deliberately invokes tracker/geometry only; no behavior sample/FSM.
            check(tracker.update(2000,{}).present == false);
        });
        test("four_owner_threads_coordinate_stress",[] {
            std::atomic<bool> failed{false}; std::vector<std::thread> threads;
            for (unsigned owner = 0; owner < 4; ++owner) threads.emplace_back([&,owner] {
                try {
                    for (int n = 0; n < 10000; ++n) {
                        const int x = (n+static_cast<int>(owner))%600;
                        const auto p = gv::rendered(gv::normalized({x,10,x+20,30},{640,480}),{640,480});
                        check(p.x1 == x && p.x2 == x+20 && p.y2 == 30);
                    }
                } catch (...) { failed = true; }
            });
            for (auto& thread : threads) thread.join();
            check(!failed);
        });
        std::cout << named_cases << " named cases; " << checks.load() << " assertions; 40000 stress iterations PASS\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
