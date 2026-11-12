#include "behavior_shadow.h"
#include <atomic>
#include <cmath>
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <limits>
#include <random>
#include <stdexcept>
#include <thread>

namespace {
using namespace behavior_shadow;
std::atomic<unsigned> checks{0};
void check(bool ok, const char* message) {
    ++checks;
    if (!ok) throw std::runtime_error(message);
}
void rejects(const std::function<void()>& action) {
    bool rejected = false;
    try { action(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid input was accepted");
}
std::string read(const char* path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("cannot open test fixture");
    return {std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
}
std::string replace(std::string input, const std::string& from, const std::string& to) {
    const auto pos = input.find(from);
    if (pos == std::string::npos) throw std::runtime_error("test replacement not found");
    input.replace(pos, from.size(), to); return input;
}
std::vector<Detection> cat(const Box& box) { return {{Object::Cat, 0.95, box}}; }
Maybe<BehaviorSample> sample(Behavior label, Millis now, double confidence = 0.9, std::uint64_t id = 0) {
    BehaviorSample s; s.label = label; s.timestamp_ms = now; s.confidence = confidence;
    if (id != 0) s.track_id = Maybe<std::uint64_t>(id);
    return Maybe<BehaviorSample>(s);
}
Update start(Pipeline& p, const Box& box, Behavior label, Millis first = 0) {
    Update out;
    for (Millis now = first; now <= first + 1000; now += 100) out = p.update(now, cat(box), sample(label, now));
    check(out.events.size() == 1, "expected one confirmed start");
    check(out.events[0].start_ms == first + 1000, "start must be confirmation time, not retroactive");
    return out;
}
void configuration_tests(const std::string& json, const std::string& unconfigured) {
    rejects([&] { load_config_json(json); });
    rejects([&] { load_config_json(unconfigured, true); });
    Config configured = load_config_json(replace(json,"SYNTHETIC_TEST_ONLY","CONFIGURED"));
    check(configured.tracker.ttl_ms == 1500, "configured schema");
    const std::vector<std::pair<std::string,std::string>> edits{
        {"\"schema_version\": 2", "\"schema_version\": true"},
        {"\"schema_version\": 2", "\"schema_version\": 3"},
        {"\"food_bowl_color\": \"RED\"", "\"food_bowl_color\": \"BLUE\""},
        {"\"water_bowl_color\": \"BLUE\"", "\"water_bowl_color\": \"RED\""},
        {"normalized_original_camera_frame", "pixels"}, {"BLUE_FLOOR_LINE", "CM_CALIBRATION"},
        {"\"x1\": 0.1", "\"x1\": -0.1"}, {"\"x2\": 0.35", "\"x2\": 1.1"},
        {"\"x1\": 0.1", "\"x1\": 0.35"}, {"\"x1\": 0.1", "\"x1\": 0.4"},
        {"\"x1\": 0.65", "\"x1\": 0.2"},
        {"\"food_roi\": {", "\"food_roi\": {\"extra\": 1,"},
        {"\"food_roi\": {", "\"food_roi\": {\"x1\": 0.2,"},
        {"\"food_roi\"", "\"food_roii\""},
        {"\"ttl_ms\": 1500", "\"ttl_ms\": null"}, {"\"ttl_ms\": 1500", "\"ttl_ms\": 0"},
        {"\"ttl_ms\": 1500", "\"ttl_ms\": 1.5"}, {"\"ttl_ms\": 1500", "\"ttl_ms\": 999999999999999999999"},
        {"\"ttl_ms\": 1500", "\"ttl_ms\": \"1500\""},
        {"\"history_capacity\": 32", "\"history_capacity\": 1"},
        {"\"history_capacity\": 32", "\"history_capacity\": 513"},
        {"\"near_distance\": 0.03", "\"near_distance\": 0.9"},
        {"\"min_iou\": 0.15", "\"min_iou\": 0"},
        {"\"min_confidence\": 0.5", "\"min_confidence\": 1.1"},
        {"\"confirm_ms\": 1000", "\"confirm_ms\": -1"},
        {"\"max_observation_gap_ms\": 500", "\"max_observation_gap_ms\": 1501"},
        {"\"approach_line\": null", "\"approach_line\": false"},
        {"\"approach_line\": null", "\"approach_line\": {\"x1\":0,\"y1\":0,\"x2\":0,\"y2\":0}"},
        {"\"approach_line\": null", "\"approach_line\": {\"x1\":0,\"y1\":0,\"x2\":2,\"y2\":0}"},
        {"\"notes\":", "\"unknown\":"}
    };
    for (const auto& edit : edits) rejects([&] { load_config_json(replace(json,edit.first,edit.second),true); });
    for (const std::string& malformed : std::vector<std::string>{"", "[]", "null", "true", "{", "{}x", "{\"a\":01}",
             "{\"a\":1.}", "{\"a\":+1}", "{\"a\":1e}", "{\"a\":NaN}", "{\"a\":1e999}",
             "{\"a\":1,}", "{\"a\":1,\"a\":2}", "{\"a\":\"\\uDC00\"}", "{\"a\":\"\\uD800x\"}",
             "{\"a\":\"\\z\"}", "{\"a\":\"\n\"}", "{/*comment*/}", std::string(65537,' ')})
        rejects([&] { load_config_json(malformed,true); });
    check(load_config_json(replace(json,"\"approach_line\": null",
          "\"approach_line\": {\"x1\":0.9,\"y1\":0.4,\"x2\":0.1,\"y2\":0.4}"),true)
          .geometry.approach_line_start.present, "horizontal/reversed line endpoints are valid");
    check(load_config_json(replace(json,"INVENTED TEST GEOMETRY ONLY.","\\uD83D\\uDE00 "),true).tracker.ttl_ms == 1500,
          "Unicode surrogate pair in note");
    rejects([&] { load_config_json(replace(json,"INVENTED TEST GEOMETRY ONLY.",std::string(1,static_cast<char>(0xff))),true); });
    for (std::size_t n = 0; n < json.size(); n += 13) rejects([&] { load_config_json(json.substr(0,n),true); });
    std::mt19937 random(12345);
    for (int i = 0; i < 2000; ++i) {
        std::string changed = json;
        changed[static_cast<std::size_t>(random()) % changed.size()] = static_cast<char>(random() % 128u);
        try { validate_config(load_config_json(changed,true)); } catch (const std::invalid_argument&) { /* expected */ }
        ++checks;
    }
}
void tracker_tests(const Config& c) {
    const Box a = c.geometry.food_roi;
    SingleCatTracker t(c.tracker);
    auto value = t.update(0,cat(a));
    check(value.present && value.value.id == 1 && value.value.observed && value.value.age_ms == 0, "new track");
    const auto id = value.value.id;
    auto jitter = a; jitter.x1 += 0.01; jitter.x2 += 0.01;
    check(t.update(100,cat(jitter)).value.id == id, "IoU association");
    value = t.update(200,{});
    check(value.present && !value.value.observed && value.value.misses == 1 && value.value.last_seen_ms == 100,
          "miss retains last seen, not a new observation");
    check(t.update(300,cat(a)).value.id == id, "short dropout preserves ID");
    auto many = cat(a); many.push_back({Object::Cat,0.9,c.geometry.water_roi});
    check(!t.update(400,many).value.observed && t.ambiguous(), "multiple cats ambiguous");
    check(!t.update(500,cat(c.geometry.water_roi)).value.observed, "far unmatched cat not forced onto old track");
    value = t.update(1800,{});
    check(value.present && value.value.age_ms == 1800, "TTL inclusive boundary");
    check(!t.update(1801,{}).present, "TTL expires strictly after deadline");
    check(t.update(1802,cat(a)).value.id == id + 1, "new ID after expiration");
    for (Millis i = 1803; i <= 2000; ++i) value = t.update(i,cat(a));
    check(value.value.history.size() == c.tracker.history_capacity, "history hard bound");
    auto bad = cat(a); bad[0].box.x1 = std::numeric_limits<double>::quiet_NaN();
    rejects([&] { t.update(2001,bad); });
    check(t.update(2001,cat(a)).value.observed, "invalid input does not advance clock");
    rejects([&] { t.update(2001,cat(a)); }); rejects([&] { t.update(-1,{}); });
    SingleCatTracker dogs(c.tracker);
    check(!dogs.update(0,{{Object::Dog,1,a}}).present, "dog is not a cat");
    check(!dogs.update(1,{{Object::Cat,0.1,a}}).present, "weak cat is ignored");
    auto cc = c.tracker; cc.min_iou = 0.99; cc.max_centroid_distance = 0.1;
    SingleCatTracker centroid(cc);
    const Box small{0.1,0.1,0.12,0.12}, nearby{0.15,0.1,0.17,0.12};
    centroid.update(0,cat(small));
    check(centroid.update(1,cat(nearby)).value.observed, "centroid gate bridges low IoU");
}
void geometry_tests(const Config& c) {
    auto g = c.geometry; g.min_body_overlap = 1;
    Track t; t.observed = true; t.box = {0.2,0.2,0.25,0.4}; t.last_seen_ms = 100;
    check(observe_geometry(t,g).state == GeometryState::NearFood, "near food");
    t.box = c.geometry.water_roi;
    check(observe_geometry(t,g).state == GeometryState::NearWater, "near water");
    t.box = {0.37,0.3,0.42,0.4};
    check(!observe_geometry(t,g).near && observe_geometry(t,g,Roi::Food).near, "ROI entry/exit hysteresis");
    t.box = {0.1,0.1,0.9,0.4}; g.min_body_overlap = 0.2;
    check(observe_geometry(t,g).state == GeometryState::Ambiguous, "body spanning both bowls ambiguous");
    t.box = {0.2,0.4,0.25,0.5}; t.last_seen_ms = 1000;
    t.history = {{0,{0.2,0.6,0.25,0.7}},{1000,t.box}};
    check(observe_geometry(t,g).state == GeometryState::ApproachingFood, "approaching food is motion only");
    t.box = {0.7,0.4,0.75,0.5}; t.history = {{0,{0.7,0.6,0.75,0.7}},{1000,t.box}};
    check(observe_geometry(t,g).state == GeometryState::ApproachingWater, "approaching water");
    t.box = {0.2,0.6,0.25,0.7}; t.history = {{0,{0.2,0.2,0.25,0.3}},{1000,t.box}};
    check(observe_geometry(t,g).state == GeometryState::Leaving, "leaving food");
    t.observed = false;
    check(!observe_geometry(t,g).near, "missed detection does not reuse geometry as fresh");
    check(intersection_over_union(c.geometry.food_roi,c.geometry.food_roi) == 1, "IoU identity");
    check(intersection_over_union(c.geometry.food_roi,c.geometry.water_roi) == 0, "IoU disjoint");
}
void temporal_tests(const Config& c) {
    const Box food = c.geometry.food_roi, water = c.geometry.water_roi;
    for (Behavior label : {Behavior::Unknown,Behavior::Unsure,Behavior::Idle}) {
        Pipeline p(c);
        for (Millis now = 0; now < 4000; now += 100) {
            const auto out = p.update(now,cat(food),sample(label,now));
            check(out.events.empty() && out.state == State::Observing, "non-consumption label cannot confirm");
        }
    }
    for (const auto& pair : std::vector<std::pair<Box,Behavior>>{{food,Behavior::Drinking},{water,Behavior::Eating}}) {
        Pipeline p(c);
        for (Millis now = 0; now < 3000; now += 100)
            check(p.update(now,cat(pair.first),sample(pair.second,now)).events.empty(), "wrong ROI must not cross-trigger");
    }
    Pipeline geometry_only(c);
    for (Millis now = 0; now < 3000; now += 100)
        check(geometry_only.update(now,cat(food)).events.empty(), "geometry alone cannot predict behavior");
    Pipeline p(c,{"trial-1","food-1"});
    auto out = start(p,food,Behavior::Eating);
    const Event started = out.events[0];
    check(started.type == EventType::EatingStart && !started.end_ms.present && !started.duration_ms.present, "START contract");
    check(started.confidence.samples == 11 && std::abs(started.confidence.mean - 0.9) < 1e-12, "confidence summary");
    check(started.metadata.food_id == "food-1" && started.shadow_only, "metadata/shadow contract");
    out = p.update(1200,{},sample(Behavior::Unknown,1200));
    check(out.events.empty() && out.state == State::Eating, "short disappearance tolerated");
    out = p.update(1400,cat(food),sample(Behavior::Eating,1400));
    check(out.events.empty() && out.track.value.id == started.track_id, "short recovery no duplicate start");
    for (Millis now = 1600; now <= 2400; now += 200) out = p.update(now,{},sample(Behavior::Unsure,now));
    check(out.events.size() == 1 && out.events[0].type == EventType::EatingEnd, "sustained disappearance ends");
    const Event ended = out.events[0];
    check(ended.session_id == started.session_id && ended.track_id == started.track_id, "paired IDs");
    check(ended.end_ms.value == 2200 && ended.duration_ms.value == 1200 && ended.emitted_ms == 2400,
          "logical end deadline distinct from notification time");
    check(!ended.weight_before.present && !ended.weight_after.present && !ended.consumed_grams.present, "no invented grams");
    check(p.update(2500,{}).events.empty(), "END emitted once");
    Pipeline drink(c); check(start(drink,water,Behavior::Drinking).events[0].type == EventType::DrinkingStart, "drinking start");
    Pipeline sparse(c);
    sparse.update(0,cat(food),sample(Behavior::Eating,0));
    check(sparse.update(1200,cat(food),sample(Behavior::Eating,1200)).events.empty(), "sparse time gap cannot confirm");
    Pipeline gap(c); start(gap,food,Behavior::Eating);
    out = gap.update(1600,cat(food),sample(Behavior::Eating,1600));
    check(out.events.size() == 1 && out.events[0].reason == EndReason::ObservationGap, "active clock gap closes session");
    Pipeline lost(c); start(lost,food,Behavior::Eating);
    out = lost.update(3000,cat(water),sample(Behavior::Drinking,3000));
    check(out.events.size() == 1 && out.events[0].reason == EndReason::TrackLost && out.track.value.id != started.track_id,
          "expiration/new track ends old session");
    Pipeline unknown(c);
    for (Millis now = 0; now <= 500; now += 100) unknown.update(now,cat(food),sample(Behavior::Eating,now));
    unknown.update(600,cat(food),sample(Behavior::Unknown,600));
    unknown.update(700,cat(food),sample(Behavior::Unsure,700));
    for (Millis now = 800; now <= 1000; now += 100) out = unknown.update(now,cat(food),sample(Behavior::Eating,now));
    check(out.events.size() == 1, "short unknown/unsure tolerance");
    Pipeline idle(c);
    for (Millis now = 0; now <= 500; now += 100) idle.update(now,cat(food),sample(Behavior::Eating,now));
    idle.update(600,cat(food),sample(Behavior::Idle,600));
    for (Millis now = 700; now <= 1500; now += 100)
        check(idle.update(now,cat(food),sample(Behavior::Eating,now)).events.empty(), "explicit IDLE resets confirmation");
    Pipeline ambiguous(c); auto both = cat(food); both.push_back({Object::Cat,0.9,water});
    for (Millis now = 0; now < 3000; now += 100)
        check(ambiguous.update(now,both,sample(Behavior::Eating,now)).events.empty(), "multiple cats suppress behavior");
    Pipeline stale(c);
    for (Millis now = 1000; now < 3000; now += 100) {
        out = stale.update(now,cat(food),sample(Behavior::Eating,0));
        check(!out.behavior_accepted && out.events.empty(), "stale behavior rejected");
    }
    Pipeline mismatch(c);
    for (Millis now = 0; now < 3000; now += 100)
        check(!mismatch.update(now,cat(food),sample(Behavior::Eating,now,0.9,99)).behavior_accepted, "track mismatch rejected");
    Pipeline weak(c);
    for (Millis now = 0; now < 3000; now += 100)
        check(weak.update(now,cat(food),sample(Behavior::Eating,now,0.1)).events.empty(), "low confidence not IDLE or positive");
    Pipeline invalid(c);
    rejects([&] { invalid.update(0,cat(food),sample(Behavior::Eating,1)); });
    check(invalid.update(0,cat(food)).track.value.id == 1, "bad sample rollback");
    rejects([&] { invalid.update(0,cat(food)); });
    rejects([&] { invalid.update(1,cat(food),sample(Behavior::Eating,1,std::numeric_limits<double>::infinity())); });
    Pipeline reused(c); reused.update(0,cat(food),sample(Behavior::Eating,0));
    check(!reused.update(100,cat(food),sample(Behavior::Eating,0)).behavior_accepted, "same sample not counted twice");
    auto long_min = c; long_min.temporal.min_state_ms = 2000;
    Pipeline minimum(long_min); start(minimum,food,Behavior::Eating);
    for (Millis now = 1200; now < 3000; now += 200)
        check(minimum.update(now,cat(food),sample(Behavior::Unknown,now)).events.empty(), "minimum active duration");
    check(minimum.update(3000,cat(food)).events.size() == 1, "minimum duration eventually ends unknown");
    // Different sample rates yield the same elapsed-time confirmation boundary.
    for (Millis interval : {Millis(50),Millis(100),Millis(200),Millis(250)}) {
        Pipeline rate(c);
        for (Millis now = 0; now <= 1000; now += interval) {
            out = rate.update(now,cat(food),sample(Behavior::Eating,now));
            check((now == 1000) == !out.events.empty(), "FPS-independent confirmation");
        }
    }
    check(event_json(ended).find("\"consumed_grams\":null") != std::string::npos, "JSON weight null");
    rejects([&] { Pipeline bad(c,{std::string(129,'a'),""}); });
    rejects([&] { Pipeline bad(c,{"\n",""}); });
}
void stress(const Config& c, unsigned seed) {
    Pipeline a(c), b(c);
    std::mt19937 random(seed);
    Millis now = 0;
    std::uint64_t open_session = 0, open_track = 0;
    for (int i = 0; i < 20000; ++i) {
        now += static_cast<Millis>(1 + random() % 600u);
        const auto pick = static_cast<unsigned>(random() % 10u);
        const Box box = pick < 5 ? c.geometry.food_roi : c.geometry.water_roi;
        auto detections = pick == 0 ? std::vector<Detection>{} : cat(box);
        if (pick == 9) detections.push_back({Object::Cat,0.9,c.geometry.food_roi});
        const auto label = pick < 4 ? Behavior::Eating : (pick < 8 ? Behavior::Drinking : Behavior::Unsure);
        const auto sa = sample(label,now);
        const auto x = a.update(now,detections,sa), y = b.update(now,detections,sa);
        check(x.state == y.state && x.events.size() == y.events.size(), "deterministic replay");
        check(x.events.size() <= 2, "event output bounded");
        check(!x.track.present || x.track.value.history.size() <= c.tracker.history_capacity, "stress history bound");
        for (std::size_t j = 0; j < x.events.size(); ++j) {
            const auto& e = x.events[j];
            check(event_json(e) == event_json(y.events[j]), "identical event replay");
            check(e.shadow_only && !e.consumed_grams.present, "stress shadow-only");
            if (e.type == EventType::EatingStart || e.type == EventType::DrinkingStart) {
                check(open_session == 0, "no overlapping sessions"); open_session = e.session_id; open_track = e.track_id;
            } else {
                check(open_session == e.session_id && open_track == e.track_id, "no orphan/misattributed END");
                check(e.end_ms.present && e.duration_ms.present && e.duration_ms.value >= 0 &&
                      e.end_ms.value - e.start_ms == e.duration_ms.value && e.end_ms.value <= now, "event time invariants");
                open_session = 0;
            }
        }
    }
}
void boundary_tests(const Config& c) {
    const Box food = c.geometry.food_roi;
    check(!valid_box({0,0,1e-200,1e-200}), "underflow-area boxes rejected");
    rejects([&] { intersection_over_union({0,0,0,0},food); });
    Pipeline dog(c), body(c), flicker(c);
    for (Millis now = 0; now <= 4000; now += 100) {
        check(dog.update(now,{{Object::Dog,1,food}},sample(Behavior::Eating,now)).events.empty(), "DOG never starts cat session");
        check(body.update(now,cat({0.1,0.1,0.9,0.4}),sample(Behavior::Eating,now)).events.empty(), "ambiguous body geometry never starts");
        check(flicker.update(now,cat(food),sample(now % 200 == 0 ? Behavior::Eating : Behavior::Drinking,now)).events.empty(),
              "alternating contradictory behavior cannot accumulate confirmation");
    }
    Pipeline burst(c);
    burst.update(0,cat(food),sample(Behavior::Eating,0));
    for (Millis now = 100; now <= 3000; now += 100)
        check(burst.update(now,cat(food),sample(Behavior::Unknown,now)).events.empty(), "one-frame burst never confirms");
    Pipeline steady(c); auto began = start(steady,food,Behavior::Eating);
    for (Millis now = 1100; now <= 4000; now += 100)
        check(steady.update(now,cat(food),sample(Behavior::Eating,now)).events.empty(), "no duplicate START while stable");
    for (Millis now = 4100; now <= 4800; now += 100)
        check(steady.update(now,cat(food),sample(Behavior::Unsure,now)).events.empty(), "dropout inclusive boundary");
    const auto late = steady.update(4900,cat(food),sample(Behavior::Eating,4900));
    check(late.events.size() == 1 && late.events[0].type == EventType::EatingEnd, "late recovery cannot revive expired evidence");
    check(late.events[0].end_ms.value == 4800, "timeout logical end");
    Update again;
    for (Millis now = 5000; now <= 5900; now += 100) again = steady.update(now,cat(food),sample(Behavior::Eating,now));
    check(again.events.size() == 1, "late recovery must reconfirm before restart");
    check(again.events[0].session_id == began.events[0].session_id + 1, "new session after reconfirmation");
    // A long silent caller gap must not inflate the old session to the new time.
    Pipeline silent(c); start(silent,food,Behavior::Eating);
    const auto closed = silent.update(100000,{});
    check(closed.events.size() == 1 && closed.events[0].end_ms.value == 2000 && closed.events[0].emitted_ms == 100000,
          "silent gap duration bounded by last evidence/minimum state, not arrival time");
    Pipeline atomic(c);
    auto invalid = cat(food); invalid[0].confidence = -0.01;
    rejects([&] { atomic.update(0,invalid); });
    invalid = cat(food); invalid[0].object = static_cast<Object>(99);
    rejects([&] { atomic.update(0,invalid); });
    rejects([&] { atomic.update(0,std::vector<Detection>(1025,{Object::Cat,0.9,food})); });
    rejects([&] { atomic.update(0,cat(food),sample(static_cast<Behavior>(99),0)); });
    check(atomic.update(0,cat(food)).track.value.id == 1, "invalid inputs leave tracker unchanged");
    // Millisecond arithmetic remains bounded at the signed clock limit.
    auto limit_config = c; limit_config.temporal.min_state_ms = 2000;
    Pipeline limit(limit_config);
    const auto max = std::numeric_limits<Millis>::max();
    for (Millis offset = 2000; offset >= 1000; offset -= 100)
        limit.update(max - offset,cat(food),sample(Behavior::Eating,max - offset));
    const auto limit_end = limit.update(max,{});
    check(limit_end.events.size() == 1 && limit_end.events[0].end_ms.value == max, "saturating near-limit clock arithmetic");
    Event e = began.events[0]; e.consumed_grams = Maybe<double>(1);
    rejects([&] { event_json(e); });
    e = began.events[0]; e.shadow_only = false;
    rejects([&] { event_json(e); });
    const auto nested = std::string(17,'{'); // valid nesting with keys, rejected by depth budget
    std::string deep;
    for (std::size_t i = 0; i < nested.size(); ++i) deep += "{\"n\":";
    deep += "null" + std::string(nested.size(),'}');
    rejects([&] { load_config_json(deep,true); });
    rejects([&] { load_config_json("{\"n\":\"" + std::string(4097,'a') + "\"}",true); });
}
} // namespace
int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::invalid_argument("usage: test_behavior_shadow synthetic.json unconfigured.json");
        const auto json = read(argv[1]); const auto config = behavior_shadow::load_config_json(json,true);
        configuration_tests(json,read(argv[2])); std::cout << "PASS configuration + malformed/mutation inputs\n";
        tracker_tests(config); std::cout << "PASS tracker + TTL + bounded history\n";
        geometry_tests(config); std::cout << "PASS geometry + hysteresis + motion\n";
        temporal_tests(config); std::cout << "PASS temporal/FSM + event contracts\n";
        boundary_tests(config); std::cout << "PASS contradictory evidence + silent gap + numeric/input budgets\n";
        std::atomic<bool> failed{false};
        std::vector<std::thread> workers;
        for (unsigned i = 0; i < 4; ++i) workers.emplace_back([&,i] {
            try { stress(config,100 + i); } catch (const std::exception& e) { std::cerr << e.what() << '\n'; failed = true; }
        });
        for (auto& thread : workers) thread.join();
        check(!failed, "independent-pipeline stress failed");
        std::cout << "PASS 80000 paired replay updates across four independent owner threads\n"
                  << checks.load() << " checks PASS (offline/synthetic; not physical validation)\n";
        return 0;
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
