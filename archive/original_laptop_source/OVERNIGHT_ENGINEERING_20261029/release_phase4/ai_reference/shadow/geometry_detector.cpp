// Same source-inclusion pattern as existing test_detector_regression.cpp.
// Production source/binary are never edited. Do not call the renamed camera main.
#define main for_cat_unused_production_main
#include "../cat_dog_trt.cpp"
#undef main
#include "geometry_detector.h"
#include "geometry_validation.h"

namespace geometry_validation {
struct Detector::Impl {
    std::unique_ptr<IRuntime,TrtDestroy<IRuntime>> runtime;
    std::unique_ptr<ICudaEngine,TrtDestroy<ICudaEngine>> engine;
    std::unique_ptr<IExecutionContext,TrtDestroy<IExecutionContext>> context;
    std::vector<float> input = std::vector<float>(3*320*320), output = std::vector<float>(84*2100);
    GpuResources gpu; // destroyed/synchronized before host vectors/context/engine/runtime
    explicit Impl(const std::string& path) {
        std::ifstream file(path,std::ios::binary|std::ios::ate);
        require(bool(file) && file.tellg() > 0 && file.tellg() <= 512*1024*1024, "invalid engine file");
        std::vector<char> bytes(static_cast<std::size_t>(file.tellg())); file.seekg(0);
        require(bool(file.read(bytes.data(),static_cast<std::streamsize>(bytes.size()))), "engine read failed");
        runtime.reset(createInferRuntime(gLogger)); require(bool(runtime), "TensorRT runtime failed");
        engine.reset(runtime->deserializeCudaEngine(bytes.data(),bytes.size())); require(bool(engine), "engine deserialization failed");
        std::vector<latency::Binding> bindings;
        for (int i = 0; i < engine->getNbBindings(); ++i) {
            require(engine->getBindingFormat(i) == TensorFormat::kLINEAR && engine->getBindingVectorizedDim(i) == -1,
                    "engine needs unvectorized linear storage");
            latency::Binding b{engine->bindingIsInput(i),engine->getBindingDataType(i) == DataType::kFLOAT,{}};
            const auto dims = engine->getBindingDimensions(i);
            for (int j = 0; j < dims.nbDims; ++j) b.dimensions.push_back(dims.d[j]);
            bindings.push_back(b);
        }
        require(latency::binding_error(bindings,engine->hasImplicitBatchDimension()).empty(), "engine binding contract mismatch");
        context.reset(engine->createExecutionContext()); require(bool(context), "context creation failed");
        checked(cudaMalloc(&gpu.buffers[0],input.size()*sizeof(float)),"geometry input allocation");
        checked(cudaMalloc(&gpu.buffers[1],output.size()*sizeof(float)),"geometry output allocation");
        checked(cudaStreamCreate(&gpu.stream),"geometry stream creation");
    }
};
Detector::Detector(const std::string& path) : impl_(new Impl(path)) {}
Detector::~Detector() = default;
std::vector<behavior_shadow::Detection> Detector::infer(const cv::Mat& original) {
    require(!original.empty() && original.type() == CV_8UC3,"expected original BGR image");
    LetterboxInfo info; auto& p = *impl_;
    preprocess(original,p.input.data(),info); // exact production BGR->RGB / CHW /255
    checked(cudaMemcpyAsync(p.gpu.buffers[0],p.input.data(),p.input.size()*sizeof(float),cudaMemcpyHostToDevice,p.gpu.stream),"geometry H2D");
    require(p.context->enqueueV2(p.gpu.buffers,p.gpu.stream,nullptr),"geometry enqueue failed");
    checked(cudaMemcpyAsync(p.output.data(),p.gpu.buffers[1],p.output.size()*sizeof(float),cudaMemcpyDeviceToHost,p.gpu.stream),"geometry D2H");
    checked(cudaStreamSynchronize(p.gpu.stream),"geometry sync");
    const auto decoded = postprocess(p.output.data(),original.size(),info); // exact class thresholds + per-class NMS
    std::vector<behavior_shadow::Detection> result;
    for (const auto& d : decoded) {
        const Pixels box{d.box.x,d.box.y,d.box.x+d.box.width,d.box.y+d.box.height};
        result.push_back({d.classId == CAT_ID ? behavior_shadow::Object::Cat : behavior_shadow::Object::Dog,
                          d.confidence,normalized(box,{original.cols,original.rows})});
    }
    return result;
}
struct LiveSource::Impl {
    latency::Capture capture{true};
    behavior_shadow::Maybe<latency::Clock::time_point> first;
    behavior_shadow::Millis previous = -1;
    explicit Impl(const std::string& device) {
        latency::Options options; options.device = device; options.gui = false; options.snapshot = false;
        capture.open(options); // reuses validated sole-reader/latest-slot capture
    }
};
LiveSource::LiveSource(const std::string& device) : impl_(new Impl(device)) {}
LiveSource::~LiveSource() = default;
bool LiveSource::read(cv::Mat& original, behavior_shadow::Millis& stamp) {
    latency::Packet<cv::Mat> packet;
    if (!impl_->capture.take(packet)) {
        require(!impl_->capture.failed(),"camera read failure budget exhausted"); return false;
    }
    if (!impl_->first.present) impl_->first = behavior_shadow::Maybe<latency::Clock::time_point>(packet.received);
    stamp = std::chrono::duration_cast<std::chrono::milliseconds>(packet.received-impl_->first.value).count();
    if (stamp <= impl_->previous) return false; // never fabricate a timestamp
    impl_->previous = stamp; original = std::move(packet.image); return true;
}

unsigned detector_coordinate_tests() {
    unsigned checks = 0;
    const auto expect = [&](bool ok) { ++checks; require(ok,"production coordinate/preprocess regression"); };
    expect(CAT_ID == 15 && DOG_ID == 16 && CONF_THRESHOLD == 0.35f && NMS_THRESHOLD == 0.45f);
    for (const cv::Size size : {cv::Size(640,480),cv::Size(1280,720),cv::Size(480,640),cv::Size(641,479)}) {
        cv::Mat frame(size,CV_8UC3,cv::Scalar(10,20,30)); LetterboxInfo info;
        std::vector<float> input(3*320*320); preprocess(frame,input.data(),info);
        const int pixel = 160*320+160;
        expect(std::abs(input[pixel]-30.f/255) < 1e-6f && std::abs(input[320*320+pixel]-20.f/255) < 1e-6f &&
               std::abs(input[2*320*320+pixel]-10.f/255) < 1e-6f);
        const float x = static_cast<float>(size.width)*0.25f, y = static_cast<float>(size.height)*0.25f;
        const float w = static_cast<float>(size.width)*0.3f, h = static_cast<float>(size.height)*0.3f;
        std::vector<float> output(84*2100,0);
        output[0] = (x+w/2)*info.scale+static_cast<float>(info.padX);
        output[2100] = (y+h/2)*info.scale+static_cast<float>(info.padY);
        output[2*2100] = w*info.scale; output[3*2100] = h*info.scale; output[(4+15)*2100] = 0.9f;
        const auto decoded = postprocess(output.data(),size,info);
        expect(decoded.size() == 1 && decoded[0].classId == CAT_ID);
        expect(std::abs(decoded[0].box.x-static_cast<int>(x)) <= 1 && std::abs(decoded[0].box.y-static_cast<int>(y)) <= 1 &&
               std::abs(decoded[0].box.width-static_cast<int>(w)) <= 1 && std::abs(decoded[0].box.height-static_cast<int>(h)) <= 1);
        // Duplicated candidate is suppressed by the original per-class NMS.
        for (int channel : {0,1,2,3,4+15}) output[channel*2100+1] = output[channel*2100];
        expect(postprocess(output.data(),size,info).size() == 1);
        output[(4+15)*2100] = 0; output[(4+15)*2100+1] = 0; output[(4+16)*2100] = 0.9f;
        expect(postprocess(output.data(),size,info)[0].classId == DOG_ID);
    }
    return checks;
}
} // namespace geometry_validation
