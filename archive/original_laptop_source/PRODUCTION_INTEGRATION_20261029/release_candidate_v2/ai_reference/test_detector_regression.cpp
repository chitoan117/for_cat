// Native unit cases and optional real-engine OFFLINE images. Never a physical animal PASS.
#define main detector_program_main
#include "cat_dog_trt.cpp"
#undef main

namespace {
void expect(bool condition, const char* reason) {
    if (!condition) throw std::runtime_error(reason);
}
void decoder_cases() {
    constexpr int predictions = 2100;
    std::vector<float> output(84 * predictions, 0);
    LetterboxInfo info{0.5f, 0, 40};
    const cv::Size size(640, 480);
    expect(postprocess(output.data(), size, info).empty(), "zero output must produce NONE");
    output[0] = 160; output[predictions] = 160;
    output[2 * predictions] = 100; output[3 * predictions] = 100;
    output[(4 + CAT_ID) * predictions] = 0.9f;
    auto result = postprocess(output.data(), size, info);
    expect(result.size() == 1 && result[0].classId == CAT_ID && result[0].box == cv::Rect(220,140,200,200), "CAT decoding/letterbox regression");
    output[(4 + CAT_ID) * predictions] = 0;
    output[(4 + DOG_ID) * predictions] = 0.8f;
    result = postprocess(output.data(), size, info);
    expect(result.size() == 1 && result[0].classId == DOG_ID, "DOG decoding regression");
    output[(4 + DOG_ID) * predictions] = 0;
    output[4 * predictions] = 0.99f;
    expect(postprocess(output.data(), size, info).empty(), "person-only logits must produce NONE");
    output[(4 + CAT_ID) * predictions] = 0.4f;
    expect(postprocess(output.data(), size, info).size() == 1,
           "Documented limitation changed: decoder does not select global 80-class winner");
    std::vector<float> input(3 * 320 * 320);
    cv::Mat original(480, 640, CV_8UC3, cv::Scalar(10,20,30));
    preprocess(original, input.data(), info);
    const int center = 160 * 320 + 160;
    expect(std::fabs(input[center] - 30.0f/255) < 1e-6f && std::fabs(input[320*320+center] - 20.0f/255) < 1e-6f,
           "BGR/RGB CHW preprocessing regression");
    std::cout << "Decoder/preprocess: 6 synthetic unit cases PASS (not physical evidence)\n";
}

void offline_images(char** paths) {
    std::ifstream file(ENGINE_PATH, std::ios::binary | std::ios::ate);
    expect(bool(file), "offline engine missing");
    std::vector<char> bytes(static_cast<std::size_t>(file.tellg()));
    file.seekg(0); file.read(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    std::unique_ptr<IRuntime, TrtDestroy<IRuntime>> runtime(createInferRuntime(gLogger));
    expect(bool(runtime), "offline runtime failed");
    std::unique_ptr<ICudaEngine, TrtDestroy<ICudaEngine>> engine(runtime->deserializeCudaEngine(bytes.data(), bytes.size()));
    expect(bool(engine), "offline engine failed");
    std::vector<latency::Binding> bindings;
    for (int index = 0; index < engine->getNbBindings(); ++index) {
        latency::Binding binding{engine->bindingIsInput(index), engine->getBindingDataType(index) == DataType::kFLOAT, {}};
        const auto dims = engine->getBindingDimensions(index);
        for (int dimension = 0; dimension < dims.nbDims; ++dimension) binding.dimensions.push_back(dims.d[dimension]);
        bindings.push_back(binding);
    }
    expect(latency::binding_error(bindings, engine->hasImplicitBatchDimension()).empty(), "offline engine binding mismatch");
    std::unique_ptr<IExecutionContext, TrtDestroy<IExecutionContext>> context(engine->createExecutionContext());
    expect(bool(context), "offline context failed");
    std::vector<float> input(3 * 320 * 320), output(84 * 2100);
    GpuResources gpu;
    checked(cudaMalloc(&gpu.buffers[0], input.size()*sizeof(float)), "offline input allocation");
    checked(cudaMalloc(&gpu.buffers[1], output.size()*sizeof(float)), "offline output allocation");
    checked(cudaStreamCreate(&gpu.stream), "offline stream");
    const int expected[] = {CAT_ID, DOG_ID, -1};
    for (int sample = 0; sample < 3; ++sample) {
        auto frame = cv::imread(paths[sample]);
        expect(!frame.empty(), "offline image missing");
        LetterboxInfo info;
        preprocess(frame, input.data(), info);
        checked(cudaMemcpyAsync(gpu.buffers[0], input.data(), input.size()*sizeof(float), cudaMemcpyHostToDevice, gpu.stream), "offline H2D");
        expect(context->enqueueV2(gpu.buffers, gpu.stream, nullptr), "offline inference failed");
        checked(cudaMemcpyAsync(output.data(), gpu.buffers[1], output.size()*sizeof(float), cudaMemcpyDeviceToHost, gpu.stream), "offline D2H");
        checked(cudaStreamSynchronize(gpu.stream), "offline sync");
        const auto detections = postprocess(output.data(), frame.size(), info);
        bool matched = expected[sample] == -1 ? detections.empty() : false;
        std::cout << "OFFLINE_IMAGE sample=" << sample << " expected=" << expected[sample];
        for (const auto& detection : detections) {
            std::cout << " class=" << detection.classId << " confidence=" << detection.confidence;
            matched = matched || detection.classId == expected[sample];
        }
        std::cout << " result=" << (matched ? "PASS" : "FAIL") << '\n';
        expect(matched, "offline image regression failed");
    }
    std::cout << "Physical live CAT/DOG/PERSON tests: NOT_TESTED_PHYSICALLY\n";
}
}
int main(int argc, char** argv) {
    try {
        decoder_cases();
        if (argc == 4) offline_images(argv + 1);
        else expect(argc == 1, "supply CAT_image DOG_image PERSON_image, or no arguments for units only");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
