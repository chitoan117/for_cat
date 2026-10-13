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

int main()
{
    std::cout
        << "=== FOR_CAT TensorRT C++ ==="
        << std::endl;

    std::ifstream engineFile(
        ENGINE_PATH,
        std::ios::binary
    );

    if (!engineFile)
    {
        std::cerr
            << "Khong mo duoc engine: "
            << ENGINE_PATH
            << std::endl;

        return 1;
    }

    engineFile.seekg(
        0,
        std::ios::end
    );

    size_t engineSize =
        static_cast<size_t>(
            engineFile.tellg()
        );

    engineFile.seekg(
        0,
        std::ios::beg
    );

    std::vector<char> engineData(
        engineSize
    );

    engineFile.read(
        engineData.data(),
        engineSize
    );

    IRuntime* runtime =
        createInferRuntime(gLogger);

    if (!runtime)
    {
        std::cerr
            << "Khong tao duoc TensorRT Runtime"
            << std::endl;

        return 1;
    }

    ICudaEngine* engine =
        runtime->deserializeCudaEngine(
            engineData.data(),
            engineSize
        );

    if (!engine)
    {
        std::cerr
            << "Khong deserialize duoc engine"
            << std::endl;

        runtime->destroy();
        return 1;
    }

    IExecutionContext* context =
        engine->createExecutionContext();

    if (!context)
    {
        std::cerr
            << "Khong tao duoc execution context"
            << std::endl;

        engine->destroy();
        runtime->destroy();

        return 1;
    }

    std::cout
        << "Engine: OK"
        << std::endl;

    std::cout
        << "Bindings: "
        << engine->getNbBindings()
        << std::endl;

    for (int i = 0;
         i < engine->getNbBindings();
         ++i)
    {
        Dims dims =
            engine->getBindingDimensions(i);

        std::cout
            << i
            << " "
            << (
                engine->bindingIsInput(i)
                ? "INPUT "
                : "OUTPUT "
            )
            << engine->getBindingName(i)
            << " shape=(";

        for (int j = 0;
             j < dims.nbDims;
             ++j)
        {
            std::cout << dims.d[j];

            if (j < dims.nbDims - 1)
                std::cout << ",";
        }

        std::cout
            << ")"
            << std::endl;
    }

    const size_t inputElements =
        1 * 3 * INPUT_H * INPUT_W;

    const size_t outputElements =
        1 * 84 * 2100;

    const size_t inputBytes =
        inputElements * sizeof(float);

    const size_t outputBytes =
        outputElements * sizeof(float);

    std::vector<float> hostInput(
        inputElements
    );

    std::vector<float> hostOutput(
        outputElements
    );

    void* deviceBuffers[2] =
    {
        nullptr,
        nullptr
    };

    if (!cudaCheck(
            cudaMalloc(
                &deviceBuffers[0],
                inputBytes
            ),
            "cudaMalloc input"))
    {
        return 1;
    }

    if (!cudaCheck(
            cudaMalloc(
                &deviceBuffers[1],
                outputBytes
            ),
            "cudaMalloc output"))
    {
        cudaFree(deviceBuffers[0]);
        return 1;
    }

    cudaStream_t stream;

    if (!cudaCheck(
            cudaStreamCreate(&stream),
            "cudaStreamCreate"))
    {
        cudaFree(deviceBuffers[0]);
        cudaFree(deviceBuffers[1]);

        return 1;
    }

    cv::VideoCapture cap(
        0,
        cv::CAP_V4L2
    );

    cap.set(
        cv::CAP_PROP_FOURCC,
        cv::VideoWriter::fourcc(
            'M',
            'J',
            'P',
            'G'
        )
    );

    cap.set(
        cv::CAP_PROP_FRAME_WIDTH,
        640
    );

    cap.set(
        cv::CAP_PROP_FRAME_HEIGHT,
        480
    );

    cap.set(
        cv::CAP_PROP_FPS,
        30
    );

    if (!cap.isOpened())
    {
        std::cerr
            << "Khong mo duoc /dev/video0"
            << std::endl;

        cudaStreamDestroy(stream);
        cudaFree(deviceBuffers[0]);
        cudaFree(deviceBuffers[1]);

        context->destroy();
        engine->destroy();
        runtime->destroy();

        return 1;
    }

    std::cout
        << "Camera: OK"
        << std::endl;

    std::cout
        << "Chi loc CAT / DOG"
        << std::endl;

    bool hasDisplay =
        std::getenv("DISPLAY") != nullptr;

    if (hasDisplay)
    {
        std::cout
            << "GUI: ON"
            << std::endl;
    }
    else
    {
        std::cout
            << "GUI: OFF - SSH headless"
            << std::endl;

        std::cout
            << "Anh moi nhat: "
            << "/home/toan/for_cat/latest.jpg"
            << std::endl;
    }

    cv::Mat frame;

    double smoothFps = 0.0;

    auto lastLog =
        std::chrono::steady_clock::now();

    auto lastSave =
        std::chrono::steady_clock::now();

    while (true)
    {
        auto frameStart =
            std::chrono::steady_clock::now();

        if (!cap.read(frame))
        {
            std::cerr
                << "Khong doc duoc frame"
                << std::endl;

            continue;
        }

        LetterboxInfo info;

        preprocess(
            frame,
            hostInput.data(),
            info
        );

        if (!cudaCheck(
                cudaMemcpyAsync(
                    deviceBuffers[0],
                    hostInput.data(),
                    inputBytes,
                    cudaMemcpyHostToDevice,
                    stream
                ),
                "H2D"))
        {
            break;
        }

        bool inferenceOK =
            context->enqueueV2(
                deviceBuffers,
                stream,
                nullptr
            );

        if (!inferenceOK)
        {
            std::cerr
                << "TensorRT inference failed"
                << std::endl;

            break;
        }

        if (!cudaCheck(
                cudaMemcpyAsync(
                    hostOutput.data(),
                    deviceBuffers[1],
                    outputBytes,
                    cudaMemcpyDeviceToHost,
                    stream
                ),
                "D2H"))
        {
            break;
        }

        if (!cudaCheck(
                cudaStreamSynchronize(stream),
                "cudaStreamSynchronize"))
        {
            break;
        }

        std::vector<Detection> detections =
            postprocess(
                hostOutput.data(),
                frame.size(),
                info
            );

        for (const Detection& d :
             detections)
        {
            std::string label;

            if (d.classId == CAT_ID)
            {
                label = "CAT";
            }
            else
            {
                label = "DOG";
            }

            char text[64];

            std::snprintf(
                text,
                sizeof(text),
                "%s %.2f",
                label.c_str(),
                d.confidence
            );

            cv::rectangle(
                frame,
                d.box,
                cv::Scalar(
                    0,
                    255,
                    0
                ),
                2
            );

            int textY =
                std::max(
                    20,
                    d.box.y - 8
                );

            cv::putText(
                frame,
                text,
                cv::Point(
                    d.box.x,
                    textY
                ),
                cv::FONT_HERSHEY_SIMPLEX,
                0.7,
                cv::Scalar(
                    0,
                    255,
                    0
                ),
                2
            );
        }

        auto frameEnd =
            std::chrono::steady_clock::now();

        double elapsed =
            std::chrono::duration<double>(
                frameEnd - frameStart
            ).count();

        double fps =
            elapsed > 0.0
            ? 1.0 / elapsed
            : 0.0;

        if (smoothFps == 0.0)
        {
            smoothFps = fps;
        }
        else
        {
            smoothFps =
                smoothFps * 0.9 +
                fps * 0.1;
        }

        char fpsText[64];

        std::snprintf(
            fpsText,
            sizeof(fpsText),
            "FPS %.1f",
            smoothFps
        );

        cv::putText(
            frame,
            fpsText,
            cv::Point(10, 30),
            cv::FONT_HERSHEY_SIMPLEX,
            0.7,
            cv::Scalar(
                255,
                255,
                255
            ),
            2
        );

        auto now =
            std::chrono::steady_clock::now();

        double logElapsed =
            std::chrono::duration<double>(
                now - lastLog
            ).count();

        if (logElapsed >= 1.0)
        {
            if (detections.empty())
            {
                std::cout
                    << "NONE | FPS "
                    << smoothFps
                    << std::endl;
            }
            else
            {
                for (const Detection& d :
                     detections)
                {
                    std::cout
                        << (
                            d.classId == CAT_ID
                            ? "CAT "
                            : "DOG "
                        )
                        << d.confidence
                        << " ";
                }

                std::cout
                    << "| FPS "
                    << smoothFps
                    << std::endl;
            }

            lastLog = now;
        }

        if (hasDisplay)
        {
            cv::imshow(
                "FOR_CAT TensorRT",
                frame
            );

            int key =
                cv::waitKey(1) & 0xFF;

            if (key == 'q')
                break;
        }
        else
        {
            double saveElapsed =
                std::chrono::duration<double>(
                    now - lastSave
                ).count();

            if (saveElapsed >= 1.0)
            {
                cv::imwrite(
                    "/home/toan/for_cat/latest.jpg",
                    frame
                );

                lastSave = now;
            }
        }
    }

    cap.release();

    if (hasDisplay)
        cv::destroyAllWindows();

    cudaStreamDestroy(stream);

    cudaFree(deviceBuffers[0]);
    cudaFree(deviceBuffers[1]);

    context->destroy();
    engine->destroy();
    runtime->destroy();

    return 0;
}
