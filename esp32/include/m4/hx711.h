#pragma once
#include "io.h"
#include "calibration.h"

namespace m4 {
struct Hx711Config { Pin dout{}, sck{}; uint32_t ready_timeout_ms = 500; };
class Hx711 {
 public:
  explicit Hx711(PinIO& io) : io_(io) {}
  bool begin(Hx711Config config, uint32_t now) {
    active_ = averaging_ = false; raw = {}; averaged = {}; grams = {};
    config_ = config;
    if (!inputValid(io_, config.dout) || !outputValid(io_, config.sck) ||
        config.dout.number == config.sck.number || !config.ready_timeout_ms || config.ready_timeout_ms > 5000) {
      status = {}; return false;
    }
    io_.input(config.dout.number, Pull::NONE);
    io_.output(config.sck.number); io_.write(config.sck.number, false);
    active_ = true; waiting_at_ = now; status = {Health::INITIALIZING, Reason::NONE}; return true;
  }
  void poll(uint32_t now) {
    raw.fresh = averaged.fresh = grams.fresh = false;
    if (!active_) return;
    if (io_.read(config_.dout.number)) {
      if (static_cast<uint32_t>(now - waiting_at_) >= config_.ready_timeout_ms) {
        raw.valid = averaged.valid = grams.valid = false;
        averaging_ = false; // do not combine pre-/post-fault samples into calibration
        status = {Health::NOT_CONNECTED, Reason::TIMEOUT};
      }
      return; // no busy waiting or pulseIn
    }
    uint32_t bits = 0;
    io_.enterCritical();
    for (uint8_t bit = 0; bit < 24; ++bit) {
      io_.write(config_.sck.number, true); io_.pauseMicros(2);
      bits = (bits << 1) | (io_.read(config_.dout.number) ? 1u : 0u);
      io_.write(config_.sck.number, false); io_.pauseMicros(2);
    }
    // 25th pulse selects channel A / gain 128; high pulses remain short.
    io_.write(config_.sck.number, true); io_.pauseMicros(2);
    io_.write(config_.sck.number, false); io_.pauseMicros(2);
    io_.exitCritical();
    const int32_t signed_raw = bits & 0x800000 ? static_cast<int32_t>(bits) - 16777216 : static_cast<int32_t>(bits);
    raw = {true, signed_raw, now, true}; waiting_at_ = now;
    if (signed_raw == -8388608 || signed_raw == 8388607) {
      raw.valid = false;
      grams = {}; averaged = {}; averaging_ = false;
      status = {Health::FAULT, Reason::INVALID_DATA}; return; // ADC rail/saturation
    }
    if (averaging_ && average_.add(signed_raw) && average_.ready()) {
      averaged = {true, average_.mean(), now, true}; averaging_ = false;
    }
    grams = calibration.grams(signed_raw, now);
    status = !calibration.valid() ? Status{Health::NOT_CALIBRATED, Reason::NOT_CALIBRATED} :
             grams.valid ? Status{Health::HEALTHY, Reason::NONE} : Status{Health::DEGRADED, Reason::INVALID_DATA};
  }
  bool startAverage(uint8_t count) {
    if (!active_ || !average_.begin(count)) return false;
    averaged = {}; averaging_ = true; return true;
  }
  Reading<int32_t> readRaw() const { return raw; }
  Reading<double> readAveragedRaw() const { return averaged; }
  bool tare() {
    if (!averaged.valid || !calibration.tare(averaged.value)) return false;
    grams = {}; // the previous calibrated result cannot survive invalidation of its factor
    status = {Health::NOT_CALIBRATED, Reason::NOT_CALIBRATED};
    return true;
  }
  bool calibrate(double known_grams) {
    if (!averaged.valid || !calibration.reference(averaged.value, known_grams)) return false;
    grams = {}; status = {Health::INITIALIZING, Reason::NONE}; // new factor needs a new sample
    return true;
  }
  void applyCalibration(const ScaleCalibration& next) {
    calibration = next; grams = {}; averaged = {}; averaging_ = false;
    if (active_ && raw.valid)
      status = calibration.valid() ? Status{Health::INITIALIZING, Reason::NONE} :
                                    Status{Health::NOT_CALIBRATED, Reason::NOT_CALIBRATED};
  }
  Status status{};
  ScaleCalibration calibration{};
  Reading<int32_t> raw{};
  Reading<double> averaged{};
  Reading<float> grams{};
 private:
  PinIO& io_;
  Hx711Config config_{};
  RawAverage average_{};
  bool active_ = false, averaging_ = false;
  uint32_t waiting_at_ = 0;
};
}  // namespace m4
