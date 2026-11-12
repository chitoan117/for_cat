#pragma once

// C++14, dependency-free capture handoff and engine-contract checks.
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <string>
#include <utility>
#include <vector>

namespace latency {
using Clock = std::chrono::steady_clock;
inline double milliseconds(Clock::time_point first, Clock::time_point last) {
    return std::chrono::duration<double, std::milli>(last - first).count();
}

template <class T> struct Packet {
    T image{};
    Clock::time_point received{}; // after read(), NOT sensor exposure time
    double read_ms = 0;
    double driver_ms = 0; // optional OpenCV V4L2 buffer timestamp; clock checked by consumer
    std::uint64_t sequence = 0;
};

struct CaptureCounts {
    std::uint64_t captured = 0;
    std::uint64_t delivered = 0;
    std::uint64_t replaced = 0;
    bool pending = false;
};

template <class T> class LatestSlot {
public:
    bool publish(T image, Clock::time_point received, double read_ms, double driver_ms = 0) {
        {
            std::lock_guard<std::mutex> guard(mutex_);
            if (closed_) return false;
            if (counts_.pending) ++counts_.replaced;
            latest_.image = std::move(image);
            latest_.received = received;
            latest_.read_ms = read_ms;
            latest_.driver_ms = driver_ms;
            latest_.sequence = ++counts_.captured;
            counts_.pending = true;
        }
        ready_.notify_one();
        return true;
    }

    bool take(Packet<T>& packet, std::chrono::milliseconds timeout) {
        std::unique_lock<std::mutex> guard(mutex_);
        ready_.wait_for(guard, timeout, [this] { return counts_.pending || closed_; });
        if (!counts_.pending) return false;
        packet = std::move(latest_);
        counts_.pending = false;
        ++counts_.delivered;
        return true;
    }

    void close() {
        {
            std::lock_guard<std::mutex> guard(mutex_);
            closed_ = true;
        }
        ready_.notify_all();
    }

    CaptureCounts counts() const {
        std::lock_guard<std::mutex> guard(mutex_);
        return counts_;
    }

private:
    mutable std::mutex mutex_;
    std::condition_variable ready_;
    Packet<T> latest_{};
    CaptureCounts counts_{};
    bool closed_ = false;
};

struct Binding {
    bool input;
    bool float32;
    std::vector<int> dimensions;
};

inline std::string binding_error(const std::vector<Binding>& bindings, bool implicit_batch) {
    if (implicit_batch) return "explicit batch required";
    if (bindings.size() != 2) return "exactly two bindings required";
    if (!bindings[0].input || bindings[1].input) return "binding 0 must be INPUT; binding 1 must be OUTPUT";
    if (!bindings[0].float32 || !bindings[1].float32) return "both I/O bindings must be FLOAT32 (internal FP16 is allowed)";
    if (bindings[0].dimensions != std::vector<int>({1, 3, 320, 320})) return "input must be 1x3x320x320";
    if (bindings[1].dimensions != std::vector<int>({1, 84, 2100})) return "output must be 1x84x2100 COCO layout";
    return {};
}
} // namespace latency
