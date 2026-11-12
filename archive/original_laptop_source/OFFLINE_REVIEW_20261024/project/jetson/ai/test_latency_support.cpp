#include "latency_support.h"
#include <atomic>
#include <cstdlib>
#include <future>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <thread>

namespace {
unsigned checks = 0;
void check(bool value) {
    ++checks;
    if (!value) throw std::runtime_error("latency support check failed");
}
void contract_tests() {
    using latency::Binding;
    const std::vector<Binding> valid{{true, true, {1,3,320,320}}, {false, true, {1,84,2100}}};
    check(latency::binding_error(valid, false).empty());
    check(!latency::binding_error(valid, true).empty());
    check(!latency::binding_error({}, false).empty());
    auto wrong = valid;
    wrong.push_back(valid[0]);
    check(!latency::binding_error(wrong, false).empty());
    wrong = valid; wrong[0].input = false;
    check(!latency::binding_error(wrong, false).empty());
    wrong = valid; wrong[1].input = true;
    check(!latency::binding_error(wrong, false).empty());
    wrong = valid; wrong[0].float32 = false;
    check(!latency::binding_error(wrong, false).empty());
    wrong = valid; wrong[1].float32 = false;
    check(!latency::binding_error(wrong, false).empty());
    wrong = valid; wrong[0].dimensions[2] = -1;
    check(!latency::binding_error(wrong, false).empty());
    wrong = valid; wrong[1].dimensions = {1,7,2100};
    check(!latency::binding_error(wrong, false).empty());
    wrong = valid; wrong[1].dimensions = {1,2100,84};
    check(!latency::binding_error(wrong, false).empty());
}
void ownership_tests() {
    latency::LatestSlot<std::unique_ptr<int>> slot;
    const auto now = latency::Clock::now();
    check(slot.publish(std::unique_ptr<int>(new int(1)), now, 2));
    check(slot.publish(std::unique_ptr<int>(new int(2)), now, 3, 12345));
    latency::Packet<std::unique_ptr<int>> packet;
    check(slot.take(packet, std::chrono::milliseconds(1)));
    check(*packet.image == 2 && packet.sequence == 2 && packet.read_ms == 3 && packet.driver_ms == 12345);
    check(slot.publish(std::unique_ptr<int>(new int(3)), now, 4));
    check(*packet.image == 2); // producer cannot overwrite the consumer-owned image
    slot.close();
    check(!slot.publish(std::unique_ptr<int>(new int(4)), now, 5));
    check(slot.take(packet, std::chrono::milliseconds(1)) && *packet.image == 3);
    check(!slot.take(packet, std::chrono::milliseconds(1)));
    const auto counts = slot.counts();
    check(counts.captured == 3 && counts.delivered == 2 && counts.replaced == 1 && !counts.pending);
}
void wakeup_test() {
    latency::LatestSlot<int> slot;
    std::promise<void> started;
    auto done = std::async(std::launch::async, [&] {
        latency::Packet<int> packet;
        started.set_value();
        return slot.take(packet, std::chrono::milliseconds(5000));
    });
    started.get_future().wait();
    slot.close();
    check(done.wait_for(std::chrono::seconds(1)) == std::future_status::ready);
    check(!done.get());
}
void stress_test() {
    latency::LatestSlot<int> slot;
    constexpr int iterations = 20000;
    std::atomic<bool> failed{false};
    std::thread producer([&] {
        for (int i = 1; i <= iterations; ++i) slot.publish(i, latency::Clock::now(), 0);
        slot.close();
    });
    std::uint64_t last = 0;
    latency::Packet<int> packet;
    while (slot.take(packet, std::chrono::milliseconds(1000))) {
        if (packet.sequence <= last || packet.sequence != static_cast<std::uint64_t>(packet.image)) failed.store(true);
        last = packet.sequence;
    }
    producer.join();
    const auto counts = slot.counts();
    check(!failed.load());
    check(last == iterations);
    check(counts.captured == iterations);
    check(counts.captured == counts.delivered + counts.replaced && !counts.pending);
}
}

int main() {
    try {
        contract_tests(); ownership_tests(); wakeup_test(); stress_test();
        std::cout << "Latency support: " << checks << " checks PASS; 20000-publication concurrency stress PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
