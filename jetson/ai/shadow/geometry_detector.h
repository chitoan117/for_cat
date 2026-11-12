#ifndef FOR_CAT_GEOMETRY_DETECTOR_H
#define FOR_CAT_GEOMETRY_DETECTOR_H
#include "behavior_shadow.h"
#include <memory>
#include <opencv2/core.hpp>
namespace geometry_validation {
class Detector {
public:
    explicit Detector(const std::string& engine_path);
    ~Detector();
    std::vector<behavior_shadow::Detection> infer(const cv::Mat& original);
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
class LiveSource {
public:
    explicit LiveSource(const std::string& device);
    ~LiveSource();
    bool read(cv::Mat& original, behavior_shadow::Millis& timestamp_ms);
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
// Tests invoke the exact production preprocessing/decoder, without loading an engine.
unsigned detector_coordinate_tests();
} // namespace geometry_validation
#endif
