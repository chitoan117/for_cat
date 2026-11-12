#pragma once

// OpenCV capture/statistics helpers. Inference remains on the main thread.
#include "latency_support.h"
#include <atomic>
#include <csignal>
#include <deque>
#include <iomanip>
#include <thread>

namespace latency {
struct Options {
    bool latest = true;
    bool gui = std::getenv("DISPLAY") && *std::getenv("DISPLAY");
    bool snapshot = true;
    double seconds = 0; // zero = operator-controlled continuous runtime
    int warmup = 5;
    int camera_buffers = 2; // one V4L2 buffer measured 15 FPS on the target webcam
    std::string engine = ENGINE_PATH;
    std::string device = "/dev/video0";
    std::string snapshot_path = "/home/toan/for_cat/latest.jpg";
};

inline Options options(int argc, char** argv) {
    Options result;
    for (int index = 1; index < argc; ++index) {
        const std::string arg = argv[index];
        if (arg == "--headless") result.gui = false;
        else if (arg == "--gui") result.gui = true;
        else if (arg == "--no-snapshot") result.snapshot = false;
        else if (arg == "--help") {
            std::cout << "--capture-mode latest|sequential --headless --gui --no-snapshot "
                         "--seconds N --warmup-frames N --camera-buffers 1|2|4 --device PATH --engine PATH --snapshot-path PATH\n";
            std::exit(0);
        } else {
            if (++index >= argc) throw std::runtime_error("missing value for " + arg);
            const std::string value = argv[index];
            if (arg == "--capture-mode") {
                if (value != "latest" && value != "sequential") throw std::runtime_error("invalid capture mode");
                result.latest = value == "latest";
            } else if (arg == "--seconds") {
                std::size_t end = 0;
                result.seconds = std::stod(value, &end);
                if (end != value.size() || !std::isfinite(result.seconds) || result.seconds <= 0 || result.seconds > 3600)
                    throw std::runtime_error("seconds must be finite, >0 and <=3600");
            } else if (arg == "--warmup-frames") {
                std::size_t end = 0;
                result.warmup = std::stoi(value, &end);
                if (end != value.size() || result.warmup < 0 || result.warmup > 100) throw std::runtime_error("invalid warmup frames");
            } else if (arg == "--camera-buffers") {
                if (value != "1" && value != "2" && value != "4") throw std::runtime_error("camera buffers must be 1, 2 or 4");
                result.camera_buffers = std::stoi(value);
            } else if (arg == "--device") result.device = value;
            else if (arg == "--engine") result.engine = value;
            else if (arg == "--snapshot-path") result.snapshot_path = value;
            else throw std::runtime_error("unknown option " + arg);
        }
    }
    return result;
}

class Capture {
public:
    explicit Capture(bool latest) : latest_(latest) {}
    Capture(const Capture&) = delete;
    Capture& operator=(const Capture&) = delete;
    ~Capture() { stop(); }

    void open(const Options& settings) {
        // OpenCV V4L2 select timeout, not a claim of driver-level cancellation.
        // Configure before threads; no cross-thread release() on a reading cap.
        ::setenv("OPENCV_VIDEOIO_V4L_SELECT_TIMEOUT", "1", 0);
        if (!camera_.open(settings.device, cv::CAP_V4L2)) throw std::runtime_error("cannot open " + settings.device);
        camera_.set(cv::CAP_PROP_FOURCC, cv::VideoWriter::fourcc('M', 'J', 'P', 'G'));
        camera_.set(cv::CAP_PROP_FRAME_WIDTH, 640);
        camera_.set(cv::CAP_PROP_FRAME_HEIGHT, 480);
        camera_.set(cv::CAP_PROP_FPS, 30);
        // Sequential is the instrumented pre-patch baseline: keep original buffer policy.
        const bool buffer = latest_ && camera_.set(cv::CAP_PROP_BUFFERSIZE, 1);
        // The target accepts one buffer but then delivers only 15 FPS. Two driver
        // buffers avoid capture starvation; the application still has ONE slot.
        const bool selected_buffer = latest_ && settings.camera_buffers != 1 &&
                                     camera_.set(cv::CAP_PROP_BUFFERSIZE, settings.camera_buffers);
        const int code = static_cast<int>(camera_.get(cv::CAP_PROP_FOURCC));
        std::string fourcc;
        for (int shift = 0; shift < 32; shift += 8) fourcc += static_cast<char>((code >> shift) & 255);
        std::cout << "Camera requested: 640x480 @30 MJPG\nCamera actual: "
                  << camera_.get(cv::CAP_PROP_FRAME_WIDTH) << 'x' << camera_.get(cv::CAP_PROP_FRAME_HEIGHT)
                  << " @" << camera_.get(cv::CAP_PROP_FPS) << ' ' << fourcc
                  << " backend=" << camera_.getBackendName() << '\n'
                  << "CAP_PROP_BUFFERSIZE request: " << (!latest_ ? "BASELINE_UNCHANGED" : buffer ? "OK" : "NOT_SUPPORTED")
                  << " selected_request=" << (latest_ ? settings.camera_buffers : 0)
                  << " selected_set=" << (settings.camera_buffers == 1 ? buffer : selected_buffer)
                  << " reported=" << camera_.get(cv::CAP_PROP_BUFFERSIZE) << '\n';
        if (latest_) worker_ = std::thread([this] { loop(); });
    }

    bool take(Packet<cv::Mat>& packet) {
        if (latest_) return slot_.take(packet, std::chrono::milliseconds(100));
        cv::Mat frame;
        const auto begin = Clock::now();
        if (!read(frame)) return false;
        packet.received = Clock::now();
        packet.read_ms = milliseconds(begin, packet.received);
        packet.image = std::move(frame);
        packet.driver_ms = last_driver_ms_;
        packet.sequence = ++sequential_count_;
        return true;
    }

    CaptureCounts counts() const {
        if (latest_) return slot_.counts();
        CaptureCounts result;
        result.captured = result.delivered = sequential_count_;
        return result;
    }
    bool failed() const { return failed_.load(); }
    unsigned failures() const { return failures_.load(); }
    void stop() {
        stop_.store(true);
        slot_.close();
        if (worker_.joinable()) worker_.join();
        camera_.release();
    }

private:
    bool read(cv::Mat& frame) {
        try {
            if (camera_.read(frame) && !frame.empty()) {
                last_driver_ms_ = camera_.get(cv::CAP_PROP_POS_MSEC);
                return true;
            }
        } catch (const cv::Exception&) {}
        failures_.fetch_add(1);
        return false;
    }
    void loop() {
        unsigned consecutive = 0;
        while (!stop_.load()) {
            cv::Mat frame; // independent ownership each read; never reused after publish
            const auto began = Clock::now();
            if (!read(frame)) {
                if (++consecutive >= 3) { failed_.store(true); break; }
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                continue;
            }
            consecutive = 0;
            const auto received = Clock::now();
            if (!slot_.publish(std::move(frame), received, milliseconds(began, received), last_driver_ms_)) break;
        }
        slot_.close();
    }
    bool latest_;
    cv::VideoCapture camera_;
    LatestSlot<cv::Mat> slot_;
    std::thread worker_;
    std::atomic<bool> stop_{false}, failed_{false};
    std::atomic<unsigned> failures_{0};
    std::uint64_t sequential_count_ = 0; // main-thread-only in sequential mode
    double last_driver_ms_ = 0; // only touched by the active reader, never shared directly
};

struct Metrics {
    double pre = 0, ai = 0, h2d = 0, trt = 0, d2h = 0, enqueue = 0, sync = 0;
    double post = 0, display = 0, snapshot = 0, age = 0, queue = 0, read = 0;
    bool snapshot_written = false;
    double driver_age = -1;
};

class Statistics {
public:
    void add(const Metrics& value) {
        ++frames;
        pre += value.pre; ai += value.ai; h2d += value.h2d; trt += value.trt; d2h += value.d2h;
        enqueue += value.enqueue; sync += value.sync; post += value.post;
        display += value.display; snapshot += value.snapshot; age += value.age;
        if (value.snapshot_written) ++snapshot_writes;
        if (value.driver_age >= 0) {
            driver_age += value.driver_age;
            ++driver_frames;
            driver_ages.push_back(value.driver_age);
            if (driver_ages.size() > 4096) driver_ages.pop_front();
        }
        queue += value.queue; read += value.read;
        ages.push_back(value.age);
        if (ages.size() > 4096) ages.pop_front();
    }
    void print(const char* prefix, const Options& settings, double elapsed, const CaptureCounts& capture,
               std::uint64_t total, std::uint64_t sequence, unsigned read_failures) const {
        const double count = static_cast<double>(frames ? frames : 1);
        auto sorted = std::vector<double>(ages.begin(), ages.end());
        std::sort(sorted.begin(), sorted.end());
        const double p95 = sorted.empty() ? 0 : sorted[static_cast<std::size_t>(0.95 * static_cast<double>(sorted.size() - 1))];
        auto driver_sorted = std::vector<double>(driver_ages.begin(), driver_ages.end());
        std::sort(driver_sorted.begin(), driver_sorted.end());
        const double driver_p95 = driver_sorted.empty() ? -1 : driver_sorted[static_cast<std::size_t>(0.95 * static_cast<double>(driver_sorted.size() - 1))];
        std::cout << std::fixed << std::setprecision(3) << prefix
                  << " MODE=" << (settings.latest ? "latest" : "sequential")
                  << " FPS=" << (elapsed > 0 ? static_cast<double>(frames) / elapsed : 0)
                  << " AI_ms=" << ai/count << " PRE_ms=" << pre/count
                  << " H2D_ms=" << h2d/count << " TRT_ms=" << trt/count << " D2H_ms=" << d2h/count
                  << " ENQUEUE_ms=" << enqueue/count << " SYNC_ms=" << sync/count
                  << " POST_ms=" << post/count << " DISPLAY_ms=" << display/count
                  << " SNAPSHOT_ms=" << snapshot/static_cast<double>(snapshot_writes ? snapshot_writes : 1)
                  << " SNAPSHOT_AMORTIZED_ms=" << snapshot/count << " FRAME_AGE_ms=" << age/count
                  << " AGE_P95_ms=" << p95 << " QUEUE_AGE_ms=" << queue/count << " READ_ms=" << read/count
                  << " DRIVER_AGE_ms=" << (driver_frames ? driver_age/static_cast<double>(driver_frames) : -1)
                  << " DRIVER_AGE_P95_ms=" << driver_p95 << " DRIVER_VALID=" << driver_frames
                  << " CAPTURED=" << capture.captured << " PROCESSED=" << total
                  << " MEASURED=" << frames << " DROPPED=" << capture.replaced << " SEQ=" << sequence
                  << " READ_FAILURES=" << read_failures << " SECONDS=" << elapsed << std::endl;
    }
    std::uint64_t frames = 0;
private:
    double pre = 0, ai = 0, h2d = 0, trt = 0, d2h = 0, enqueue = 0, sync = 0;
    double post = 0, display = 0, snapshot = 0, age = 0, queue = 0, read = 0;
    std::deque<double> ages;
    std::uint64_t snapshot_writes = 0;
    std::uint64_t driver_frames = 0;
    double driver_age = 0;
    std::deque<double> driver_ages;
};
} // namespace latency
