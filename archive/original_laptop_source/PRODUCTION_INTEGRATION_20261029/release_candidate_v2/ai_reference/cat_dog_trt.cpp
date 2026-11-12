#include <NvInfer.h>
#include <cuda_runtime_api.h>

#include <opencv2/opencv.hpp>
#include <opencv2/dnn/dnn.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

using namespace nvinfer1;

static const char* ENGINE_PATH =
    "/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine";

static constexpr int INPUT_W = 320;
static constexpr int INPUT_H = 320;

static constexpr int CAT_ID = 15;
static constexpr int DOG_ID = 16;

static constexpr float CONF_THRESHOLD = 0.35f;
static constexpr float NMS_THRESHOLD = 0.45f;

class Logger : public ILogger
{
public:
    void log(Severity severity, const char* msg) noexcept override
    {
        if (severity <= Severity::kWARNING)
            std::cout << "[TensorRT] " << msg << std::endl;
    }
};

Logger gLogger;

struct Detection
{
    int classId;
    float confidence;
    cv::Rect box;
};

struct LetterboxInfo
{
    float scale;
    int padX;
    int padY;
};

static bool cudaCheck(cudaError_t result, const char* where)
{
    if (result != cudaSuccess)
    {
        std::cerr
            << "CUDA ERROR at "
            << where
            << ": "
            << cudaGetErrorString(result)
            << std::endl;

        return false;
    }

    return true;
}

cv::Mat letterbox(
    const cv::Mat& frame,
    LetterboxInfo& info)
{
    int originalW = frame.cols;
    int originalH = frame.rows;

    float scaleW =
        static_cast<float>(INPUT_W) /
        static_cast<float>(originalW);

    float scaleH =
        static_cast<float>(INPUT_H) /
        static_cast<float>(originalH);

    info.scale = std::min(
        scaleW,
        scaleH
    );

    int newW = static_cast<int>(
        std::round(
            originalW * info.scale
        )
    );

    int newH = static_cast<int>(
        std::round(
            originalH * info.scale
        )
    );

    info.padX = (INPUT_W - newW) / 2;
    info.padY = (INPUT_H - newH) / 2;

    cv::Mat resized;

    cv::resize(
        frame,
        resized,
        cv::Size(newW, newH)
    );

    cv::Mat output(
        INPUT_H,
        INPUT_W,
        CV_8UC3,
        cv::Scalar(114, 114, 114)
    );

    resized.copyTo(
        output(
            cv::Rect(
                info.padX,
                info.padY,
                newW,
                newH
            )
        )
    );

    return output;
}

void preprocess(
    const cv::Mat& frame,
    float* input,
    LetterboxInfo& info)
{
    cv::Mat image =
        letterbox(frame, info);

    cv::cvtColor(
        image,
        image,
        cv::COLOR_BGR2RGB
    );

    const int area =
        INPUT_W * INPUT_H;

    for (int y = 0; y < INPUT_H; ++y)
    {
        for (int x = 0; x < INPUT_W; ++x)
        {
            cv::Vec3b pixel =
                image.at<cv::Vec3b>(y, x);

            int index =
                y * INPUT_W + x;

            input[index] =
                pixel[0] / 255.0f;

            input[area + index] =
                pixel[1] / 255.0f;

            input[2 * area + index] =
                pixel[2] / 255.0f;
        }
    }
}

std::vector<Detection> postprocess(
    const float* output,
    const cv::Size& originalSize,
    const LetterboxInfo& info)
{
    constexpr int NUM_PREDICTIONS = 2100;
    constexpr int NUM_CHANNELS = 84;

    (void)NUM_CHANNELS;

    std::vector<cv::Rect> catBoxes;
    std::vector<float> catScores;

    std::vector<cv::Rect> dogBoxes;
    std::vector<float> dogScores;

    for (int i = 0;
         i < NUM_PREDICTIONS;
         ++i)
    {
        float catScore =
            output[
                (4 + CAT_ID) *
                NUM_PREDICTIONS + i
            ];

        float dogScore =
            output[
                (4 + DOG_ID) *
                NUM_PREDICTIONS + i
            ];

        int classId;
        float score;

        if (catScore >= dogScore)
        {
            classId = CAT_ID;
            score = catScore;
        }
        else
        {
            classId = DOG_ID;
            score = dogScore;
        }

        if (score < CONF_THRESHOLD)
            continue;

        float cx =
            output[
                0 * NUM_PREDICTIONS + i
            ];

        float cy =
            output[
                1 * NUM_PREDICTIONS + i
            ];

        float w =
            output[
                2 * NUM_PREDICTIONS + i
            ];

        float h =
            output[
                3 * NUM_PREDICTIONS + i
            ];

        float x1 =
            (cx - w / 2.0f - info.padX)
            / info.scale;

        float y1 =
            (cy - h / 2.0f - info.padY)
            / info.scale;

        float x2 =
            (cx + w / 2.0f - info.padX)
            / info.scale;

        float y2 =
            (cy + h / 2.0f - info.padY)
            / info.scale;

        x1 = std::max(
            0.0f,
            std::min(
                x1,
                static_cast<float>(
                    originalSize.width - 1
                )
            )
        );

        y1 = std::max(
            0.0f,
            std::min(
                y1,
                static_cast<float>(
                    originalSize.height - 1
                )
            )
        );

        x2 = std::max(
            0.0f,
            std::min(
                x2,
                static_cast<float>(
                    originalSize.width - 1
                )
            )
        );

        y2 = std::max(
            0.0f,
            std::min(
                y2,
                static_cast<float>(
                    originalSize.height - 1
                )
            )
        );

        int boxX =
            static_cast<int>(x1);

        int boxY =
            static_cast<int>(y1);

        int boxW =
            static_cast<int>(x2 - x1);

        int boxH =
            static_cast<int>(y2 - y1);

        if (boxW <= 1 || boxH <= 1)
            continue;

        cv::Rect box(
            boxX,
            boxY,
            boxW,
            boxH
        );

        if (classId == CAT_ID)
        {
            catBoxes.push_back(box);
            catScores.push_back(score);
        }
        else
        {
            dogBoxes.push_back(box);
            dogScores.push_back(score);
        }
    }

    std::vector<Detection> results;

    std::vector<int> catIndices;

    cv::dnn::NMSBoxes(
        catBoxes,
        catScores,
        CONF_THRESHOLD,
        NMS_THRESHOLD,
        catIndices
    );

    for (int index : catIndices)
    {
        Detection d;

        d.classId = CAT_ID;
        d.confidence = catScores[index];
        d.box = catBoxes[index];

        results.push_back(d);
    }

    std::vector<int> dogIndices;

    cv::dnn::NMSBoxes(
        dogBoxes,
        dogScores,
        CONF_THRESHOLD,
        NMS_THRESHOLD,
        dogIndices
    );

    for (int index : dogIndices)
    {
        Detection d;

        d.classId = DOG_ID;
        d.confidence = dogScores[index];
        d.box = dogBoxes[index];

        results.push_back(d);
    }

    return results;
}

#include <stdexcept>
#include "latency_runtime.h"

namespace {
static_assert(ATOMIC_BOOL_LOCK_FREE == 2, "signal stop requires a lock-free atomic bool");
std::atomic<bool> interrupted{false};
void onSignal(int) { interrupted.store(true, std::memory_order_relaxed); }

template <class T> struct TrtDestroy {
    void operator()(T* object) const { if (object) object->destroy(); }
};
struct GpuResources {
    void* buffers[2]{nullptr, nullptr};
    cudaStream_t stream = nullptr;
    cudaEvent_t events[4]{nullptr, nullptr, nullptr, nullptr};
    ~GpuResources() {
        if (stream) cudaStreamSynchronize(stream);
        for (auto event : events) if (event) cudaEventDestroy(event);
        if (stream) cudaStreamDestroy(stream);
        for (auto buffer : buffers) if (buffer) cudaFree(buffer);
    }
};
void checked(cudaError_t result, const char* operation) {
    if (!cudaCheck(result, operation)) throw std::runtime_error(operation);
}

int run(const latency::Options& options) {
    using latency::Clock;
    using latency::milliseconds;
    std::ifstream file(options.engine, std::ios::binary | std::ios::ate);
    if (!file || file.tellg() <= 0 || file.tellg() > 512 * 1024 * 1024)
        throw std::runtime_error("engine missing/empty/oversized: " + options.engine);
    const auto size = static_cast<std::size_t>(file.tellg());
    std::vector<char> bytes(size);
    file.seekg(0);
    if (!file.read(bytes.data(), static_cast<std::streamsize>(size))) throw std::runtime_error("engine read failed");
    std::unique_ptr<IRuntime, TrtDestroy<IRuntime>> runtime(createInferRuntime(gLogger));
    if (!runtime) throw std::runtime_error("TensorRT runtime creation failed");
    std::unique_ptr<ICudaEngine, TrtDestroy<ICudaEngine>> engine(runtime->deserializeCudaEngine(bytes.data(), size));
    if (!engine) throw std::runtime_error("engine deserialization failed");
    std::vector<latency::Binding> bindings;
    for (int index = 0; index < engine->getNbBindings(); ++index) {
        const auto dims = engine->getBindingDimensions(index);
        std::cout << "Binding storage " << index << " format=" << engine->getBindingFormatDesc(index)
                  << " vectorized_dim=" << engine->getBindingVectorizedDim(index) << '\n';
        if (engine->getBindingFormat(index) != TensorFormat::kLINEAR || engine->getBindingVectorizedDim(index) != -1)
            throw std::runtime_error("ENGINE_CONTRACT_MISMATCH: unvectorized linear I/O required");
        latency::Binding binding{engine->bindingIsInput(index), engine->getBindingDataType(index) == DataType::kFLOAT, {}};
        std::cout << "Binding " << index << ' ' << (binding.input ? "INPUT " : "OUTPUT ")
                  << engine->getBindingName(index) << " dtype=" << static_cast<int>(engine->getBindingDataType(index)) << " shape=";
        for (int dimension = 0; dimension < dims.nbDims; ++dimension) {
            binding.dimensions.push_back(dims.d[dimension]);
            std::cout << (dimension ? "x" : "") << dims.d[dimension];
        }
        std::cout << '\n';
        bindings.push_back(binding);
    }
    const auto contract = latency::binding_error(bindings, engine->hasImplicitBatchDimension());
    if (!contract.empty()) throw std::runtime_error("ENGINE_CONTRACT_MISMATCH: " + contract);
    std::cout << "ENGINE_CONTRACT=PASS; COCO CAT=15 DOG=16; monitoring only; no actuator path\n";
    std::unique_ptr<IExecutionContext, TrtDestroy<IExecutionContext>> context(engine->createExecutionContext());
    if (!context) throw std::runtime_error("execution context creation failed");
    constexpr std::size_t input_count = 1 * 3 * INPUT_H * INPUT_W;
    constexpr std::size_t output_count = 1 * 84 * 2100;
    std::vector<float> input(input_count), output(output_count);
    GpuResources gpu;
    checked(cudaMalloc(&gpu.buffers[0], input_count * sizeof(float)), "allocate input");
    checked(cudaMalloc(&gpu.buffers[1], output_count * sizeof(float)), "allocate output");
    checked(cudaStreamCreate(&gpu.stream), "create stream");
    for (auto& event : gpu.events) checked(cudaEventCreate(&event), "create event");
    // Created after GPU objects so capture joins before context/buffers are destroyed.
    latency::Capture capture(options.latest);
    capture.open(options);
    std::cout << "GUI=" << options.gui << " SNAPSHOT=" << (!options.gui && options.snapshot)
              << " WARMUP_FRAMES=" << options.warmup
              << " FRAME_AGE=app-read-complete-to-output-complete; not exposure latency\n";
    latency::Statistics statistics;
    std::uint64_t processed = 0, sequence = 0;
    unsigned sequential_failures = 0;
    double last_driver_timestamp = 0;
    const auto startup = Clock::now();
    auto measured_start = startup, last_report = startup, last_save = startup;
    bool measuring = options.warmup == 0;
    while (!interrupted.load(std::memory_order_relaxed)) {
        const auto now = Clock::now();
        if (options.seconds > 0 && measuring && milliseconds(measured_start, now) >= options.seconds * 1000) break;
        if (!measuring && milliseconds(startup, now) > 30000) throw std::runtime_error("warmup deadline exceeded");
        latency::Packet<cv::Mat> packet;
        if (!capture.take(packet)) {
            if (capture.failed() || (!options.latest && ++sequential_failures >= 3)) throw std::runtime_error("camera read failure budget exhausted");
            if (!options.latest) std::this_thread::sleep_for(std::chrono::milliseconds(50));
            continue;
        }
        sequential_failures = 0;
        if (packet.sequence <= sequence) throw std::runtime_error("non-increasing frame sequence");
        sequence = packet.sequence;
        if (processed == 0) std::cout << std::fixed << std::setprecision(3) << "DRIVER_TIMESTAMP_ms=" << packet.driver_ms
            << " HOST_MONOTONIC_ms=" << std::chrono::duration<double, std::milli>(Clock::now().time_since_epoch()).count() << '\n';
        cv::Mat frame = std::move(packet.image);
        latency::Metrics metrics;
        metrics.queue = milliseconds(packet.received, Clock::now());
        metrics.read = packet.read_ms;
        LetterboxInfo info;
        const auto pre_start = Clock::now();
        preprocess(frame, input.data(), info);
        metrics.pre = milliseconds(pre_start, Clock::now());
        const auto ai_start = Clock::now();
        checked(cudaEventRecord(gpu.events[0], gpu.stream), "event H2D begin");
        checked(cudaMemcpyAsync(gpu.buffers[0], input.data(), input_count * sizeof(float), cudaMemcpyHostToDevice, gpu.stream), "H2D");
        checked(cudaEventRecord(gpu.events[1], gpu.stream), "event H2D end");
        const auto enqueue_start = Clock::now();
        if (!context->enqueueV2(gpu.buffers, gpu.stream, nullptr)) throw std::runtime_error("TensorRT enqueue failed");
        metrics.enqueue = milliseconds(enqueue_start, Clock::now());
        checked(cudaEventRecord(gpu.events[2], gpu.stream), "event TRT end");
        checked(cudaMemcpyAsync(output.data(), gpu.buffers[1], output_count * sizeof(float), cudaMemcpyDeviceToHost, gpu.stream), "D2H");
        checked(cudaEventRecord(gpu.events[3], gpu.stream), "event D2H end");
        const auto sync_start = Clock::now();
        checked(cudaStreamSynchronize(gpu.stream), "inference synchronize");
        metrics.sync = milliseconds(sync_start, Clock::now());
        metrics.ai = milliseconds(ai_start, Clock::now());
        float h2d = 0, trt = 0, d2h = 0;
        checked(cudaEventElapsedTime(&h2d, gpu.events[0], gpu.events[1]), "time H2D");
        checked(cudaEventElapsedTime(&trt, gpu.events[1], gpu.events[2]), "time TRT");
        checked(cudaEventElapsedTime(&d2h, gpu.events[2], gpu.events[3]), "time D2H");
        metrics.h2d = h2d; metrics.trt = trt; metrics.d2h = d2h;
        const auto post_start = Clock::now();
        const auto detections = postprocess(output.data(), frame.size(), info);
        for (const auto& detection : detections) {
            char text[64];
            std::snprintf(text, sizeof(text), "%s %.2f", detection.classId == CAT_ID ? "CAT" : "DOG", detection.confidence);
            cv::rectangle(frame, detection.box, cv::Scalar(0,255,0), 2);
            cv::putText(frame, text, cv::Point(detection.box.x, std::max(20, detection.box.y-8)),
                        cv::FONT_HERSHEY_SIMPLEX, 0.7, cv::Scalar(0,255,0), 2);
        }
        metrics.post = milliseconds(post_start, Clock::now());
        bool quit = false;
        if (options.gui) {
            const auto begin = Clock::now();
            cv::imshow("FOR_CAT TensorRT", frame);
            quit = (cv::waitKey(1) & 0xff) == 'q';
            metrics.display = milliseconds(begin, Clock::now());
        } else if (options.snapshot && milliseconds(last_save, Clock::now()) >= 1000) {
            const auto begin = Clock::now();
            if (!cv::imwrite(options.snapshot_path, frame)) throw std::runtime_error("snapshot write failed");
            last_save = Clock::now();
            metrics.snapshot = milliseconds(begin, last_save);
            metrics.snapshot_written = true;
        }
        metrics.age = milliseconds(packet.received, Clock::now());
        const double driver_age = std::chrono::duration<double, std::milli>(Clock::now().time_since_epoch()).count() - packet.driver_ms;
        if (std::isfinite(packet.driver_ms) && packet.driver_ms > last_driver_timestamp && driver_age >= 0 && driver_age < 60000) {
            metrics.driver_age = driver_age;
            last_driver_timestamp = packet.driver_ms;
        }
        ++processed;
        if (measuring) statistics.add(metrics);
        else if (processed >= static_cast<std::uint64_t>(options.warmup)) {
            measuring = true;
            measured_start = last_report = Clock::now();
        }
        if (measuring && milliseconds(last_report, Clock::now()) >= 1000) {
            std::cout << (detections.empty() ? "NONE" : "DETECTIONS");
            for (const auto& detection : detections) std::cout << ' ' << (detection.classId == CAT_ID ? "CAT" : "DOG") << '=' << detection.confidence;
            statistics.print("", options, milliseconds(measured_start, Clock::now())/1000,
                             capture.counts(), processed, sequence, capture.failures());
            last_report = Clock::now();
        }
        if (quit) break;
    }
    const double elapsed = milliseconds(measured_start, Clock::now()) / 1000;
    const auto stopping = Clock::now();
    capture.stop();
    if (options.gui) cv::destroyAllWindows();
    statistics.print("SUMMARY", options, elapsed, capture.counts(), processed, sequence, capture.failures());
    std::cout << "CAPTURE_APP_FPS=" << static_cast<double>(capture.counts().captured)/(milliseconds(startup, Clock::now())/1000) << '\n';
    std::cout << "SHUTDOWN_ms=" << milliseconds(stopping, Clock::now()) << '\n';
    return statistics.frames ? 0 : 2;
}
}

int main(int argc, char** argv) {
    std::signal(SIGINT, onSignal);
    std::signal(SIGTERM, onSignal);
    try { return run(latency::options(argc, argv)); }
    catch (const std::exception& error) { std::cerr << "FOR_CAT_ERROR: " << error.what() << '\n'; return 1; }
}
