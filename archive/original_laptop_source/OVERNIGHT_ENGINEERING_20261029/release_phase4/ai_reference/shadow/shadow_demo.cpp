#include "behavior_shadow.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>

// Intentionally only a deterministic synthetic demo, never a live camera bridge.
int main(int argc, char** argv) {
    using namespace behavior_shadow;
    try {
        if (argc != 3 || std::string(argv[1]) != "--synthetic")
            throw std::invalid_argument("usage: shadow_demo --synthetic test_config.synthetic.json");
        std::ifstream file(argv[2], std::ios::binary);
        if (!file) throw std::runtime_error("cannot open config");
        std::string json;
        char ch = 0;
        while (file.get(ch)) {
            json += ch;
            if (json.size() > 65536) throw std::invalid_argument("config exceeds 64 KiB");
        }
        const auto config = load_config_json(json, true);
        Pipeline pipeline(config, {"synthetic-trial", "synthetic-food"});
        std::cerr << "SYNTHETIC SHADOW ONLY; no model, camera, persistence, weights, or actuators\n";
        // Derived from the provided fixture so no deployment coordinates are implied.
        const Box food = config.geometry.food_roi, water = config.geometry.water_roi;
        for (Millis now = 0; now <= 9000; now += 100) {
            std::vector<Detection> detections;
            Maybe<BehaviorSample> sample;
            if (now <= 2500 || (now >= 5000 && now <= 7500)) {
                const bool eating = now <= 2500;
                detections.push_back({Object::Cat, 0.95, eating ? food : water});
                BehaviorSample s; s.label = eating ? Behavior::Eating : Behavior::Drinking;
                s.confidence = 0.9; s.timestamp_ms = now; sample = Maybe<BehaviorSample>(s);
            }
            const auto out = pipeline.update(now, detections, sample);
            for (const auto& event : out.events) std::cout << event_json(event) << '\n';
        }
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 2; }
}
