// FOR_CAT ESP32-S3
// HX711 golden calibration + SSD1306 OLED + 4 range sensors + PIR + water level.
// V14 isolated MANUAL BENCH: 1=CAT, 2=DOG, 0=EXIT. FC1/Jetson motor commands DISABLED.
// Servo MG996R 360 continuous: 1350us OPEN RIGHT, 1600us CLOSE LEFT (travel trial).
// 1500us NEUTRAL. Timed reversal is NOT verified mechanical closed position.
// Explicit one-time arming / polarity setup required; then 1 and 2 repeat until 0.
// NO water pump automatic control; NEVER move servo on boot.
//
// Board: ESP32S3 Dev Module.
// ESP32 Arduino core: 3.3.11.
// USB CDC On Boot: Disabled.
// Serial0 / external USB-UART bridge: 115200.
//
// HX711 DOUT=4, SCK=5.
// Continuous servo GPIO6.
// HC1 12/13; HC2 16/17; D1 BOWL 14/15; D2 TANK 18/19.
// OLED SSD1306 0x3C SDA8 SCL9; PIR 11; manual feed button 21.
// Before sensors_on: verify ALL ECHO/OUT voltages <=3.3 V.
//
// Serial Monitor commands:
//   hx, status, weight, tare, cal 38, cal 20, t, cal_cancel,
//   sensors_on, sensors_off, sensors, water_full, water_empty,
//   water_reset, oled, help, STOP, stop
//   SETUP: verify 3.3V ECHO and choose buzzer_high OR buzzer_low once. Then 1/2/0.
//   open_ms 900 / close_ms 1450; 3=open, 4=close; no fine-adjust commands.
//   GPIO47 disabled; 1/2 retain CAT/DOG commands; standalone 0 stops immediately.
//
// Other FC1 protocol commands still use the Jetson sender.
//
// HX711 uses signed 24-bit A128, median-3, 15 samples for tare/reference,
// fast response filter (1g threshold, alpha 0.40), zero deadband 0.20g.
// Legacy FC1 autonomous servo settings remain disabled; V8 is BENCH ONLY.

#include <Arduino.h>
#include "FallbackGate.h"
#include "CatNearGate.h"
#include <Preferences.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <driver/gpio.h>
#include <esp_system.h>
#include <esp_arduino_version.h>
#include <cmath>
#include <cstring>
#include <cstdint>
#include <cstddef>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>

#if ESP_ARDUINO_VERSION_MAJOR < 3
#error "Select ESP32 Arduino core 3.x. Tested with 3.3.11."
#endif

#if !defined(CONFIG_IDF_TARGET_ESP32S3)
#error "Select ESP32S3 Dev Module."
#endif

#if ARDUINO_USB_CDC_ON_BOOT
#error "Disable USB CDC On Boot. This sketch uses Serial0."
#endif

#define M4_SENSOR_BRINGUP 1
#define M4_QUAD_ULTRASONIC 1
#define FORCAT_MANUAL_STATION 1

void setup();
void loop();

// ============================================================
// HARDWARE CONSTANTS
// ============================================================

namespace current_hardware {
constexpr int SERVO_SIGNAL = 6;
constexpr int PUMP_CONTROL = 7;
// PCB D2 ECHO J3_20=GPIO19. USB-UART only; native USB D- shares GPIO19.
constexpr int D2_WATER_ECHO = 19;
}

namespace uart_v1 {

inline uint16_t crc16(const uint8_t* p, size_t n) {
  uint16_t c = 0xffff;

  for (size_t i = 0; i < n; ++i) {
    c ^= uint16_t(p[i]) << 8;

    for (unsigned j = 0; j < 8; ++j) {
      c = c & 0x8000
        ? uint16_t((c << 1) ^ 0x1021)
        : uint16_t(c << 1);
    }
  }

  return c;
}

}

// ============================================================
// SENSOR TYPES
// ============================================================

namespace m4 {

constexpr int PIN_NOT_ASSIGNED = -1;

enum class Health : uint8_t {
  NOT_CONFIGURED,
  NOT_CONNECTED,
  NOT_CALIBRATED,
  INITIALIZING,
  HEALTHY,
  DEGRADED,
  FAULT
};

enum class Reason : uint8_t {
  NONE,
  CONFIGURATION_INVALID,
  TIMEOUT,
  BUS_ERROR,
  INVALID_DATA,
  NOT_CALIBRATED,
  GEOMETRY_INVALID,
  RANGE_INVALID,
  ACTUATORS_DISABLED,
  CLOCK_HALTED,
  RTC_INVALID_TIME,
  RTC_IO_ERROR,
  WRITE_PROTECTED,
  READBACK_MISMATCH,
  NO_RESPONSE
};

inline const char* name(Health h) {
  switch (h) {
    case Health::NOT_CONFIGURED: return "NOT_CONFIGURED";
    case Health::NOT_CONNECTED: return "NOT_CONNECTED";
    case Health::NOT_CALIBRATED: return "NOT_CALIBRATED";
    case Health::INITIALIZING: return "INITIALIZING";
    case Health::HEALTHY: return "HEALTHY";
    case Health::DEGRADED: return "DEGRADED";
    default: return "FAULT";
  }
}

inline const char* name(Reason r) {
  switch (r) {
    case Reason::NONE: return "NONE";
    case Reason::CONFIGURATION_INVALID:
      return "CONFIGURATION_INVALID";
    case Reason::TIMEOUT: return "TIMEOUT";
    case Reason::BUS_ERROR: return "BUS_ERROR";
    case Reason::INVALID_DATA: return "INVALID_DATA";
    case Reason::NOT_CALIBRATED: return "NOT_CALIBRATED";
    case Reason::GEOMETRY_INVALID: return "GEOMETRY_INVALID";
    case Reason::RANGE_INVALID: return "RANGE_INVALID";
    case Reason::CLOCK_HALTED: return "CLOCK_HALTED";
    case Reason::RTC_INVALID_TIME: return "INVALID_TIME";
    case Reason::RTC_IO_ERROR: return "IO_ERROR";
    case Reason::WRITE_PROTECTED: return "WRITE_PROTECTED";
    case Reason::READBACK_MISMATCH: return "READBACK_MISMATCH";
    case Reason::NO_RESPONSE: return "NO_RESPONSE";
    default: return "ACTUATORS_DISABLED";
  }
}

template<class T>
struct Reading {
  bool valid = false;
  T value{};
  uint32_t sampled_at_ms = 0;
  bool fresh = false;
};

struct Status {
  Health health = Health::NOT_CONFIGURED;
  Reason reason = Reason::CONFIGURATION_INVALID;
};

struct Pin {
  int number = PIN_NOT_ASSIGNED;
  bool reviewed = false;
};

enum class Pull : uint8_t {
  NONE,
  UP,
  DOWN
};

class PinIO {
 public:
  virtual ~PinIO() = default;
  virtual bool inputAllowed(int pin) const = 0;
  virtual bool outputAllowed(int pin) const = 0;
  virtual void input(int pin, Pull pull) = 0;
  virtual void output(int pin) = 0;
  virtual bool read(int pin) = 0;
  virtual void write(int pin, bool high) = 0;
  virtual void pauseMicros(uint32_t short_us) = 0;
  virtual void enterCritical() = 0;
  virtual void exitCritical() = 0;
};

inline bool inputValid(PinIO& io, Pin pin) {
  return pin.reviewed && io.inputAllowed(pin.number);
}

inline bool outputValid(PinIO& io, Pin pin) {
  return pin.reviewed && io.outputAllowed(pin.number);
}

// ============================================================
// HX711 CALIBRATION TYPES
// ============================================================

inline bool rawValid(double raw) {
  return std::isfinite(raw)
    && raw >= -8388608
    && raw <= 8388607;
}

class RawAverage {
 public:
  bool begin(uint8_t count) {
    if (!count || count > 64) return false;
    needed_ = count;
    count_ = 0;
    sum_ = 0;
    return true;
  }

  bool add(int32_t raw) {
    if (!rawValid(raw) || !needed_ || count_ >= needed_) {
      return false;
    }

    sum_ += raw;
    ++count_;
    return true;
  }

  bool ready() const {
    return needed_ && count_ == needed_;
  }

  double mean() const {
    return ready() ? static_cast<double>(sum_) / count_ : 0;
  }

 private:
  uint8_t needed_ = 0;
  uint8_t count_ = 0;
  int64_t sum_ = 0;
};

struct ScaleCalibration {
  bool tared = false;
  bool calibrated = false;
  double tare_counts = 0;
  double grams_per_count = 0;

  bool tare(double empty_average) {
    if (!rawValid(empty_average)) return false;

    tared = true;
    calibrated = false;
    tare_counts = empty_average;
    grams_per_count = 0;
    return true;
  }

  bool reference(double loaded_average, double known_grams) {
    if (!tared
        || !rawValid(loaded_average)
        || !std::isfinite(known_grams)
        || known_grams <= 0
        || loaded_average == tare_counts) {
      return false;
    }

    const double factor =
      known_grams / (loaded_average - tare_counts);

    if (!std::isfinite(factor) || factor == 0) return false;

    grams_per_count = factor;
    calibrated = true;
    return true;
  }

  bool valid() const {
    return calibrated
      && tared
      && rawValid(tare_counts)
      && std::isfinite(grams_per_count)
      && grams_per_count != 0;
  }

  Reading<float> grams(double raw, uint32_t now) const {
    Reading<float> result;

    if (!valid() || !rawValid(raw)) return result;

    const double value =
      (raw - tare_counts) * grams_per_count;

    // Allow small negative zero-drift (down to -5.0 g) on empty tray
    // without falsely marking hx_health as DEGRADED / INVALID_DATA.
    if (!std::isfinite(value) || value < -5.0 || value > 100000) {
      return result;
    }

    const float clamped = value < 0.0 ? 0.0f : static_cast<float>(value);
    return {true, clamped, now, true};
  }
};

struct LevelCalibration {
  bool calibrated = false;
  float full_cm = 0;
  float empty_cm = 0;

  bool valid() const {
    return calibrated
      && std::isfinite(full_cm)
      && std::isfinite(empty_cm)
      && full_cm > 0
      && empty_cm > full_cm;
  }
};

// ============================================================
// HX711 REFERENCE MEDIAN / DISPLAY
// ============================================================

class Hx711Median3 {
 public:
  void reset() {
    count_ = 0;
  }

  bool add(int32_t raw, int32_t& result) {
    values_[count_++] = raw;

    if (count_ != 3) return false;

    count_ = 0;

    int32_t a = values_[0];
    int32_t b = values_[1];
    int32_t c = values_[2];
    int32_t t;

    if (a > b) {
      t = a; a = b; b = t;
    }

    if (b > c) {
      t = b; b = c; c = t;
    }

    if (a > b) {
      t = a; a = b; b = t;
    }

    result = b;
    return true;
  }

 private:
  int32_t values_[3]{};
  uint8_t count_ = 0;
};

inline Reading<float> hx711SignedGrams(
    const ScaleCalibration& calibration,
    double raw,
    uint32_t now) {

  if (!calibration.valid() || !rawValid(raw)) return {};

  const double scale_factor =
    1.0 / calibration.grams_per_count;

  const double grams =
    (raw - calibration.tare_counts) / scale_factor;

  if (!std::isfinite(scale_factor)
      || scale_factor == 0
      || !std::isfinite(grams)
      || std::fabs(grams) > 100000) {
    return {};
  }

  return {true, static_cast<float>(grams), now, true};
}

class Hx711ReferenceDisplay {
 public:
  static constexpr float ZERO_DEADBAND = 0.20f;
  static constexpr float FAST_CHANGE_THRESHOLD = 1.0f;
  static constexpr float STABLE_ALPHA = 0.40f;

  void reset() {
    displayed_ = 0;
  }

  Reading<float> update(const Reading<float>& measurement) {
    if (!measurement.valid
        || !std::isfinite(measurement.value)) {
      reset();
      return {};
    }

    if (!measurement.fresh) return {};

    float current = measurement.value;

    if (current > -ZERO_DEADBAND && current < ZERO_DEADBAND) {
      current = 0;
    }

    if (current < 0 && current > -0.5f) current = 0;

    if (std::fabs(current - displayed_)
        >= FAST_CHANGE_THRESHOLD) {
      displayed_ = current;
    } else {
      displayed_ =
        STABLE_ALPHA * current
        + (1.0f - STABLE_ALPHA) * displayed_;
    }

    if (displayed_ > -ZERO_DEADBAND
        && displayed_ < ZERO_DEADBAND) {
      displayed_ = 0;
    }

    return {
      true,
      displayed_,
      measurement.sampled_at_ms,
      true
    };
  }

 private:
  float displayed_ = 0;
};

// ============================================================
// HX711 DRIVER: SIGNED 24-BIT / A128 / MEDIAN OF 3
// ============================================================

struct Hx711Config {
  Pin dout{};
  Pin sck{};
  uint32_t ready_timeout_ms = 500;
};

class Hx711 {
 public:
  explicit Hx711(PinIO& io) : io_(io) {}

  bool begin(Hx711Config config, uint32_t now) {
    active_ = averaging_ = false;
    raw = {};
    averaged = {};
    resetMeasurement();
    config_ = config;

    if (!inputValid(io_, config.dout)
        || !outputValid(io_, config.sck)
        || config.dout.number == config.sck.number
        || !config.ready_timeout_ms
        || config.ready_timeout_ms > 5000) {
      status = {};
      return false;
    }

    io_.input(config.dout.number, Pull::NONE);
    io_.output(config.sck.number);
    io_.write(config.sck.number, false);

    active_ = true;
    waiting_at_ = now;
    status = {Health::INITIALIZING, Reason::NONE};
    return true;
  }

  void poll(uint32_t now) {
    raw.fresh = averaged.fresh = grams.fresh = false;
    median_raw.fresh =
      signed_grams.fresh =
      display_grams.fresh = false;

    if (!active_) return;

    if (io_.read(config_.dout.number)) {
      if (static_cast<uint32_t>(now - waiting_at_)
          >= config_.ready_timeout_ms) {
        raw.valid = averaged.valid = false;
        resetMeasurement();
        averaging_ = false;
        status = {Health::NOT_CONNECTED, Reason::TIMEOUT};
      }

      return;
    }

    uint32_t bits = 0;

    io_.enterCritical();

    for (uint8_t bit = 0; bit < 24; ++bit) {
      io_.write(config_.sck.number, true);
      io_.pauseMicros(2);

      bits =
        (bits << 1)
        | (io_.read(config_.dout.number) ? 1u : 0u);

      io_.write(config_.sck.number, false);
      io_.pauseMicros(2);
    }

    // Pulse 25 selects channel A, gain 128.
    io_.write(config_.sck.number, true);
    io_.pauseMicros(2);
    io_.write(config_.sck.number, false);
    io_.pauseMicros(2);

    io_.exitCritical();

    const int32_t signed_raw =
      bits & 0x800000
        ? static_cast<int32_t>(bits) - 16777216
        : static_cast<int32_t>(bits);

    raw = {true, signed_raw, now, true};
    waiting_at_ = now;

    if (signed_raw == 0
        || signed_raw == -1
        || signed_raw == -8388608
        || signed_raw == 8388607) {
      raw.valid = false;
      resetMeasurement();
      averaged = {};
      averaging_ = false;
      status = {Health::FAULT, Reason::INVALID_DATA};
      return;
    }

    if (averaging_
        && average_.add(signed_raw)
        && average_.ready()) {
      averaged = {true, average_.mean(), now, true};
      averaging_ = false;
    }

    int32_t median = 0;

    if (!median_.add(signed_raw, median)) {
      if (!median_raw.valid) {
        status = calibration.valid()
          ? Status{Health::INITIALIZING, Reason::NONE}
          : Status{
              Health::NOT_CALIBRATED,
              Reason::NOT_CALIBRATED
            };
      }

      return;
    }

    median_raw = {true, median, now, true};

    signed_grams =
      hx711SignedGrams(calibration, median, now);

    display_grams = display_.update(signed_grams);

    // Control reading is NOT the smoothed display reading.
    grams = calibration.grams(median, now);

    status = !calibration.valid()
      ? Status{
          Health::NOT_CALIBRATED,
          Reason::NOT_CALIBRATED
        }
      : grams.valid
        ? Status{Health::HEALTHY, Reason::NONE}
        : Status{Health::DEGRADED, Reason::INVALID_DATA};
  }

  bool startAverage(uint8_t count) {
    if (!active_ || !average_.begin(count)) return false;

    averaged = {};
    averaging_ = true;
    return true;
  }

  Reading<int32_t> readRaw() const {
    return raw;
  }

  Reading<double> readAveragedRaw() const {
    return averaged;
  }

  bool tare() {
    if (!averaged.valid
        || !calibration.tare(averaged.value)) {
      return false;
    }

    resetMeasurement();
    status = {
      Health::NOT_CALIBRATED,
      Reason::NOT_CALIBRATED
    };
    return true;
  }

  bool calibrate(double known_grams) {
    if (!averaged.valid
        || !calibration.reference(
            averaged.value,
            known_grams)) {
      return false;
    }

    resetMeasurement();
    status = {Health::INITIALIZING, Reason::NONE};
    return true;
  }

  void applyCalibration(const ScaleCalibration& next) {
    calibration = next;
    resetMeasurement();
    averaged = {};
    averaging_ = false;

    if (active_ && raw.valid) {
      status = calibration.valid()
        ? Status{Health::INITIALIZING, Reason::NONE}
        : Status{
            Health::NOT_CALIBRATED,
            Reason::NOT_CALIBRATED
          };
    }
  }

  bool tarePreservingFactor() {
    if (!averaged.valid || !calibration.valid()) {
      return false;
    }

    ScaleCalibration next = calibration;
    next.tare_counts = averaged.value;

    if (!next.valid()) return false;

    applyCalibration(next);
    return true;
  }

  Status status{};
  ScaleCalibration calibration{};
  Reading<int32_t> raw{};
  Reading<double> averaged{};
  Reading<float> grams{};
  Reading<int32_t> median_raw{};
  Reading<float> signed_grams{};
  Reading<float> display_grams{};

 private:
  void resetMeasurement() {
    grams = {};
    median_raw = {};
    signed_grams = {};
    display_grams = {};
    median_.reset();
    display_.reset();
  }

  PinIO& io_;
  Hx711Config config_{};
  RawAverage average_{};
  Hx711Median3 median_{};
  Hx711ReferenceDisplay display_{};
  bool active_ = false;
  bool averaging_ = false;
  uint32_t waiting_at_ = 0;
};

// ============================================================
// EXISTING NVS CALIBRATION RECORD
// ============================================================

struct CalibrationRecord {
  ScaleCalibration hx711{};
  LevelCalibration food{};
  LevelCalibration water{};
};

namespace calibration_record {

constexpr size_t SIZE = 39;

inline bool valid(const CalibrationRecord& record) {
  if (record.hx711.tared
      && !rawValid(record.hx711.tare_counts)) {
    return false;
  }

  if (!record.hx711.tared
      && (record.hx711.tare_counts != 0
          || record.hx711.calibrated)) {
    return false;
  }

  if (record.hx711.calibrated
      && !record.hx711.valid()) {
    return false;
  }

  if (!record.hx711.calibrated
      && record.hx711.grams_per_count != 0) {
    return false;
  }

  const LevelCalibration* geometries[] = {
    &record.food, &record.water
  };

  for (const auto* geometry : geometries) {
    if (geometry->calibrated && !geometry->valid()) {
      return false;
    }

    if (!geometry->calibrated
        && (geometry->full_cm != 0
            || geometry->empty_cm != 0)) {
      return false;
    }
  }

  return true;
}

inline void put(
    uint8_t* output,
    uint64_t bits,
    size_t count) {

  for (size_t i = 0; i < count; ++i) {
    output[i] = static_cast<uint8_t>(bits >> (8 * i));
  }
}

inline uint64_t get(const uint8_t* input, size_t count) {
  uint64_t result = 0;

  for (size_t i = 0; i < count; ++i) {
    result |=
      static_cast<uint64_t>(input[i]) << (8 * i);
  }

  return result;
}

inline bool decode(
    const uint8_t (&bytes)[SIZE],
    CalibrationRecord& record) {

  if (bytes[0] != 'M'
      || bytes[1] != '4'
      || bytes[2] != 'C'
      || bytes[3] != 1
      || (bytes[4] & 0xf0)
      || get(bytes + SIZE - 2, 2)
        != uart_v1::crc16(bytes, SIZE - 2)) {
    return false;
  }

  CalibrationRecord next;

  next.hx711.tared = bytes[4] & 1;
  next.hx711.calibrated = bytes[4] & 2;
  next.food.calibrated = bytes[4] & 4;
  next.water.calibrated = bytes[4] & 8;

  uint64_t bits = get(bytes + 5, 8);
  std::memcpy(&next.hx711.tare_counts, &bits, 8);

  bits = get(bytes + 13, 8);
  std::memcpy(&next.hx711.grams_per_count, &bits, 8);

  float* values[] = {
    &next.food.full_cm,
    &next.food.empty_cm,
    &next.water.full_cm,
    &next.water.empty_cm
  };

  for (size_t i = 0; i < 4; ++i) {
    uint32_t word =
      static_cast<uint32_t>(
        get(bytes + 21 + i * 4, 4));

    std::memcpy(values[i], &word, 4);
  }

  if (!valid(next)) return false;

  record = next;
  return true;
}

// Store exactly the same versioned 39-byte calibration record used by decode().
inline bool encode(const CalibrationRecord& record, uint8_t (&bytes)[SIZE]) {
  if (!valid(record)) return false;
  std::memset(bytes, 0, SIZE);
  bytes[0] = 'M'; bytes[1] = '4'; bytes[2] = 'C'; bytes[3] = 1;
  bytes[4] = (record.hx711.tared ? 1u : 0u)
           | (record.hx711.calibrated ? 2u : 0u)
           | (record.food.calibrated ? 4u : 0u)
           | (record.water.calibrated ? 8u : 0u);
  uint64_t d = 0;
  std::memcpy(&d, &record.hx711.tare_counts, sizeof(d));
  put(bytes + 5, d, 8);
  std::memcpy(&d, &record.hx711.grams_per_count, sizeof(d));
  put(bytes + 13, d, 8);
  const float values[] = {record.food.full_cm, record.food.empty_cm,
                          record.water.full_cm, record.water.empty_cm};
  for (size_t i = 0; i < 4; ++i) {
    uint32_t word = 0;
    std::memcpy(&word, &values[i], sizeof(word));
    put(bytes + 21 + i * 4, word, 4);
  }
  put(bytes + SIZE - 2, uart_v1::crc16(bytes, SIZE - 2), 2);
  return true;
}

}

// ============================================================
// GPIO ADAPTER
// ============================================================

class ArduinoPins final : public PinIO {
 public:
  bool inputAllowed(int pin) const override {
    if (pin < 0 || pin > 48 || !GPIO_IS_VALID_GPIO(pin)) {
      return false;
    }

    if (pin == current_hardware::SERVO_SIGNAL
        || pin == current_hardware::PUMP_CONTROL) {
      return false;
    }

    if ((pin >= 26 && pin <= 38)
        || pin == 0
        || pin == 3
        || pin == 20
        || (pin >= 39 && pin <= 46)) {
      return false;
    }

    return true;
  }

  bool outputAllowed(int pin) const override {
    return inputAllowed(pin)
      && pin != 10
      && pin != current_hardware::D2_WATER_ECHO // GPIO19 is D2 input on this USB-UART PCB.
      && GPIO_IS_VALID_OUTPUT_GPIO(pin);
  }

  void input(int pin, Pull pull) override {
    pinMode(
      pin,
      pull == Pull::UP
        ? INPUT_PULLUP
        : pull == Pull::DOWN
          ? INPUT_PULLDOWN
          : INPUT
    );
  }

  void output(int pin) override {
    pinMode(pin, OUTPUT);
  }

  bool read(int pin) override {
    return digitalRead(pin) == HIGH;
  }

  void write(int pin, bool high) override {
    digitalWrite(pin, high ? HIGH : LOW);
  }

  void pauseMicros(uint32_t short_us) override {
    if (short_us <= 10) delayMicroseconds(short_us);
  }

  void enterCritical() override {
    portENTER_CRITICAL(&mux_);
  }

  void exitCritical() override {
    portEXIT_CRITICAL(&mux_);
  }

 private:
  portMUX_TYPE mux_ = portMUX_INITIALIZER_UNLOCKED;
};

enum class CalibrationLoad : uint8_t {
  MISSING,
  INVALID,
  LOADED
};

class NvsCalibration {
 public:
  CalibrationLoad load(CalibrationRecord& record) {
    record = {};

    Preferences prefs;

    if (!prefs.begin("m4-calibration", true)) {
      return CalibrationLoad::MISSING;
    }

    if (!prefs.isKey("sensors-v2")) {
      prefs.end();
      return CalibrationLoad::MISSING;
    }

    uint8_t bytes[calibration_record::SIZE];

    const bool read =
      prefs.getBytesLength("sensors-v2") == sizeof(bytes)
      && prefs.getBytes(
          "sensors-v2", bytes, sizeof(bytes)) == sizeof(bytes);

    prefs.end();

    return read
      && calibration_record::decode(bytes, record)
        ? CalibrationLoad::LOADED
        : CalibrationLoad::INVALID;
  }

  bool save(const CalibrationRecord& record) {
    uint8_t bytes[calibration_record::SIZE]{};
    if (!calibration_record::encode(record, bytes)) return false;
    Preferences prefs;
    if (!prefs.begin("m4-calibration", false)) return false;
    const bool ok = prefs.putBytes("sensors-v2", bytes, sizeof(bytes))
                     == sizeof(bytes);
    prefs.end();
    return ok;
  }
};

// ============================================================
// RAW SERVO OUTPUT
// ============================================================

namespace servo_bench {

constexpr int pin = 6;
constexpr uint16_t electrical_min_us = 1000;
constexpr uint16_t electrical_max_us = 2000;

class Output {
 public:
  virtual ~Output() = default;
  virtual bool start(uint16_t pulse_us) = 0;
  virtual bool write(uint16_t pulse_us) = 0;
  virtual bool off() = 0;
};

}

class LedcServoOutput final : public servo_bench::Output {
 public:
  bool off() override {
    bool stopped = true;

    if (attached_) {
      const bool zero = ledcWrite(servo_bench::pin, 0);
      const bool detached = ledcDetach(servo_bench::pin);

      attached_ = !detached;
      stopped = zero && detached;
    }

    digitalWrite(servo_bench::pin, LOW);
    pinMode(servo_bench::pin, OUTPUT);
    digitalWrite(servo_bench::pin, LOW);

    return stopped;
  }

  bool start(uint16_t pulse_us) override {
    if (attached_ || !valid(pulse_us)) return false;

    if (!ledcAttach(servo_bench::pin, 50, 14)) {
      off();
      return false;
    }

    attached_ = true;

    if (!write(pulse_us)) {
      off();
      return false;
    }

    return true;
  }

  bool write(uint16_t pulse_us) override {
    if (!attached_ || !valid(pulse_us)) return false;

    const uint32_t duty =
      (static_cast<uint32_t>(pulse_us) * 16384u + 10000u)
      / 20000u;

    const bool ok = ledcWrite(servo_bench::pin, duty);
    if (ok) pulse_us_ = pulse_us;
    return ok;
  }

  bool attached() const {
    return attached_;
  }

  bool moving() const {
    return attached_ && pulse_us_ != 1500;
  }

 private:
  static bool valid(uint16_t us) {
    return us >= servo_bench::electrical_min_us
      && us <= servo_bench::electrical_max_us;
  }

  bool attached_ = false;
  uint16_t pulse_us_ = 0;
};

}

// ============================================================
// NONBLOCKING UART0
// ============================================================

class DogNonblockingSerial {
  uint8_t bytes_[8192]{};
  size_t head_ = 0;
  size_t count_ = 0;
  bool overflow_ = false;

 public:
  void begin(unsigned long baud) {
    Serial0.begin(baud);
  }

  int available() {
    return Serial0.available();
  }

  int read() {
    return Serial0.read();
  }

  size_t write(const uint8_t* bytes, size_t n) {
    if (n > sizeof(bytes_) - count_) {
      overflow_ = true;
      return 0;
    }

    for (size_t i = 0; i < n; ++i) {
      bytes_[(head_ + count_++) % sizeof(bytes_)] = bytes[i];
    }

    return n;
  }

  void print(const char* text) {
    write(
      reinterpret_cast<const uint8_t*>(text),
      std::strlen(text)
    );
  }

  void printf(const char* format, ...) {
    char text[2048];
    va_list args;
    va_start(args, format);

    const int n =
      std::vsnprintf(text, sizeof(text), format, args);

    va_end(args);

    if (n < 0 || static_cast<size_t>(n) >= sizeof(text)) {
      overflow_ = true;
      return;
    }

    write(
      reinterpret_cast<const uint8_t*>(text),
      static_cast<size_t>(n)
    );
  }

  void drain() {
    const int room = Serial0.availableForWrite();
    size_t n =
      room > 0 ? static_cast<size_t>(room) : 0;

    if (n > 64) n = 64;
    if (n > count_) n = count_;

    if (n > sizeof(bytes_) - head_) {
      n = sizeof(bytes_) - head_;
    }

    if (n) {
      const size_t done =
        Serial0.write(bytes_ + head_, n);

      head_ = (head_ + done) % sizeof(bytes_);
      count_ -= done;
    }
  }

  bool takeOverflow() {
    const bool had_overflow = overflow_;
    overflow_ = false;
    return had_overflow;
  }
};

inline DogNonblockingSerial& protocolSerial() {
  static DogNonblockingSerial port;
  return port;
}

// ============================================================
// CONTINUOUS SERVO DRIVER
// ============================================================

namespace forcat_continuous {

struct PulseCalibration {
  uint16_t safe_min_us = 0;
  uint16_t safe_max_us = 0;
  uint16_t neutral_us = 0;
  uint16_t neutral_low_us = 0;
  uint16_t neutral_high_us = 0;
  uint16_t open_rotation_us = 0;
  uint16_t close_rotation_us = 0;

  bool continuous_type_verified = false;
  bool neutral_verified = false;
  bool directions_verified = false;

  bool valid() const {
    return continuous_type_verified
      && neutral_verified
      && directions_verified
      && safe_min_us >= 1000
      && safe_max_us <= 2000
      && safe_min_us < safe_max_us
      && safe_max_us - safe_min_us <= 100
      && neutral_low_us >= safe_min_us
      && neutral_high_us <= safe_max_us
      && neutral_low_us <= neutral_us
      && neutral_us <= neutral_high_us
      && open_rotation_us >= safe_min_us
      && open_rotation_us <= safe_max_us
      && close_rotation_us >= safe_min_us
      && close_rotation_us <= safe_max_us
      && (
        (open_rotation_us > neutral_high_us
          && close_rotation_us < neutral_low_us)
        ||
        (open_rotation_us < neutral_low_us
          && close_rotation_us > neutral_high_us)
      );
  }
};

enum class Rotation {
  Detached,
  Neutral,
  OpenDirection,
  CloseDirection,
  Unknown
};

class Driver {
  m4::servo_bench::Output& pwm_;
  PulseCalibration calibration_{};
  bool configured_ = false;
  bool attached_ = false;
  Rotation rotation_ = Rotation::Detached;

  bool rotate(uint16_t us, Rotation direction) {
    if (!configured_ || !attached_) return false;

    const bool ok = pwm_.write(us);
    rotation_ = ok ? direction : Rotation::Unknown;
    return ok;
  }

 public:
  explicit Driver(m4::servo_bench::Output& pwm)
    : pwm_(pwm) {}

  bool boot() {
    configured_ = false;
    calibration_ = {};
    return detach();
  }

  bool configure(PulseCalibration calibration) {
    if (configured_ || attached_ || !calibration.valid()) {
      return false;
    }

    calibration_ = calibration;
    configured_ = true;
    return true;
  }

  bool attachNeutral() {
    if (!configured_ || attached_) return false;

    attached_ = true;

    const bool ok =
      pwm_.start(calibration_.neutral_us);

    rotation_ = ok ? Rotation::Neutral : Rotation::Unknown;
    return ok;
  }

  bool rotateOpen() {
    return rotate(
      calibration_.open_rotation_us,
      Rotation::OpenDirection
    );
  }

  bool rotateClose() {
    return rotate(
      calibration_.close_rotation_us,
      Rotation::CloseDirection
    );
  }

  bool neutral() {
    if (!attached_) return true;

    const bool ok =
      pwm_.write(calibration_.neutral_us);

    rotation_ = ok ? Rotation::Neutral : Rotation::Unknown;
    return ok;
  }

  bool detach() {
    const bool ok = pwm_.off();

    if (ok) {
      attached_ = false;
      rotation_ = Rotation::Detached;
    } else {
      rotation_ = Rotation::Unknown;
    }

    return ok;
  }

  bool attached() const {
    return attached_;
  }

  Rotation rotation() const {
    return rotation_;
  }
};

// ============================================================
// DISPENSING STATE MACHINE
// ============================================================

enum class Mode {
  Supervised,
  Automatic
};

enum class State {
  Disarmed,
  Armed,
  Baseline,
  Opening,
  WaitingMass,
  Closing,
  NeutralHold,
  Settling,
  AwaitingOwner,
  Complete,
  FaultClosing,
  FaultNeutral,
  Fault
};

enum class Reason {
  None,
  Config,
  Approval,
  Position,
  Weight,
  Calibration,
  Clock,
  ConflictingSample,
  Lease,
  Timeout,
  NoProgress,
  Overshoot,
  UnderTarget,
  Stopped,
  Output,
  Persistence,
  Inspection,
  Duplicate,
  Busy
};

inline const char* name(State s) {
  switch (s) {
    case State::Disarmed:
      return "DISARMED";
    case State::Armed:
      return "ARMED_NO_MOTION";
    case State::Baseline:
      return "WAIT_BASELINE";
    case State::Opening:
      return "ROTATE_OPEN_DIRECTION";
    case State::WaitingMass:
      return "NEUTRAL_WAIT_MASS";
    case State::Closing:
      return "ROTATE_CLOSE_DIRECTION";
    case State::NeutralHold:
      return "NEUTRAL_STOP_COMMAND";
    case State::Settling:
      return "WAIT_STABLE_MASS";
    case State::AwaitingOwner:
      return "MEASURED_NEEDS_OWNER_CONFIRMATION";
    case State::Complete:
      return "COMPLETE_WITH_POSITION_FEEDBACK";
    case State::FaultClosing:
      return "FAULT_BOUNDED_CLOSE_UNVERIFIED";
    case State::FaultNeutral:
      return "FAULT_NEUTRAL_COMMAND";
    default:
      return "FAULT";
  }
}

struct Sample {
  uint32_t now_ms = 0;
  uint32_t sample_at_ms = 0;
  uint32_t generation = 0;
  bool healthy = false;
  bool calibrated = false;
  bool fresh = false;
  float grams = 0;
};

struct Position {
  bool available = false;
  bool healthy = false;
  bool qualified = false;
  bool closed = false;
  bool opened = false;
  uint32_t observed_ms = 0;
};

struct Settings {
  PulseCalibration pulses{};

  uint32_t opening_ms = 0;
  uint32_t closing_ms = 0;
  uint32_t neutral_hold_ms = 0;
  uint32_t settle_ms = 0;
  uint32_t stable_span_ms = 0;
  uint32_t baseline_timeout_ms = 0;
  uint32_t settle_timeout_ms = 0;
  uint32_t no_progress_ms = 0;
  uint32_t total_timeout_ms = 0;

  float stable_range_g = 0;
  float closing_lead_g = 0;

  bool travel_timing_verified = false;
  bool closing_lead_verified = false;
  bool detach_after_neutral = false;
  bool pwm_loss_stop_verified = false;
  bool supervised_bounded_fault_close = false;
  bool supervised_early_close_trial = false;

  bool valid() const {
    return pulses.valid()
      && travel_timing_verified
      && opening_ms >= 20 && opening_ms <= 5000
      && closing_ms >= 20 && closing_ms <= 3000
      && neutral_hold_ms >= 20 && neutral_hold_ms <= 500
      && settle_ms >= 500 && settle_ms <= 5000
      && stable_span_ms >= 100 && stable_span_ms <= 1500
      && baseline_timeout_ms >= 1000
      && baseline_timeout_ms <= 10000
      && settle_timeout_ms >= settle_ms + stable_span_ms
      && settle_timeout_ms <= 10000
      && no_progress_ms >= 500 && no_progress_ms <= 10000
      && total_timeout_ms >
        opening_ms + closing_ms + neutral_hold_ms
        + settle_ms + stable_span_ms
      && total_timeout_ms <= 60000
      && std::isfinite(stable_range_g)
      && stable_range_g > 0 && stable_range_g <= 2
      && std::isfinite(closing_lead_g)
      && closing_lead_g >= 0
      && (
        supervised_early_close_trial
          ? closing_lead_g <= 15
          : closing_lead_g <= 3
      )
      && (
        closing_lead_g == 0
        || closing_lead_verified
        || supervised_early_close_trial
      )
      && (
        !detach_after_neutral
        || pwm_loss_stop_verified
      );
  }
};

class Journal {
 public:
  virtual ~Journal() = default;
  virtual bool write(bool pending, uint32_t id) = 0;
};

class Controller {
  Driver& driver_;
  Journal& journal_;
  Settings settings_{};

  Mode mode_ = Mode::Supervised;
  State state_ = State::Disarmed;
  Reason reason_ = Reason::None;

  bool configured_ = false;
  bool locked_ = true;
  bool have_clock_ = false;
  bool have_sample_ = false;
  bool baseline_valid_ = false;
  bool actual_valid_ = false;
  bool in_effect_ = false;
  bool new_sample_ = false;
  bool left_closed_ = false;
  bool open_confirmed_ = false;
  bool close_started_ = false;

  uint32_t epoch_ = 0;
  uint32_t last_now_ = 0;
  uint32_t observed_at_ = 0;
  uint32_t generation_ = 0;
  uint32_t phase_at_ = 0;
  uint32_t started_at_ = 0;
  uint32_t lease_at_ = 0;
  uint32_t opening_at_ = 0;
  uint32_t closing_at_ = 0;
  uint32_t last_progress_ = 0;
  uint32_t highwater_ = 0;
  uint32_t id_ = 0;

  unsigned arms_ = 0;
  unsigned window_count_ = 0;

  float observed_grams_ = 0;
  float baseline_ = 0;
  float actual_ = 0;
  float latest_ = 0;
  float last_progress_mass_ = 0;
  float window_[4]{};

  uint32_t window_time_[4]{};

  struct Effect {
    bool& flag;

    explicit Effect(bool& f) : flag(f) {
      flag = true;
    }

    ~Effect() {
      flag = false;
    }
  };

  template<class F>
  bool effect(F f) {
    Effect guard(in_effect_);
    return f();
  }

  bool terminal() const {
    return state_ == State::Disarmed
      || state_ == State::AwaitingOwner
      || state_ == State::Complete
      || state_ == State::Fault;
  }

  bool faultState() const {
    return state_ == State::FaultClosing
      || state_ == State::FaultNeutral
      || state_ == State::Fault;
  }

  void resetWindow() {
    window_count_ = 0;
  }

  bool clock(uint32_t now) {
    if (have_clock_
        && static_cast<uint32_t>(now - last_now_)
          > 0x7fffffffu) {
      return false;
    }

    have_clock_ = true;
    last_now_ = now;
    return true;
  }

  bool positionUsable(
      const Sample& s,
      const Position& p) const {

    return p.available
      && p.healthy
      && p.qualified
      && !(p.closed && p.opened)
      && static_cast<uint32_t>(
          s.now_ms - p.observed_ms) <= 1500;
  }

  bool closedNow(
      const Sample& s,
      const Position& p) const {

    return positionUsable(s, p)
      && p.closed
      && close_started_
      && static_cast<uint32_t>(
          p.observed_ms - closing_at_) <= 0x7fffffffu;
  }

  Reason sample(const Sample& s, bool require_new) {
    new_sample_ = false;

    if (!s.calibrated || !s.generation) {
      return Reason::Calibration;
    }

    if (!s.healthy
        || !std::isfinite(s.grams)
        || std::fabs(s.grams) > 100000
        || static_cast<uint32_t>(
            s.now_ms - s.sample_at_ms) > 1500) {
      return Reason::Weight;
    }

    if (have_sample_) {
      const auto delta =
        static_cast<uint32_t>(
          s.sample_at_ms - observed_at_);

      if (delta > 0x7fffffffu
          || (delta == 0
              && s.grams != observed_grams_)) {
        return Reason::ConflictingSample;
      }

      if (!s.fresh
          && (delta || s.grams != observed_grams_)) {
        return Reason::Weight;
      }

      new_sample_ = s.fresh && delta != 0;
    } else {
      new_sample_ = s.fresh;
    }

    if (require_new && !s.fresh) return Reason::Weight;

    if (s.fresh) {
      have_sample_ = true;
      observed_at_ = s.sample_at_ms;
      observed_grams_ = s.grams;
    }

    return Reason::None;
  }

  bool stable(float& mean) {
    if (window_count_ < 4) return false;

    const unsigned last = (window_count_ - 1) % 4;
    const unsigned first = window_count_ % 4;

    if (static_cast<uint32_t>(
          window_time_[last] - window_time_[first])
        < settings_.stable_span_ms) {
      return false;
    }

    float lo = window_[0];
    float hi = lo;
    float total = 0;

    for (float v : window_) {
      if (v < lo) lo = v;
      if (v > hi) hi = v;
      total += v;
    }

    mean = total / 4;
    return hi - lo <= settings_.stable_range_g;
  }

  void add(const Sample& s) {
    if (!new_sample_) return;

    const auto i = window_count_ % 4;
    window_[i] = s.grams;
    window_time_[i] = s.sample_at_ms;
    ++window_count_;
  }

  void compensateNeutral() {
    const bool neutral =
      effect([&] { return driver_.neutral(); });

    if (!neutral) {
      reason_ = Reason::Output;
      effect([&] { return driver_.detach(); });
      state_ = State::Fault;
    }
  }

  void neutral(uint32_t now, bool fault) {
    ++epoch_;
    phase_at_ = now;

    state_ = fault
      ? State::FaultNeutral
      : State::NeutralHold;

    if (in_effect_) return;
    compensateNeutral();
  }

  void fault(
      Reason why,
      uint32_t now,
      bool force_neutral = false) {

    if (faultState()) return;

    reason_ = why;
    locked_ = true;

    if (why != Reason::UnderTarget
        && !(why == Reason::Overshoot
          && state_ == State::Settling
          && actual_valid_)) {
      actual_valid_ = false;
    }

    const bool can_close =
      !force_neutral
      && settings_.supervised_bounded_fault_close
      && mode_ == Mode::Supervised
      && (
        state_ == State::Opening
        || state_ == State::WaitingMass
        || state_ == State::Closing
      )
      && why != Reason::Clock
      && why != Reason::Position
      && why != Reason::Output
      && !in_effect_;

    if (can_close) {
      ++epoch_;

      if (state_ != State::Closing) {
        closing_at_ = now;
        close_started_ = true;
      }

      state_ = State::FaultClosing;
      const auto epoch = epoch_;

      const bool ok =
        effect([&] { return driver_.rotateClose(); });

      if (epoch != epoch_) {
        compensateNeutral();
        return;
      }

      if (!ok) {
        reason_ = Reason::Output;
        neutral(now, true);
      }

      return;
    }

    neutral(now, true);
  }

  void open(const Sample& s) {
    ++epoch_;

    state_ = State::Opening;
    opening_at_ = s.now_ms;
    last_progress_ = s.now_ms;
    last_progress_mass_ = 0;
    resetWindow();

    const auto epoch = epoch_;

    const bool attached =
      driver_.attached()
        ? driver_.rotation() == Rotation::Neutral
        : effect([&] {
            return driver_.attachNeutral();
          });

    if (epoch != epoch_ || state_ != State::Opening) {
      compensateNeutral();
      return;
    }

    if (!attached) {
      fault(Reason::Output, s.now_ms, true);
      return;
    }

    const bool ok =
      effect([&] { return driver_.rotateOpen(); });

    if (epoch != epoch_ || state_ != State::Opening) {
      compensateNeutral();
      return;
    }

    if (!ok) fault(Reason::Output, s.now_ms, true);
  }

  void close(const Sample& s) {
    ++epoch_;

    state_ = State::Closing;
    closing_at_ = s.now_ms;
    close_started_ = true;

    const auto epoch = epoch_;

    const bool ok =
      effect([&] { return driver_.rotateClose(); });

    if (epoch != epoch_ || state_ != State::Closing) {
      compensateNeutral();
      return;
    }

    if (!ok) fault(Reason::Output, s.now_ms, true);
  }

 public:
  Controller(Driver& driver, Journal& journal)
    : driver_(driver), journal_(journal) {}

  void boot(
      bool initialized,
      bool pending,
      uint32_t last_id) {

    if (in_effect_) return;

    ++epoch_;
    state_ = State::Disarmed;
    reason_ = Reason::None;
    configured_ = false;
    locked_ = !initialized || pending;

    have_clock_ = false;
    have_sample_ = false;
    baseline_valid_ = false;
    actual_valid_ = false;
    left_closed_ = false;
    open_confirmed_ = false;
    close_started_ = false;

    highwater_ = last_id;
    id_ = 0;
    arms_ = 0;
    resetWindow();

    if (!effect([&] { return driver_.boot(); })) {
      state_ = State::Fault;
      reason_ = Reason::Output;
      locked_ = true;
    }
  }

  bool configure(Settings s) {
    if (in_effect_
        || state_ != State::Disarmed
        || locked_
        || configured_
        || arms_
        || !s.valid()) {
      return false;
    }

    if (!driver_.configure(s.pulses)) return false;

    settings_ = s;
    configured_ = true;
    return true;
  }

  Reason arm(
      const Sample& s,
      const Position& p,
      Mode mode,
      bool owner_approved) {

    if (in_effect_) return Reason::Busy;
    if (locked_) return Reason::Inspection;
    if (!configured_) return Reason::Config;

    if (mode == Mode::Automatic
        && settings_.supervised_early_close_trial) {
      return Reason::Config;
    }

    if (!owner_approved) return Reason::Approval;

    if ((state_ != State::Disarmed
          && state_ != State::Complete)
        || arms_ >= 3) {
      return Reason::Busy;
    }

    if (!clock(s.now_ms)) return Reason::Clock;

    const auto ok = sample(s, true);
    if (ok != Reason::None) return ok;

    if (p.available && !positionUsable(s, p)) {
      return Reason::Position;
    }

    if (mode == Mode::Automatic
        && (!positionUsable(s, p) || !p.closed)) {
      return Reason::Position;
    }

    mode_ = mode;
    generation_ = s.generation;
    state_ = State::Armed;
    phase_at_ = lease_at_ = s.now_ms;
    ++arms_;

    return Reason::None;
  }

  Reason start(uint32_t id, const Sample& s) {
    if (in_effect_) return Reason::Busy;

    if (!id || id > 0xffffffu || id <= highwater_) {
      return Reason::Duplicate;
    }

    if (state_ != State::Armed) return Reason::Busy;

    if (!clock(s.now_ms)) {
      fault(Reason::Clock, last_now_, true);
      return reason_;
    }

    if (s.now_ms - lease_at_ >= 1500) {
      fault(Reason::Lease, s.now_ms, true);
      return reason_;
    }

    if (s.now_ms - phase_at_ >= 2000) {
      fault(Reason::Timeout, s.now_ms, true);
      return reason_;
    }

    const auto ok = sample(s, true);

    if (ok != Reason::None || s.generation != generation_) {
      fault(
        ok == Reason::None ? Reason::Calibration : ok,
        s.now_ms,
        true
      );
      return reason_;
    }

    highwater_ = id;
    id_ = id;
    locked_ = true;
    state_ = State::Baseline;
    started_at_ = phase_at_ = lease_at_ = s.now_ms;

    baseline_valid_ = false;
    actual_valid_ = false;
    left_closed_ = false;
    open_confirmed_ = false;
    close_started_ = false;
    resetWindow();

    const auto epoch = epoch_;

    const bool saved =
      effect([&] {
        return journal_.write(true, id);
      });

    if (epoch != epoch_ || state_ != State::Baseline) {
      compensateNeutral();
      return reason_;
    }

    if (!saved) {
      fault(Reason::Persistence, s.now_ms, true);
      return reason_;
    }

    return Reason::None;
  }

  void heartbeat(uint32_t now) {
    if (in_effect_ || terminal() || faultState()) return;

    if (!clock(now)) {
      fault(Reason::Clock, last_now_, true);
      return;
    }

    lease_at_ = now;
  }

  void stop(uint32_t now) {
    if (state_ == State::FaultNeutral
        || state_ == State::Fault) {
      return;
    }

    reason_ = Reason::Stopped;
    locked_ = true;
    actual_valid_ = false;
    neutral(now, true);
  }

  void tick(const Sample& s, const Position& p) {
    if (in_effect_ || terminal()) return;

    if (!clock(s.now_ms)) {
      reason_ = Reason::Clock;
      locked_ = true;
      ++epoch_;
      state_ = State::Fault;

      effect([&] { return driver_.neutral(); });
      effect([&] { return driver_.detach(); });
      return;
    }

    if (state_ == State::FaultClosing) {
      if (s.now_ms - started_at_
            >= settings_.total_timeout_ms
          || closedNow(s, p)
          || s.now_ms - closing_at_
            >= settings_.closing_ms) {
        neutral(s.now_ms, true);
      }

      return;
    }

    if (state_ == State::FaultNeutral) {
      if (s.now_ms - phase_at_
          < settings_.neutral_hold_ms) {
        return;
      }

      const auto epoch = epoch_;

      if (settings_.detach_after_neutral) {
        const bool off =
          effect([&] { return driver_.detach(); });

        if (epoch != epoch_) {
          compensateNeutral();
          return;
        }

        if (!off) {
          reason_ = Reason::Output;
          state_ = State::Fault;
          locked_ = true;
          return;
        }
      }

      state_ = State::Fault;
      return;
    }

    if (s.now_ms - lease_at_ >= 1500) {
      fault(Reason::Lease, s.now_ms, true);
      return;
    }

    if (state_ == State::Armed) {
      if (s.now_ms - phase_at_ >= 2000) {
        fault(Reason::Timeout, s.now_ms, true);
      }
      return;
    }

    if (s.now_ms - started_at_
        >= settings_.total_timeout_ms) {
      fault(Reason::Timeout, s.now_ms, true);
      return;
    }

    const auto ok = sample(s, false);

    if (ok != Reason::None || s.generation != generation_) {
      fault(
        ok == Reason::None ? Reason::Calibration : ok,
        s.now_ms
      );
      return;
    }

    if (p.available && !positionUsable(s, p)) {
      fault(Reason::Position, s.now_ms, true);
      return;
    }

    if (mode_ == Mode::Automatic
        && !positionUsable(s, p)) {
      fault(Reason::Position, s.now_ms, true);
      return;
    }

    if (baseline_valid_) {
      latest_ = s.grams - baseline_;

      if (latest_ > 40.f) {
        fault(Reason::Overshoot, s.now_ms);
        return;
      }

      if (latest_ < -settings_.stable_range_g) {
        fault(Reason::Weight, s.now_ms, true);
        return;
      }
    }

    if (state_ == State::NeutralHold) {
      if (mode_ == Mode::Automatic && !closedNow(s, p)) {
        fault(Reason::Position, s.now_ms, true);
        return;
      }

      if (s.now_ms - phase_at_
          < settings_.neutral_hold_ms) {
        return;
      }

      const auto epoch = epoch_;

      if (settings_.detach_after_neutral) {
        const bool off =
          effect([&] { return driver_.detach(); });

        if (epoch != epoch_) {
          compensateNeutral();
          return;
        }

        if (!off) {
          reason_ = Reason::Output;
          state_ = State::Fault;
          locked_ = true;
          return;
        }
      }

      state_ = State::Settling;
      phase_at_ = s.now_ms;
      resetWindow();
      return;
    }

    if (state_ == State::Baseline) {
      if (mode_ == Mode::Automatic && !p.closed) {
        fault(Reason::Position, s.now_ms, true);
        return;
      }

      if (s.now_ms - phase_at_
          >= settings_.baseline_timeout_ms) {
        fault(Reason::Timeout, s.now_ms, true);
        return;
      }

      add(s);

      float mean = 0;

      if (stable(mean)) {
        baseline_ = mean;
        baseline_valid_ = true;
        latest_ = 0;
        open(s);
      }

      return;
    }

    if (positionUsable(s, p)
        && static_cast<uint32_t>(
            p.observed_ms - opening_at_) <= 0x7fffffffu) {
      if (!p.closed) left_closed_ = true;
      if (p.opened) open_confirmed_ = true;
    }

    if (state_ == State::Opening
        || state_ == State::WaitingMass) {

      if (new_sample_
          && latest_ >= 35.f - settings_.closing_lead_g) {
        close(s);
        return;
      }

      if (new_sample_
          && latest_ - last_progress_mass_
            >= settings_.stable_range_g / 4) {
        last_progress_ = s.now_ms;
        last_progress_mass_ = latest_;
      }

      if (s.now_ms - last_progress_
          >= settings_.no_progress_ms) {
        fault(Reason::NoProgress, s.now_ms);
        return;
      }

      if (state_ == State::Opening
          && (open_confirmed_
              || s.now_ms - opening_at_
                >= settings_.opening_ms)) {

        if (mode_ == Mode::Automatic && !open_confirmed_) {
          fault(Reason::Position, s.now_ms, true);
          return;
        }

        state_ = State::WaitingMass;
        const auto epoch = epoch_;

        const bool neutral_ok =
          effect([&] { return driver_.neutral(); });

        if (epoch != epoch_) {
          compensateNeutral();
          return;
        }

        if (!neutral_ok) {
          fault(Reason::Output, s.now_ms, true);
        }
      }

      return;
    }

    if (state_ == State::Closing) {
      if (closedNow(s, p)) {
        neutral(s.now_ms, false);
        return;
      }

      if (s.now_ms - closing_at_ >= settings_.closing_ms) {
        if (mode_ == Mode::Automatic) {
          fault(Reason::Position, s.now_ms, true);
          return;
        }

        neutral(s.now_ms, false);
      }

      return;
    }

    if (state_ == State::Settling) {
      if (mode_ == Mode::Automatic && !closedNow(s, p)) {
        fault(Reason::Position, s.now_ms, true);
        return;
      }

      if (s.now_ms - phase_at_
          >= settings_.settle_timeout_ms) {
        fault(Reason::Timeout, s.now_ms, true);
        return;
      }

      if (s.now_ms - phase_at_ < settings_.settle_ms) {
        return;
      }

      add(s);
      float mean = 0;

      if (!stable(mean)) return;

      actual_ = mean - baseline_;
      actual_valid_ = true;

      if (actual_ < 30.f) {
        fault(Reason::UnderTarget, s.now_ms, true);
        return;
      }

      if (actual_ > 40.f) {
        fault(Reason::Overshoot, s.now_ms, true);
        return;
      }

      if (mode_ == Mode::Supervised) {
        state_ = State::AwaitingOwner;
        locked_ = true;
        return;
      }

      if (!left_closed_
          || !open_confirmed_
          || !closedNow(s, p)) {
        fault(Reason::Position, s.now_ms, true);
        return;
      }

      const auto epoch = epoch_;

      const bool saved =
        effect([&] {
          return journal_.write(false, id_);
        });

      if (epoch != epoch_ || state_ != State::Settling) {
        locked_ = true;

        const bool restored =
          effect([&] {
            return journal_.write(true, id_);
          });

        if (!restored) reason_ = Reason::Persistence;

        compensateNeutral();
        return;
      }

      if (!saved) {
        fault(Reason::Persistence, s.now_ms, true);
        return;
      }

      locked_ = false;
      state_ = State::Complete;
    }
  }

  State state() const { return state_; }
  Reason reason() const { return reason_; }
  uint32_t id() const { return id_; }
  uint32_t highwater() const { return highwater_; }
  bool inspectionRequired() const { return locked_; }
  bool baselineValid() const { return baseline_valid_; }

  float closeTriggerGrams() const {
    return 35.f - settings_.closing_lead_g;
  }

  float baselineGrams() const {
    return baseline_valid_ ? baseline_ : NAN;
  }

  float latestGrams() const {
    return baseline_valid_ ? latest_ : NAN;
  }

  float actualGrams() const {
    return actual_valid_ ? actual_ : NAN;
  }
};

// ============================================================
// READ-ONLY HX711 ADAPTER
// ============================================================

class HxAdapter {
  m4::ScaleCalibration previous_{};
  bool have_ = false;
  bool exhausted_ = false;
  uint32_t generation_ = 0;

 public:
  Sample read(const m4::Hx711& hx, uint32_t now) {
    const auto& cal = hx.calibration;

    const bool changed =
      !have_
      || previous_.tared != cal.tared
      || previous_.calibrated != cal.calibrated
      || std::memcmp(
          &previous_.tare_counts,
          &cal.tare_counts,
          sizeof(double))
      || std::memcmp(
          &previous_.grams_per_count,
          &cal.grams_per_count,
          sizeof(double));

    if (changed) {
      if (generation_ == UINT32_MAX) {
        exhausted_ = true;
      } else {
        ++generation_;
      }

      previous_ = cal;
      have_ = true;
    }

    return {
      now,
      hx.grams.sampled_at_ms,
      exhausted_ ? 0 : generation_,
      hx.status.health == m4::Health::HEALTHY
        && hx.grams.valid,
      cal.valid() && !exhausted_,
      hx.grams.fresh,
      hx.grams.valid ? hx.grams.value : 0
    };
  }
};

}

// ============================================================
// HC-SR04 DRIVER
// ============================================================

namespace m4 {

class MedianFilter {
 public:
  bool add(float value) {
    if (!std::isfinite(value)) return false;

    values_[cursor_] = value;
    cursor_ = (cursor_ + 1) % 5;

    if (count_ < 5) ++count_;
    return true;
  }

  void clear() {
    count_ = cursor_ = 0;
  }

  float median() const {
    if (!count_) return 0;

    float sorted[5];

    for (uint8_t i = 0; i < count_; ++i) {
      sorted[i] = values_[i];
    }

    for (uint8_t i = 1; i < count_; ++i) {
      float value = sorted[i];
      int j = i - 1;

      while (j >= 0 && sorted[j] > value) {
        sorted[j + 1] = sorted[j];
        --j;
      }

      sorted[j + 1] = value;
    }

    return sorted[count_ / 2];
  }

 private:
  float values_[5]{};
  uint8_t count_ = 0;
  uint8_t cursor_ = 0;
};

struct UltrasonicConfig {
  Pin trigger{};
  Pin echo{};
  float minimum_cm = 0;
  float maximum_cm = 0;
  uint32_t echo_timeout_us = 30000;
  float sound_cm_per_us = 0.0343f;
};

enum class EchoPhase : uint8_t {
  IDLE,
  PULSE_LOW,
  PULSE_HIGH,
  WAIT_RISE,
  WAIT_FALL
};

class Ultrasonic {
 public:
  explicit Ultrasonic(PinIO& io) : io_(io) {}

  bool begin(UltrasonicConfig config) {
    active_ = false;
    phase_ = EchoPhase::IDLE;
    raw = filtered = {};
    config_ = config;
    timeout_count_ = 0;

    if (!outputValid(io_, config.trigger)
        || !inputValid(io_, config.echo)
        || config.trigger.number == config.echo.number
        || !std::isfinite(config.minimum_cm)
        || !std::isfinite(config.maximum_cm)
        || config.minimum_cm <= 0
        || config.maximum_cm <= config.minimum_cm
        || !std::isfinite(config.sound_cm_per_us)
        || config.sound_cm_per_us <= 0
        || config.echo_timeout_us < 100
        || config.echo_timeout_us > 100000) {
      status = {};
      return false;
    }

    io_.output(config.trigger.number);
    io_.write(config.trigger.number, false);
    io_.input(config.echo.number, Pull::NONE);

    active_ = true;
    phase_ = EchoPhase::IDLE;
    filter_.clear();
    status = {Health::INITIALIZING, Reason::NONE};
    return true;
  }

  bool trigger(uint32_t now_us) {
    if (!active_ || phase_ != EchoPhase::IDLE) {
      return false;
    }

    raw.fresh = filtered.fresh = false;

    if (io_.read(config_.echo.number)) {
      fail(Reason::INVALID_DATA);
      return false;
    }

    io_.write(config_.trigger.number, false);
    delayMicroseconds(2);
    io_.write(config_.trigger.number, true);
    delayMicroseconds(18);
    io_.write(config_.trigger.number, false);
    phase_ = EchoPhase::WAIT_RISE;
    began_ = phase_at_ = micros();
    return true;
  }

  void poll(uint32_t now_us, uint32_t now_ms) {
    raw.fresh = filtered.fresh = false;

    if (!active_ || phase_ == EchoPhase::IDLE) return;

    if (static_cast<uint32_t>(now_us - began_)
        >= config_.echo_timeout_us) {
      fail(Reason::TIMEOUT);
      return;
    }

    switch (phase_) {
      case EchoPhase::PULSE_LOW:
        if (static_cast<uint32_t>(
              now_us - phase_at_) >= 2) {
          io_.write(config_.trigger.number, true);
          phase_ = EchoPhase::PULSE_HIGH;
          phase_at_ = now_us;
        }
        break;

      case EchoPhase::PULSE_HIGH:
        if (static_cast<uint32_t>(
              now_us - phase_at_) >= 20) {
          io_.write(config_.trigger.number, false);
          phase_ = EchoPhase::WAIT_RISE;
        }
        break;

      case EchoPhase::WAIT_RISE:
        if (io_.read(config_.echo.number)) {
          rise_at_ = now_us;
          phase_ = EchoPhase::WAIT_FALL;
        }
        break;

      case EchoPhase::WAIT_FALL:
        if (!io_.read(config_.echo.number)) {
          const auto width =
            static_cast<uint32_t>(now_us - rise_at_);

          const float distance =
            static_cast<float>(width)
            * config_.sound_cm_per_us / 2;

          phase_ = EchoPhase::IDLE;

          if (!width
              || !std::isfinite(distance)
              || distance < config_.minimum_cm
              || distance > config_.maximum_cm) {
            fail(Reason::RANGE_INVALID);
            return;
          }

          raw = {true, distance, now_ms, true};
          filter_.add(distance);

          filtered = {
            true, filter_.median(), now_ms, true
          };

          status = {Health::HEALTHY, Reason::NONE};
        }
        break;

      default:
        break;
    }
  }

  bool busy() const {
    return phase_ != EchoPhase::IDLE;
  }

  Status status{};
  Reading<float> raw{};
  Reading<float> filtered{};

 private:
  void fail(Reason reason) {
    if (reason == Reason::TIMEOUT
        && timeout_count_ != UINT32_MAX) {
      ++timeout_count_;
    }

    if (active_) {
      io_.write(config_.trigger.number, false);
    }

    raw = {};
    phase_ = EchoPhase::IDLE;

    status = {
      reason == Reason::TIMEOUT
        ? Health::NOT_CONNECTED
        : Health::FAULT,
      reason
    };
  }

  PinIO& io_;
  UltrasonicConfig config_{};
  MedianFilter filter_{};
  EchoPhase phase_ = EchoPhase::IDLE;
  uint32_t began_ = 0;
  uint32_t phase_at_ = 0;
  uint32_t rise_at_ = 0;
  bool active_ = false;
  uint32_t timeout_count_ = 0;
};

}

// ============================================================
// CAT + NEAR GATE
// ============================================================

namespace cat_test {

class Gate {
  uint32_t ai_at_ = 0;
  uint32_t near_at_ = 0;
  uint32_t source_seq_ = 0;
  unsigned near_count_ = 0;
  bool cat_ = false;
  bool visited_ = false;

 public:
  bool ai(
      uint32_t now,
      uint32_t seq,
      uint32_t age,
      uint32_t transport_age,
      unsigned confidence,
      bool cat) {

    if (!seq
        || seq <= source_seq_
        || age > 750
        || transport_age > 750
        || age + transport_age > 750
        || confidence > 1000) {
      return false;
    }

    source_seq_ = seq;
    ai_at_ = now - age - transport_age;
    cat_ = cat && confidence >= 800;

    if (!cat_) near_count_ = 0;
    return true;
  }

  bool catFresh(uint32_t now) const {
    return cat_ && uint32_t(now - ai_at_) <= 750;
  }

  void near(uint32_t now, bool valid, float cm) {
    if (!catFresh(now)
        || !valid
        || !std::isfinite(cm)
        || cm < 2
        || cm > 20) {
      near_count_ = 0;
      return;
    }

    if (near_count_
        && uint32_t(now - near_at_) > 250) {
      near_count_ = 0;
    }

    near_at_ = now;
    if (near_count_ < 3) ++near_count_;
  }

  bool ready(uint32_t now) const {
    return !visited_
      && catFresh(now)
      && near_count_ >= 3
      && uint32_t(now - near_at_) <= 200;
  }

  void consume() {
    visited_ = true;
  }

  bool visited() const {
    return visited_;
  }

  void inspected() {
    visited_ = false;
    near_count_ = 0;
    cat_ = false;
  }
};

inline uint16_t crc(const char* p, unsigned n) {
  uint16_t c = 0xffff;

  for (unsigned i = 0; i < n; ++i) {
    c ^= uint16_t(uint8_t(p[i])) << 8;

    for (unsigned j = 0; j < 8; ++j) {
      c = c & 0x8000
        ? uint16_t((c << 1) ^ 0x1021)
        : uint16_t(c << 1);
    }
  }

  return c;
}

inline bool number(const char* s, uint32_t& v) {
  if (!s || !*s) return false;
  v = 0;

  for (; *s; ++s) {
    if (*s < '0'
        || *s > '9'
        || v >
          (UINT32_MAX - unsigned(*s - '0')) / 10) {
      return false;
    }

    v = v * 10 + unsigned(*s - '0');
  }

  return true;
}

struct Packet {
  char* op = nullptr;
  char* args[5]{};
  unsigned count = 0;
  uint32_t seq = 0;
  uint32_t echo = 0;
};

class Receiver {
  uint32_t last_ = 0;

 public:
  uint32_t last() const {
    return last_;
  }

  bool parse(
      char* line,
      uint32_t boot,
      uint32_t now,
      Packet& p) {

    p = {};

    char* star = std::strchr(line, '*');

    if (!star || std::strlen(star + 1) != 4) {
      return false;
    }

    uint16_t expected = 0;

    for (char* c = star + 1; *c; ++c) {
      unsigned n;

      if (*c >= '0' && *c <= '9') {
        n = *c - '0';
      } else if (*c >= 'A' && *c <= 'F') {
        n = *c - 'A' + 10;
      } else {
        return false;
      }

      expected = uint16_t(expected * 16 + n);
    }

    if (crc(line, unsigned(star - line)) != expected) {
      return false;
    }

    *star = 0;

    char* words[10]{};
    unsigned n = 0;
    char* save = nullptr;

    for (char* s = strtok_r(line, " ", &save);
         s;
         s = strtok_r(nullptr, " ", &save)) {
      if (n == 10) return false;
      words[n++] = s;
    }

    uint32_t b = 0;

    if (n < 5
        || std::strcmp(words[0], "FC1")
        || !number(words[1], b)
        || b != boot
        || !number(words[2], p.seq)
        || !p.seq
        || p.seq <= last_
        || !number(words[3], p.echo)
        || uint32_t(now - p.echo) > 750) {
      return false;
    }

    p.op = words[4];
    p.count = n - 5;

    for (unsigned i = 0; i < p.count; ++i) {
      p.args[i] = words[i + 5];
    }

    last_ = p.seq;
    return true;
  }
};

}

// ============================================================
// USER SETTINGS
//
// CURRENT TEST: LEAVE THESE VALUES UNCHANGED.
// HX711 RAW DOES NOT NEED SERVO SETTINGS OR CALIBRATION.
//
// Before a future supervised dispensing test, fill actual measured
// neutral/deadband/directions/travel timing.
// ============================================================

namespace user_settings {

inline forcat_continuous::Settings settings() {
  forcat_continuous::Settings s;

  s.pulses.safe_min_us = 0;
  s.pulses.safe_max_us = 0;

  s.pulses.neutral_us = 0;
  s.pulses.neutral_low_us = 0;
  s.pulses.neutral_high_us = 0;

  s.pulses.open_rotation_us = 0;
  s.pulses.close_rotation_us = 0;

  s.pulses.continuous_type_verified = false;
  s.pulses.neutral_verified = false;
  s.pulses.directions_verified = false;

  s.opening_ms = 0;
  s.closing_ms = 0;
  s.travel_timing_verified = false;

  s.neutral_hold_ms = 100;
  s.settle_ms = 1000;
  s.stable_span_ms = 200;

  s.baseline_timeout_ms = 5000;
  s.settle_timeout_ms = 6000;
  s.no_progress_ms = 3000;
  s.total_timeout_ms = 20000;
  s.stable_range_g = 1;

  // PCB commissioning target: measured 35g, no early-close trial offset.
  s.closing_lead_g = 0;
  s.supervised_early_close_trial = false;

  s.detach_after_neutral = false;
  s.supervised_bounded_fault_close = false;

  return s;
}

// NVS is read first.
// Do not fill approximate or historical offsets here.
// grams_per_count is g/count, NOT counts/g.
constexpr bool exact_calibration_import_reviewed = false;
constexpr double tare_counts = 0;
constexpr double grams_per_count = 0;
constexpr const char* calibration_provenance = "UNSET";

constexpr bool hc_sr04_wiring_reviewed = false;
constexpr float hc_min_cm = 2;
constexpr float hc_max_cm = 400;

}

// ============================================================
// APPLICATION
// ============================================================

using namespace forcat_continuous;

namespace {

class PersistentJournal : public Journal {
 public:
  bool initialized = false;
  bool pending = false;
  bool corrupt = false;
  uint32_t last = 0;

  void load() {
    Preferences p;

    if (!p.begin("fc-cr-test", true)) return;

    if (p.isKey("journal")) {
      uint8_t b[12]{};

      if (p.getBytesLength("journal") != 12
          || p.getBytes("journal", b, 12) != 12
          || b[0] != 'C'
          || b[1] != 'R'
          || b[2] != 1
          || b[3] > 1
          || m4::calibration_record::get(b + 10, 2)
            != uart_v1::crc16(b, 10)) {
        corrupt = true;
      } else {
        last = uint32_t(
          m4::calibration_record::get(b + 4, 4));

        pending = b[3];
        initialized = last <= 0xffffffu;

        if (!initialized) corrupt = true;
      }
    }

    p.end();
  }

  bool write(bool value, uint32_t id) override {
    if (corrupt || id < last || id > 0xffffffu) {
      return false;
    }

    uint8_t b[12]{'C', 'R', 1, uint8_t(value)};

    m4::calibration_record::put(b + 4, id, 4);

    m4::calibration_record::put(
      b + 10,
      uart_v1::crc16(b, 10),
      2
    );

    Preferences p;

    if (!p.begin("fc-cr-test", false)) return false;

    const bool ok =
      p.putBytes("journal", b, 12) == 12;

    p.end();

    if (ok) {
      initialized = true;
      pending = value;
      last = id;
    }

    return ok;
  }
};

m4::ArduinoPins pins;
m4::Hx711 hx(pins);
cat_proximity::Window cat_near;
m4::Ultrasonic hc(pins);       // HC-SR04 #1, near cat
m4::Ultrasonic hc2(pins);      // HC-SR04 E2: food reservoir
m4::Ultrasonic bowl_d1(pins); // HC-SR04 D1: drinking bowl
m4::Ultrasonic tank_d2(pins);// HC-SR04 D2: water reservoir

constexpr int PIN_OLED_SDA = 8;
constexpr int PIN_OLED_SCL = 9;
constexpr int PIN_PIR = 11;
constexpr int PIN_BUTTON = 21;
constexpr bool USE_CLOSE_LIMIT_SWITCH = false; // Timed closure selected by owner.
constexpr int PIN_CLOSE_LIMIT = 47; // V-153-1C25 limit switch (COM -> GND, NO -> GPIO47)
constexpr uint32_t MAX_DISTANCE_AGE_MS = 4500;
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
bool oled_ok = false;
bool sensors_enabled = false;
// V12 BENCH CONFIGURATION: sensors that have previously been tested are
// enabled on boot.  IMPORTANT: ONLY FLASH THIS CONFIGURATION AFTER verifying
// that ALL 5V ultrasonic ECHO pins and PIR OUT reach ESP32 at <= 3.3V.
// Change this to false until external level shifters have been installed.
constexpr bool V12_AUTO_ENABLE_SENSORS_IF_LEVEL_SHIFTED = true;
bool motion_active = false;
bool button_down = false;
bool button_raw_old = false;
uint32_t button_changed_ms = 0;
bool limit_closed = false;
bool limit_raw_old = false;
uint32_t limit_changed_ms = 0;
bool physical_closed_verified = false;
uint32_t last_oled_ms = 0;
uint32_t last_distance_trigger_ms = 0;
uint8_t ping_step = 0;
uint8_t other_sensor_idx = 0;
float water_full_candidate = NAN;
float water_empty_candidate = NAN;
bool water_full_staged = false;
bool water_empty_staged = false;


m4::LedcServoOutput pwm;
Driver motor(pwm);
PersistentJournal journal;
Controller control(motor, journal);

HxAdapter adapter;
cat_test::Gate gate;
cat_test::Receiver receiver;

uint32_t boot_id = 0;
uint32_t last_hb = 0;
uint32_t permit_at = 0;

uint32_t last_status = 0;

bool configured = false;
bool inspected = false;
bool permit = false;
bool hc_active = false; // set only when sensor voltage checks confirmed via sensors_on
bool have_hb = false;

const char* calibration_source = "NOT_CALIBRATED";
const char* calibration_load = "NOT_ATTEMPTED";

// Golden UNO procedure on ESP32-S3: signed A128 raw, median-3,
// 15-sample empty tare, known-weight reference, then saved g/count.
// Historical UNO offset (-668483) / scale (-1064.4473 counts/g)
// must NOT be imported automatically into a different ADC/rig.
enum class BenchCal : uint8_t { Idle, Tare, Reference, Retare };
BenchCal bench_cal = BenchCal::Idle;
uint32_t bench_cal_started = 0;
double bench_known_g = 0;
m4::CalibrationRecord bench_record{};
m4::NvsCalibration bench_nvs;

void serviceBenchCal(uint32_t now);
bool startBenchCal(BenchCal kind, double known_g, uint32_t now);
void reply(uint32_t seq, bool ok, const char* detail);

bool ultrasonicBusy() {
  // sensors_off must not freeze HX/OLED/Serial while a previous ECHO is pending.
  return sensors_enabled && (hc.busy() || hc2.busy() || bowl_d1.busy() || tank_d2.busy());
}

float recentCm(const m4::Ultrasonic& u, uint32_t now) {
  return sensors_enabled && u.filtered.valid
      && uint32_t(now - u.filtered.sampled_at_ms) <= MAX_DISTANCE_AGE_MS
      ? u.filtered.value : NAN;
}

// D1=bowl, D2=reservoir. Old water geometry belonged to a different role.
// Water percentage and pump commissioning are explicitly deferred by owner.
float currentWaterPercent(uint32_t now) {
  (void)now;
  return NAN;
}

bool beginAllSensors() {
  // Do not run this until voltage dividers/level shifters are verified.
  if (sensors_enabled) return true;
  const bool a = hc.begin({{12,true},{13,true}, 2.0f, 400.0f, 30000, 0.0343f});
  const bool b = hc2.begin({{16,true},{17,true}, 2.0f, 400.0f, 30000, 0.0343f});
  // Allow full range from 2.0cm to 450.0cm so close-range tank levels (<20cm) are never rejected.
  const bool c = bowl_d1.begin({{14,true},{15,true}, 2.0f, 400.0f, 30000, 0.0343f});
  const bool d = tank_d2.begin({{18,true},{19,true}, 2.0f, 400.0f, 30000, 0.0343f});
  sensors_enabled = a && b && c && d;
  hc_active = sensors_enabled;
  motion_active = sensors_enabled;
  if (motion_active) pinMode(PIN_PIR, INPUT);
  last_distance_trigger_ms = millis() - 90;
  ping_step = other_sensor_idx = 0;
  return sensors_enabled;
}

void tickUltrasonic(uint32_t now) {
  if (!sensors_enabled || ultrasonicBusy()) return;
  const uint32_t real_now = millis();
  if (uint32_t(real_now - last_distance_trigger_ms) < 90) return;
  last_distance_trigger_ms = real_now;
  if ((ping_step++ % 2u) == 0u) {
    hc.trigger(micros());
  } else {
    switch (other_sensor_idx++ % 3u) {
      case 0: hc2.trigger(micros()); break;
      case 1: bowl_d1.trigger(micros()); break;
      default: tank_d2.trigger(micros()); break;
    }
  }
}

namespace bench_v8 {
void beginManualFeed(uint32_t now, const char* source);
extern uint32_t button_request_count;
extern uint32_t button_last_press_ms;
}

void tickButton(uint32_t now) {
  const bool raw = digitalRead(PIN_BUTTON) == LOW;
  if (now < 3500) {
    button_raw_old = button_down = raw;
    button_changed_ms = now;
    return;
  }
  if (raw != button_raw_old) {
    button_raw_old = raw;
    button_changed_ms = now;
  }
  if (uint32_t(now - button_changed_ms) >= 50 && raw != button_down) {
    button_down = raw;
    if (button_down) {
      ++bench_v8::button_request_count;
      bench_v8::button_last_press_ms = now;
      protocolSerial().printf("MANUAL_BUTTON_GPIO21: PRESSED (count=%lu) -> TRIGGERING SERVO FEED!\n",
        (unsigned long)bench_v8::button_request_count);
      bench_v8::beginManualFeed(now, "BUTTON_GPIO21");
    }
  }
}

void tickLimitSwitch(uint32_t now) {
  if (!USE_CLOSE_LIMIT_SWITCH) return;
  const bool raw = digitalRead(PIN_CLOSE_LIMIT) == LOW;
  if (raw != limit_raw_old) {
    limit_raw_old = raw;
    limit_changed_ms = now;
  }
  // Fast 10ms debounce so closing gate stops immediately upon touching V-153-1C25 lever
  if (uint32_t(now - limit_changed_ms) >= 10 && raw != limit_closed) {
    limit_closed = raw;
    if (limit_closed) {
      physical_closed_verified = true;
      protocolSerial().print("LIMIT_SWITCH_GPIO47: PRESSED (CHAM DIEM KET THUC DONG NAP)\n");
    } else {
      physical_closed_verified = false;
      protocolSerial().print("LIMIT_SWITCH_GPIO47: RELEASED (NAP DANG MO)\n");
    }
  }
}

// ============================================================
// SUPERVISED BENCH TESTS (NO JETSON AI)
// 1: CAT detection is simulated, but HC1 distance + HX711 are REAL.
// 2: DOG detection is simulated; buzzer pattern plays once per command.
// ALL servo motion is bounded; gate angle is NOT measurable without switches.
// ============================================================
namespace bench_v8 {

constexpr int BUZZER_GPIO = 2; // buzzer wired on GPIO2 per user hardware
constexpr uint16_t SERVO_OPEN_US = 1350; // Faster OPEN trial; needs physical travel verification.
constexpr uint16_t SERVO_CLOSE_US = 1600; // UNO-tested: close LEFT.
constexpr uint16_t SERVO_NEUTRAL_US = 1500;
constexpr float CAT_MIN_CM = 2.0f;
constexpr float CAT_MAX_CM = 30.0f;
constexpr float CLOSE_AT_G = 35.0f;  // Target: close on the first measured added-mass sample >=35g.
constexpr float MAX_NORMAL_G = 40.0f;
constexpr uint32_t CAT_WAIT_TIMEOUT_MS = 30000;
constexpr uint32_t WEIGHT_WAIT_TIMEOUT_MS = 25000;
constexpr uint32_t HX_WAIT_TIMEOUT_MS = 25000;
constexpr uint32_t MAX_SERVO_ACTIVE_MS = 5000;

uint16_t open_ms = 900; // Shorter OPEN for the faster pulse; initial physical trial.
uint16_t close_ms = 1450; // Owner requested a small additional closing travel (owner-supervised relative travel calibration).
uint32_t servo_move_for_ms = 0;

// A completed timed stroke is only a software estimate, never position feedback.
enum class TimedGateStop : uint8_t { UNKNOWN, OPEN, CLOSED };
TimedGateStop timed_gate_stop = TimedGateStop::UNKNOWN;


bool servo_armed = false; // retained only for isolated servo_test_* commands
bool cat_inspect_required = false; // latched on an aborted physical motion
bool demo_exited = false; // 0 stops test mode; type start + re-arm to resume.
bool buzzer_armed = false;
bool buzzer_active_high = true;

// V14: DOG alarm is a strictly bounded one-shot FSM. Duplicate 2 commands
// while active are IGNORED, not queued or restarted (no indefinite beep).
bool dog_running = false;
bool buzzer_output_on = false; // last software-commanded physical output state
uint8_t dog_phase = 0;
uint32_t dog_phase_at = 0;
uint32_t dog_started_at = 0;
constexpr uint16_t DOG_STEP_MS[] = {150, 120, 150, 400, 150, 120, 150};
constexpr uint32_t DOG_PATTERN_MS = 1240u; // 2 clusters: (150 on, 120 off, 150 on) + 400 gap + (150 on, 120 off, 150 on)
constexpr uint32_t DOG_HARD_STOP_MS = 1500u; // extra hard ceiling

enum class FeedStage : uint8_t {
  IDLE, WAIT_HX, WAIT_CAT, OPENING, WAIT_WEIGHT, CLOSING, DIAG_OPEN, DIAG_CLOSE, DONE, FAULT
};
FeedStage feed_stage = FeedStage::IDLE;
uint32_t phase_at = 0;
uint32_t started_at = 0;
uint32_t last_hc_ms = 0;
uint32_t last_scale_ms = 0;
uint8_t cat_hits = 0;
float baseline_g = NAN;
float last_delta_g = NAN;
bool close_on_weight = false;

// ============================================================
// FOOD A / FOOD B CONSUMPTION PREFERENCE TRACKING
// Rule:
//   - Target portion ~35g (35g target)
//   - LIKE (Thich an - chuan Mon A): consumed > 50% (>= 18.0g, e.g. remaining ~2g -> consumed ~33g)
//   - DISLIKE (Khong thich an - chuan Mon B): consumed <= 5.0g (e.g. remaining 30..35g -> consumed 0..5g)
// ============================================================
constexpr float PREF_LIKE_MIN_G = 18.0f;
constexpr float PREF_DISLIKE_MAX_G = 5.5f; // 5 g eaten + ~0.5 g load-cell tolerance
char current_food = 'A';
float meal_starting_g = NAN;
float meal_remaining_g = NAN;
float meal_consumed_g = NAN;
const char* meal_preference = "NONE";
bool meal_logged = false;
uint32_t meal_closed_at = 0;
uint32_t meal_stable_since = 0;
float meal_stable_ref_g = NAN;
bool meal_start_locked = false; // true once a stable starting plateau was captured
float meal_plateau_ref_g = NAN;
uint32_t meal_plateau_since = 0;

const char* classifyMeal(float starting_g, float consumed_g) {
  if (!std::isfinite(starting_g) || !std::isfinite(consumed_g) || starting_g <= 0.0f) {
    return "NONE";
  }
  if (consumed_g >= PREF_LIKE_MIN_G || consumed_g > (0.5f * starting_g)) {
    return "LIKE";
  }
  if (consumed_g <= PREF_DISLIKE_MAX_G) {
    return "DISLIKE";
  }
  return "MODERATE";
}

const char* conclusionText(char f, const char* pref) {
  if (!std::strcmp(pref, "LIKE")) {
    return (f == 'B') ? "Meo THICH an Mon B" : "Meo THICH an Mon A";
  }
  if (!std::strcmp(pref, "DISLIKE")) {
    return (f == 'B') ? "Meo KHONG THICH an Mon B" : "Meo KHONG THICH an Mon A";
  }
  if (!std::strcmp(pref, "MODERATE")) {
    return "Meo an muc trung binh";
  }
  return "Dang theo doi luong an";
}

void emitMealPreferenceLog(uint32_t now, const char* trigger) {
  if (!std::isfinite(meal_starting_g) || meal_starting_g <= 0.0f) {
    protocolSerial().print("MEAL EVAL: chua co luot cap thuc an 35g de danh gia.\n");
    return;
  }
  if (!std::isfinite(meal_remaining_g)) meal_remaining_g = meal_starting_g;
  meal_consumed_g = std::max(0.0f, meal_starting_g - meal_remaining_g);
  meal_preference = classifyMeal(meal_starting_g, meal_consumed_g);
  const char* conclusion = conclusionText(current_food, meal_preference);
  protocolSerial().printf(
    "{\"type\":\"meal_preference\","
    "\"ms\":%lu,"
    "\"trigger\":\"%s\","
    "\"food\":\"FOOD_%c\","
    "\"food_code\":\"%c\","
    "\"starting_g\":%.2f,"
    "\"remaining_g\":%.2f,"
    "\"consumed_g\":%.2f,"
    "\"classification\":\"%s\","
    "\"conclusion\":\"%s\"}\n",
    (unsigned long)now,
    trigger,
    current_food,
    current_food,
    double(meal_starting_g),
    double(meal_remaining_g),
    double(meal_consumed_g),
    meal_preference,
    conclusion
  );
  protocolSerial().printf(
    "==> [KET LUAN HANH VI - MON %c]: Cap %.1fg | Con lai %.1fg | Da an %.1fg -> %s (%s)\n",
    current_food,
    double(meal_starting_g),
    double(meal_remaining_g),
    double(meal_consumed_g),
    meal_preference,
    conclusion
  );
}

const char* stateText() {
  switch(feed_stage) {
    case FeedStage::IDLE: return "READY";
    case FeedStage::WAIT_HX: return "CAT WAIT HX";
    case FeedStage::WAIT_CAT: return "WAIT <=30cm";
    case FeedStage::OPENING: return "CAT OPENING";
    case FeedStage::WAIT_WEIGHT: return "WAIT 35g";
    case FeedStage::CLOSING: return "CAT CLOSING";
    case FeedStage::DIAG_OPEN: return "TEST SERVO OPEN";
    case FeedStage::DIAG_CLOSE: return "TEST SERVO CLOSE";
    case FeedStage::DONE: return "MASS OK GATE?";
    default: return "CAT FAULT*";
  }
}

bool busy() {
  return feed_stage == FeedStage::WAIT_HX
    || feed_stage == FeedStage::WAIT_CAT
    || feed_stage == FeedStage::OPENING
    || feed_stage == FeedStage::WAIT_WEIGHT
    || feed_stage == FeedStage::CLOSING
    || feed_stage == FeedStage::DIAG_OPEN
    || feed_stage == FeedStage::DIAG_CLOSE;
}

char ai_species = 'N'; // 'C' = Cat, 'D' = Dog, 'N' = None
uint32_t ai_species_ms = 0;
constexpr uint32_t AI_DISPLAY_HOLD_MS = 4000u;

const char* oledHeaderText(uint32_t now) {
  if (demo_exited) return "EXIT0";
  if (dog_running) return "NHAN DIEN CHO";
  if (ai_species == 'D' && ai_species_ms != 0 && uint32_t(now - ai_species_ms) <= AI_DISPLAY_HOLD_MS) {
    return "NHAN DIEN CHO";
  }
  if (ai_species == 'C' && ai_species_ms != 0 && uint32_t(now - ai_species_ms) <= AI_DISPLAY_HOLD_MS) {
    return "NHAN DIEN MEO";
  }
  return stateText();
}

const char* oledAiLineText(uint32_t now) {
  if (ai_species_ms != 0 && uint32_t(now-ai_species_ms) <= AI_DISPLAY_HOLD_MS) {
    if(ai_species=='C') return "CAT";
    if(ai_species=='D') return "DOG";
  }
  return "FAIL";
}

void buzzerWrite(bool on) {
  // An already-configured pin is ALWAYS driven to its verified inactive level.
  // INPUT/Hi-Z on active-LOW modules can float and sound continuously.
  if (!buzzer_armed) {
    buzzer_output_on = false;
    return;
  }
  digitalWrite(BUZZER_GPIO,
    (on == buzzer_active_high) ? HIGH : LOW);
  buzzer_output_on = on;
}

void buzzerStop() {
  // Single emergency-stop path used by 0/1/stop/end/reconfigure.
  // Clearing the clock *and* pin prevents a previous alarm from resuming.
  dog_running = false;
  dog_phase = 0;
  dog_phase_at = 0;
  dog_started_at = 0;
  buzzerWrite(false);
}

void buzzerMode(bool active_high) {
  buzzerStop();
  buzzer_active_high = active_high;
  // Load the inactive signal before output-mode transition, then re-drive it
  // AFTER pinMode: on ESP32 core 3.x digitalWrite() on a not-yet-OUTPUT pin
  // does not latch the output register, so the pin could come up LOW (= ON
  // for an active-LOW buzzer) and sound continuously after boot.
  digitalWrite(BUZZER_GPIO, active_high ? LOW : HIGH);
  pinMode(BUZZER_GPIO, OUTPUT);
  digitalWrite(BUZZER_GPIO, active_high ? LOW : HIGH);
  buzzer_armed = true;
  buzzer_output_on = false;
  protocolSerial().printf("BUZZER GPIO%d READY active_%s. Press 2 for 3 short + 5s long.\n",
    BUZZER_GPIO, active_high ? "HIGH" : "LOW");
}

void cancel(const char* reason, bool error);
void dogStart(uint32_t now) {
  if (demo_exited) {
    buzzerStop();
    protocolSerial().print("DOG BLOCKED: demo exited via 0. Type start to resume.\n");
    return;
  }
  if (dog_running) {
    // Crucial: do not reset dog_started_at/phase while an alarm is playing.
    // Rapid 2,2,2 can no longer keep a beep on forever.
    protocolSerial().print("DOG BUSY: current 3-short + 5s-long alarm already playing. Repeat 2 ignored.\n");
    return;
  }
  // DOG never starts servo motion. In bench testing, a dog command
  // interrupts any in-progress CAT motion rather than turning the motor.
  // This can leave the real feeder door in an UNKNOWN position.
  if (busy()) {
    const bool may_have_moved = feed_stage == FeedStage::OPENING
        || feed_stage == FeedStage::WAIT_WEIGHT
        || feed_stage == FeedStage::CLOSING
        || feed_stage == FeedStage::DIAG_OPEN
        || feed_stage == FeedStage::DIAG_CLOSE;
    cancel("DOG OVERRIDE - SERVO STOPPED", may_have_moved);
    if (may_have_moved) {
      protocolSerial().print("WARNING: DOG aborted moving gate; position UNKNOWN. Disconnect power and inspect.\n");
    }
  }
  if (!buzzer_armed) {
    // Never guess an alarm module's electrical active level: on an active-LOW
    // module, an incorrect inactive LOW could make the buzzer sound forever.
    buzzerStop();
    protocolSerial().print("DOG BLOCKED V14: configure buzzer_high OR buzzer_low ONCE to match verified hardware.\n");
    return;
  }
  // Before a NEW one-shot, force idle (including clearing any old phase).
  buzzerStop();
  dog_phase = 0;
  dog_phase_at = now;
  dog_started_at = now;
  dog_running = true;
  buzzerWrite(true);
  protocolSerial().printf("DOG START V14: 2 clusters (150ms beep, 120ms gap, 400ms cluster pause, total 1240ms) on GPIO%d; duplicates ignored.\n", BUZZER_GPIO);
}

void dogTick(uint32_t now) {
  if (!dog_running) return;
  // Absolute timing: duplicate commands do not restart, extend, or queue a beep.
  const uint32_t elapsed = uint32_t(now - dog_started_at);
  if (elapsed >= DOG_PATTERN_MS || elapsed >= DOG_HARD_STOP_MS) {
    buzzerStop(); // includes physical inactive GPIO level when polarity configured
    protocolSerial().printf("DOG DONE: 2-cluster 1.24s alarm completed, GPIO%d INACTIVE.\n", BUZZER_GPIO);
    return;
  }
  uint32_t end_at = 0;
  uint8_t phase = 0;
  for (; phase < 7; ++phase) {
    end_at += DOG_STEP_MS[phase];
    if (elapsed < end_at) break;
  }
  // On=phase 0,2,4,6; Off=phase 1,3,5. No writes while already correct.
  const bool want_on = phase < 7 && ((phase % 2u) == 0u);
  if (phase != dog_phase || want_on != buzzer_output_on) {
    dog_phase = phase;
    buzzerWrite(want_on);
  }
}

void neutralMotor() {
  // Match UNO stopServo(): keep transmitting 1500 us after a movement.
  // Detach only if the neutral command fails. Boot still starts detached.
  if (pwm.attached() && !pwm.write(SERVO_NEUTRAL_US)) pwm.off();
}

void cancel(const char* reason, bool error) {
  // Mark movement as unverified if an interrupted cycle might have moved a gate.
  const bool may_have_moved = feed_stage == FeedStage::OPENING
      || feed_stage == FeedStage::WAIT_WEIGHT
      || feed_stage == FeedStage::CLOSING
      || feed_stage == FeedStage::DIAG_OPEN
      || feed_stage == FeedStage::DIAG_CLOSE;
  neutralMotor();
  if (busy()) protocolSerial().printf("CAT STOP: %s; door position UNKNOWN.\n", reason);
  if (may_have_moved) {
    cat_inspect_required = true;
    timed_gate_stop = TimedGateStop::UNKNOWN;
  }
  feed_stage = error ? FeedStage::FAULT : FeedStage::IDLE;
  servo_armed = false;
  cat_hits = 0;
}

bool startOpen(uint32_t now) {
  if (cat_inspect_required || timed_gate_stop == TimedGateStop::OPEN) {
    protocolSerial().print("SERVO OPEN BLOCKED: already timed-open or interrupted; inspect and confirm CLOSED with inspect_ok.\n");
    cat_inspect_required = true;
    feed_stage = FeedStage::FAULT;
    return false;
  }
  timed_gate_stop = TimedGateStop::UNKNOWN;
  if ((!pwm.attached() && !pwm.start(SERVO_NEUTRAL_US)) || !pwm.write(SERVO_OPEN_US)) {
    cat_inspect_required = true;
    cancel("LEDC SERVO START FAILED", true);
    return false;
  }
  physical_closed_verified = false;
  feed_stage = FeedStage::OPENING;
  phase_at = now;
  protocolSerial().printf("SERVO OPEN %u ms, PWM %u us.\n",
     (unsigned)open_ms, (unsigned)SERVO_OPEN_US);
  return true;
}

bool manual_feed_active = false;
uint32_t button_request_count = 0;
uint32_t button_last_press_ms = 0;

void startClose(uint32_t now, bool by_weight) {
  // Duplicate close requests must not restart the configured closing timer.
  if (feed_stage == FeedStage::CLOSING) return;
  if (timed_gate_stop == TimedGateStop::CLOSED) {
    protocolSerial().print("SERVO CLOSE IGNORED: last full stroke already timed-closed.\n");
    return;
  }
  timed_gate_stop = TimedGateStop::UNKNOWN;
  manual_feed_active = false;
  close_on_weight = by_weight;
  // If V-153-1C25 limit switch on GPIO47 is already pressed, stop immediately without driving close
  if (USE_CLOSE_LIMIT_SWITCH && (limit_closed || digitalRead(PIN_CLOSE_LIMIT) == LOW)) {
    neutralMotor();
    physical_closed_verified = true;
    timed_gate_stop = TimedGateStop::CLOSED;
    cat_inspect_required = false;
    if (close_on_weight) {
      meal_starting_g = last_delta_g;
      meal_remaining_g = last_delta_g;
      meal_consumed_g = 0.0f;
      meal_preference = "WAITING";
      meal_logged = false;
      meal_start_locked = false;
      meal_plateau_ref_g = NAN;
      meal_plateau_since = 0;
      meal_closed_at = now;
      meal_stable_since = 0;
      meal_stable_ref_g = NAN;
    }
    feed_stage = close_on_weight ? FeedStage::DONE : FeedStage::IDLE;
    protocolSerial().print("CAT CLOSE: limit switch GPIO47 already CLOSED -> servo stopped immediately.\n");
    return;
  }
  if (!pwm.attached() && !pwm.start(SERVO_NEUTRAL_US)) {
    cancel("LEDC SERVO CLOSE ATTACH FAILED", true);
    return;
  }
  if (!pwm.write(SERVO_CLOSE_US)) {
    cancel("LEDC SERVO CLOSE FAILED", true);
    return;
  }
  feed_stage = FeedStage::CLOSING;
  phase_at = now;
  protocolSerial().printf("CAT CLOSING NOW: delta=%.2fg, reason=%s -> TIMED rotation for %ums; physical closure not measured.\n",
    double(last_delta_g), by_weight ? "WEIGHT_REACHED" : "TIMEOUT_FAILSAFE",
    (unsigned)close_ms);
}

// A command can arrive between HX median-3 updates. Wait for a fresh,
// healthy gram sample instead of rejecting a valid operator request.
// This stage NEVER energizes the servo; an already-loaded scale blocks motion.
// The original FC1 controller rejects NEGATIVE gram readings, causing
// healthy:false even with a calibrated HX711 around zero (-0.5 g in log).
// The bench demo instead uses recent, signed, median-of-three gram samples.
// This DOES NOT relax the production FC1 safety controller.
bool benchScaleSample(uint32_t now, float& grams, uint32_t& sample_ms) {
  if (!hx.calibration.valid() || !hx.signed_grams.valid
      || !hx.median_raw.valid || !hx.raw.valid
      || hx.status.health == m4::Health::NOT_CONNECTED
      || hx.status.health == m4::Health::FAULT
      || !std::isfinite(hx.signed_grams.value))
    return false;
  sample_ms = hx.signed_grams.sampled_at_ms;
  if (sample_ms == 0 || uint32_t(now - sample_ms) > 1200u
      || hx.median_raw.sampled_at_ms != sample_ms) return false;
  grams = hx.signed_grams.value;
  return true;
}
bool acceptableScaleSample(const Sample& s) {
  float grams = NAN;
  uint32_t t = 0;
  return benchScaleSample(s.now_ms, grams, t);
}

void beginManualFeed(uint32_t now, const char* source) {
  if (feed_stage == FeedStage::DIAG_OPEN || feed_stage == FeedStage::DIAG_CLOSE
      || bench_cal != BenchCal::Idle) {
    protocolSerial().print("MANUAL FEED BLOCKED: servo adjustment or calibration in progress.\n");
    return;
  }
  // A button/Web request must not erase the lock after an interrupted servo run.
  if (cat_inspect_required) {
    protocolSerial().print("MANUAL FEED BLOCKED: inspect the gate, align CLOSED, then inspect_ok.\n");
    return;
  }
  buzzerStop();
  demo_exited = false;
  if (feed_stage == FeedStage::WAIT_WEIGHT) {
    protocolSerial().printf("MANUAL FEED (%s): closing gate now.\n", source);
    // A manual early close is not proof that a measured serving was reached.
    startClose(now, last_delta_g >= CLOSE_AT_G && last_delta_g <= MAX_NORMAL_G);
    return;
  }
  if (feed_stage == FeedStage::OPENING || feed_stage == FeedStage::CLOSING) {
    return;
  }
  float g = NAN;
  uint32_t sample_ms = 0;
  if (!benchScaleSample(now, g, sample_ms)) {
    protocolSerial().print("MANUAL FEED BLOCKED: HX711 needs a fresh calibrated measurement; no 0g fallback.\n");
    return;
  }
  baseline_g = g;
  last_delta_g = 0.0f;
  cat_hits = 3;
  last_scale_ms = 0;
  manual_feed_active = true;
  started_at = phase_at = now;
  protocolSerial().printf("MANUAL FEED (%s): baseline=%.2fg -> SERVO OPEN NOW!\n",
    source, double(baseline_g));
  startOpen(now);
}

bool beginCatWithScale(const Sample& s) {
  float grams = NAN;
  uint32_t reading_at = 0;
  if (!benchScaleSample(s.now_ms, grams, reading_at)) return false;
  if (std::fabs(grams) > 2.0f) {
    protocolSerial().printf(
      "CAT BLOCKED: remove existing weight %.2fg. Start with EMPTY bowl (near 0g), then place 35g AFTER opening.\n",
      double(grams));
    feed_stage = FeedStage::IDLE;
    return false;
  }
  baseline_g = grams;
  last_delta_g = 0;
  cat_hits = 0;
  last_hc_ms = 0;
  last_scale_ms = 0;
  phase_at = started_at = s.now_ms;
  feed_stage = FeedStage::WAIT_CAT;
  protocolSerial().print("CAT REQUEST: E1 2..30cm, two fresh readings, prequalified window.\n");
  if(cat_near.ready(s.now_ms)) startOpen(s.now_ms);
  return true;
}

void beginCat(const Sample& s) {
  // New cycle: drop the previous meal's conclusion so telemetry/OLED never
  // show a stale LIKE/DISLIKE while the new meal is still being dispensed.
  meal_preference = "NONE";
  meal_starting_g = NAN;
  meal_remaining_g = NAN;
  meal_consumed_g = NAN;
  meal_start_locked = false;
  // CAT silences any DOG tone BEFORE checking HC1/HX711.
  // If DOG interrupted moving servo, next CAT stays locked until inspect_ok.
  // The user may send 2 -> 1 -> 2 rapidly. CAT ALWAYS silences any DOG tone,
  // BEFORE checking HX711, FC1 fault, sensor, or door-inspection gates.
  const bool was_dog = dog_running || buzzer_output_on;
  buzzerStop();
  if (was_dog)
    protocolSerial().print("CAT 1: previous DOG alarm CANCELLED, GPIO1 OFF.\n");
  if (demo_exited) {
    protocolSerial().print("CAT BLOCKED: demo exited via 0. Type start to resume.\n");
    return;
  }
  if (busy()) {
    protocolSerial().print("CAT BUSY: send 'stop' to abort.\n");
    return;
  }
  if (!sensors_enabled) {
    protocolSerial().print("CAT: sensor not enabled; trying to initialize E1/E2/D1/D2...\n");
    if (!beginAllSensors()) {
      protocolSerial().print("CAT BLOCKED: SENSOR_INIT_FAILED; verify ECHO level <=3.3V, wiring 12/13, 16/17, 14/15, 18/19.\n");
      return;
    }
    protocolSerial().print("CAT: ultrasonic/PIR sensors initialized, waiting first HC1 measurements.\n");
  }
  if (cat_inspect_required) {
    protocolSerial().print("CAT LOCKED: last motor cycle interrupted; physically inspect the disconnected mechanism, then type inspect_ok.\n");
    return;
  }
  // V14 manual demo has exclusive motor ownership. Legacy FC1 is not ticked
  // and must not gate this independent bench test based on persisted history.
  // Motion remains gated by HX zero/freshness, cat distance, and inspect_lock.
  if (bench_cal != BenchCal::Idle || pwm.moving()) {
    protocolSerial().print("CAT BLOCKED: CALIBRATION_BUSY_OR_PWM_ALREADY_ATTACHED.\n");
    return;
  }
  // Prior DOG alarm is already cancelled at the start of beginCat.
  if (acceptableScaleSample(s)) {
    beginCatWithScale(s);
    return;
  }
  feed_stage = FeedStage::WAIT_HX;
  phase_at = started_at = s.now_ms;
  protocolSerial().print("CAT WAIT HX711: no fresh valid gram sample right now. Waiting up to 25s, SERVO OFF. Keep bowl EMPTY.\n");
}

// UNO-style nonblocking manual movement, sharing the feeder PWM owner.
bool manualServoMove(bool opening, uint32_t duration, uint32_t now) {
  if (cat_inspect_required) {
    protocolSerial().print("SERVO BLOCKED: interrupted run; align CLOSED and confirm inspect_ok.\n");
    return false;
  }
  const auto target = opening ? TimedGateStop::OPEN : TimedGateStop::CLOSED;
  if (timed_gate_stop == target) {
    protocolSerial().print("SERVO IGNORED: same full stroke already completed; no extra rotation.\n");
    return false;
  }
  if (busy() || pwm.moving() || dog_running || bench_cal != BenchCal::Idle) {
    protocolSerial().print("SERVO BUSY: use 0 / stop to stop first.\n");
    return false;
  }
  if (!duration || duration > MAX_SERVO_ACTIVE_MS) return false;
  timed_gate_stop = TimedGateStop::UNKNOWN;
  if ((!pwm.attached() && !pwm.start(SERVO_NEUTRAL_US))
      || !pwm.write(opening ? SERVO_OPEN_US : SERVO_CLOSE_US)) {
    neutralMotor();
    cat_inspect_required = true;
    feed_stage = FeedStage::FAULT;
    protocolSerial().print("SERVO MANUAL OUTPUT FAILED; inspection required.\n");
    return false;
  }
  // Keep demo_exited / inspection lock unchanged: manual adjustment does not
  // authorize automatic CAT dispensing or establish a measured gate position.
  physical_closed_verified = false;
  servo_move_for_ms = duration;
  feed_stage = opening ? FeedStage::DIAG_OPEN : FeedStage::DIAG_CLOSE;
  phase_at = started_at = now;
  servo_armed = false;
  protocolSerial().printf("SERVO %s: GPIO6 pulse=%uus time=%lums; stop=1500us.\n",
    opening ? "OPEN RIGHT" : "CLOSE LEFT",
    (unsigned)(opening ? SERVO_OPEN_US : SERVO_CLOSE_US), (unsigned long)duration);
  return true;
}

// Retain existing armed diagnostic aliases for compatibility.
void diagServo(bool opening, uint32_t now) {
  if (!servo_armed || cat_inspect_required) {
    protocolSerial().print("SERVO TEST BLOCKED: servo_arm / inspect_ok required.\n");
    return;
  }
  manualServoMove(opening, opening ? open_ms : close_ms, now);
}

void tick(const Sample& s, uint32_t now) {
  dogTick(now);
  if (feed_stage == FeedStage::DONE) {
    float grams = NAN;
    uint32_t sample_ms = 0;
    if (benchScaleSample(now, grams, sample_ms) && std::isfinite(baseline_g)) {
      const float rem = std::max(0.0f, grams - baseline_g);
      // Starting mass = FIRST STABLE PLATEAU (>=20 g, +-0.8 g for >=4 s) after
      // the gate closes. A single transient peak (hand placing/bumping weights)
      // is NOT accepted as the starting mass. Until it locks: WAITING.
      if (!meal_start_locked) {
        if (!std::isfinite(meal_plateau_ref_g) || std::fabs(rem - meal_plateau_ref_g) > 0.8f) {
          meal_plateau_ref_g = rem;
          meal_plateau_since = now;
        } else if (rem >= 20.0f && uint32_t(now - meal_plateau_since) >= 4000u) {
          meal_starting_g = rem;
          meal_start_locked = true;
        }
      }
      meal_remaining_g = rem;
      meal_consumed_g = meal_start_locked ? std::max(0.0f, meal_starting_g - meal_remaining_g) : 0.0f;
      meal_preference = meal_start_locked
        ? classifyMeal(meal_starting_g, meal_consumed_g) : "WAITING";

      // Auto-emit meal_preference log once remaining weight settles after eating
      if (!meal_logged && meal_start_locked && uint32_t(now - meal_closed_at) >= 3500u) {
        if (!std::isfinite(meal_stable_ref_g) || std::fabs(rem - meal_stable_ref_g) > 0.5f) {
          meal_stable_ref_g = rem;
          meal_stable_since = now;
        } else if (meal_consumed_g >= 2.0f && uint32_t(now - meal_stable_since) >= 3000u) {
          meal_logged = true;
          emitMealPreferenceLog(now, "AUTO_SETTLED");
        }
      }
    }
    return;
  }
  if (feed_stage == FeedStage::IDLE || feed_stage == FeedStage::FAULT) return;

  if (feed_stage == FeedStage::DIAG_OPEN || feed_stage == FeedStage::DIAG_CLOSE) {
    const bool hit_close_limit = USE_CLOSE_LIMIT_SWITCH && (feed_stage == FeedStage::DIAG_CLOSE) && (limit_closed || digitalRead(PIN_CLOSE_LIMIT) == LOW);
    const uint32_t duration = servo_move_for_ms;
    if (hit_close_limit || uint32_t(now - phase_at) >= duration) {
      timed_gate_stop = feed_stage == FeedStage::DIAG_OPEN ? TimedGateStop::OPEN : TimedGateStop::CLOSED;
      neutralMotor();
      servo_armed = false;
      feed_stage = FeedStage::IDLE;
      if (hit_close_limit) {
        physical_closed_verified = true;
        protocolSerial().print("SERVO TEST CLOSE STOPPED IMMEDIATELY BY LIMIT SWITCH GPIO47!\n");
      } else {
        protocolSerial().print("SERVO TIMED TEST FINISHED; physical position not measured. Re-arm for another isolated test.\n");
      }
    }
    return;
  }
  if (feed_stage == FeedStage::WAIT_HX) {
    if (uint32_t(now - started_at) > HX_WAIT_TIMEOUT_MS) {
      cancel("HX711 NO HEALTHY GRAM WITHIN 25S; CHECK WEIGHT/SENSOR", true);
      return;
    }
    if (acceptableScaleSample(s)) beginCatWithScale(s);
    return;
  }
  if (feed_stage != FeedStage::CLOSING && uint32_t(now - started_at) > 45000u) {
    if (feed_stage == FeedStage::WAIT_WEIGHT || feed_stage == FeedStage::OPENING) {
      startClose(now, false);
    } else cancel("GLOBAL TIMEOUT", true);
    return;
  }
  if (feed_stage == FeedStage::WAIT_CAT) {
    if (uint32_t(now - phase_at) >= CAT_WAIT_TIMEOUT_MS) {
      cancel("E1 NO TWO FRESH NEAR READINGS", true);
      return;
    }
    if(cat_near.ready(now)) startOpen(now);
    return;
  }
  if (feed_stage == FeedStage::OPENING) {
    if (uint32_t(now - phase_at) >= open_ms) {
      if (!pwm.write(SERVO_NEUTRAL_US)) {
        cancel("LEDC NEUTRAL FAILED", true);
        return;
      }
      timed_gate_stop = TimedGateStop::OPEN;
      feed_stage = FeedStage::WAIT_WEIGHT;
      phase_at = now;
      last_scale_ms = 0;
      protocolSerial().print("SERVO AT TIMED-OPEN. PLACE 35g ON SCALE NOW. Max 25s.\n");
    }
    return;
  }
  if (feed_stage == FeedStage::WAIT_WEIGHT) {
    float grams = NAN;
    uint32_t sample_ms = 0;
    const bool scale_ok = benchScaleSample(now, grams, sample_ms);
    if (scale_ok && sample_ms != last_scale_ms) {
      last_scale_ms = sample_ms;
      last_delta_g = grams - baseline_g;
      if (last_delta_g >= CLOSE_AT_G) {
        if (last_delta_g > MAX_NORMAL_G)
          protocolSerial().print("WARNING: OVER 40g DETECTED; closing immediately.\n");
        startClose(now, last_delta_g <= MAX_NORMAL_G);
        return;
      }
    }
    if (manual_feed_active && uint32_t(now - phase_at) >= 4000u) {
      protocolSerial().print("MANUAL FEED MASS NOT REACHED WITHIN 4S -> BOUNDED CLOSE, RESULT NOT VERIFIED.\n");
      startClose(now, false);
      return;
    }
    // Fail-close promptly if the real load-cell data disappears mid-feed;
    // never leave the gate timed-open for 25s without valid measurements.
    if (uint32_t(now - phase_at) >= 1800u
        && (!scale_ok || (last_scale_ms && uint32_t(now-last_scale_ms) > 1500u))) {
      protocolSerial().print("CAT HX LOST AFTER OPEN: bounded reverse, flag inspection required.\n");
      startClose(now, false);
      return;
    }
    if (uint32_t(now - phase_at) >= WEIGHT_WAIT_TIMEOUT_MS) {
      protocolSerial().print("CAT WEIGHT TIMEOUT - ATTEMPT BOUNDED REVERSE.\n");
      startClose(now, false);
    }
    return;
  }
  if (feed_stage == FeedStage::CLOSING) {
    const bool hit_limit = USE_CLOSE_LIMIT_SWITCH && (limit_closed || (digitalRead(PIN_CLOSE_LIMIT) == LOW));
    const uint32_t close_elapsed = uint32_t(now - phase_at);
    static uint32_t last_close_debug = 0;
    if (uint32_t(now - last_close_debug) >= 300u) {
      last_close_debug = now;
      protocolSerial().printf(
        "CLOSING TIMED: %lums / %ums | limit switch DISABLED\n",
        (unsigned long)close_elapsed, (unsigned)close_ms);
    }
    if (hit_limit || close_elapsed >= close_ms) {
      neutralMotor();
      timed_gate_stop = TimedGateStop::CLOSED;
      physical_closed_verified = hit_limit;
      // In timed mode a FULL close stroke restores the relative CLOSED estimate.
      // An insufficient dose remains a feed FAULT below; it is not an interrupted servo.
      cat_inspect_required = USE_CLOSE_LIMIT_SWITCH && !hit_limit;
      if (close_on_weight) {
        meal_starting_g = last_delta_g;
        meal_remaining_g = last_delta_g;
        meal_consumed_g = 0.0f;
        meal_preference = "WAITING";
        meal_logged = false;
        meal_start_locked = false;
        meal_plateau_ref_g = NAN;
        meal_plateau_since = 0;
        meal_closed_at = now;
        meal_stable_since = 0;
        meal_stable_ref_g = NAN;
      }
      feed_stage = close_on_weight ? FeedStage::DONE : (hit_limit ? FeedStage::IDLE : FeedStage::FAULT);
      if (hit_limit) {
        protocolSerial().printf(
          "CAT SERVO STOPPED BY LIMIT SWITCH GPIO47 after %lums (MON %c, delta %.2fg): EXACT CLOSED POSITION VERIFIED!\n",
          (unsigned long)close_elapsed, current_food, double(last_delta_g));
      } else if (!USE_CLOSE_LIMIT_SWITCH) {
        protocolSerial().printf(
          "CAT SERVO STOPPED AFTER TIMED CLOSE %ums (delta %.2fg); physical closure not measured.\n",
          (unsigned)close_ms, double(last_delta_g));
      } else {
        protocolSerial().printf(
          "CAT SERVO STOPPED BY SAFETY TIMEOUT %ums (GPIO47 limit switch not hit, MON %c, delta %.2fg).\n",
          (unsigned)close_ms, current_food, double(last_delta_g));
      }
    }
  }
}

bool setMotionTime(const char* text, bool opening) {
  char* end = nullptr;
  const long value = std::strtol(text, &end, 10);
  if (*text == 0 || *end != 0 || value < 100 || value > MAX_SERVO_ACTIVE_MS
      || busy() || pwm.moving()) return false;
  if (opening) open_ms = (uint16_t)value;
  else close_ms = (uint16_t)value;
  return true;
}

} // namespace bench_v8

// Scheduled commands are idempotent attempts, independent of cat proximity.
namespace scheduled_feed_v1 {
struct History { uint32_t magic; uint8_t next; char ids[32][65]; };
History history{};
Preferences prefs;
bool loaded=false, storage_ok=false;
char active[65]{};
bool validId(const char* id) {
  size_t n=std::strlen(id);
  if (!n || n>64) return false;
  for(size_t i=0;i<n;++i) if(!((id[i]>='a'&&id[i]<='z')||(id[i]>='A'&&id[i]<='Z')||(id[i]>='0'&&id[i]<='9')||id[i]=='_'||id[i]=='-')) return false;
  return true;
}
bool load() {
  if(loaded) return storage_ok;
  loaded=true;
  if(!prefs.begin("fc_sched_v1",false)) return false;
  size_t n=prefs.getBytesLength("history");
  if(n==0) { history.magic=0x53434831; history.next=0; storage_ok=true; return true; }
  if(n!=sizeof(history)||prefs.getBytes("history",&history,sizeof(history))!=sizeof(history)
      ||history.magic!=0x53434831||history.next>=32) return false;
  for(auto& id:history.ids) if(std::memchr(id,0,sizeof(id))==nullptr || (id[0]&&!validId(id))) return false;
  storage_ok=true;return true;
}
void ack(const char* id,const char* status,const char* reason) {
  protocolSerial().printf("{\"type\":\"scheduled_ack\",\"request_id\":\"%s\",\"status\":\"%s\",\"reason\":\"%s\"}\n",id,status,reason);
}
bool command(const char* line,uint32_t now) {
  if(std::strncmp(line,"feed_once ",10)) return false;
  const char* id=line+10;
  if(!validId(id)) { ack("invalid","REJECTED","INVALID_ID");return true; }
  if(!load()) { ack(id,"REJECTED","STORAGE_UNAVAILABLE");return true; }
  for(auto& old:history.ids) if(!std::strcmp(old,id)) { ack(id,"DUPLICATE","ATTEMPT_ALREADY_RECORDED");return true; }
  if(bench_v8::busy()||pwm.moving()||bench_cal!=BenchCal::Idle||bench_v8::dog_running||bench_v8::demo_exited) {
    ack(id,"BUSY","WAIT_DEVICE_READY");return true;
  }
  if(bench_v8::cat_inspect_required||bench_v8::timed_gate_stop==bench_v8::TimedGateStop::OPEN) {
    ack(id,"REJECTED","INSPECTION_REQUIRED");return true;
  }
  float g;uint32_t stamp;
  if(!bench_v8::benchScaleSample(now,g,stamp)) { ack(id,"BUSY","HX_NOT_READY");return true; }
  History next=history;
  std::strncpy(next.ids[next.next],id,64);next.ids[next.next][64]=0;next.next=(next.next+1)%32;
  // Record before motion: an interrupted attempt is never silently repeated.
  if(prefs.putBytes("history",&next,sizeof(next))!=sizeof(next)) { ack(id,"REJECTED","STORAGE_WRITE_FAILED");return true; }
  history=next;
  bench_v8::beginManualFeed(now,"SCHEDULED");
  if(bench_v8::feed_stage!=bench_v8::FeedStage::OPENING) { ack(id,"REJECTED","START_FAILED");return true; }
  bench_v8::manual_feed_active=false; // full weight-controlled timeout, not the4s button bench timeout
  std::strncpy(active,id,64);active[64]=0;
  ack(id,"ACCEPTED","MEASURED_35G_ATTEMPT_STARTED");return true;
}
void tick() {
  if(!active[0]||bench_v8::busy()) return;
  const bool ok=bench_v8::feed_stage==bench_v8::FeedStage::DONE;
  protocolSerial().printf("{\"type\":\"scheduled_result\",\"request_id\":\"%s\",\"status\":\"%s\",\"measured_at_close_g\":",
      active,ok?"WEIGHT_REACHED":"FAILED");
  if(std::isfinite(bench_v8::last_delta_g)) protocolSerial().printf("%.3f",double(bench_v8::last_delta_g));
  else protocolSerial().print("null");
  protocolSerial().print("}\n");active[0]=0;
}
}

// Candidate feature: disabled until backup power has been physically commissioned.
namespace power_backup {
using fallback_policy::Gate;using fallback_policy::Inputs;using fallback_policy::Action;
Preferences prefs;
Gate gate;
bool storage_ok=false,enabled=false,seen_host=false,active=false;
uint32_t boot_at=0,host_at=0;
bool offline(uint32_t now){return uint32_t(now-boot_at)>=30000&&(!seen_host||uint32_t(now-host_at)>15000);}
void begin(uint32_t now){
  boot_at=now;
  storage_ok=prefs.begin("fc_backup_v1",false);
  if(!storage_ok)return;
  enabled=prefs.getBool("enabled",false);
  uint8_t state=prefs.getUChar("state",0);
  if(state>2){storage_ok=false;return;}
  if(state){gate.consumed(now);}
  if(state==1){bench_v8::cat_inspect_required=true;}
}
bool save(uint8_t state){
  if(!storage_ok||prefs.putUChar("state",state)!=1){storage_ok=false;return false;}
  return true;
}
void inspected(uint32_t now){
  if(storage_ok&&prefs.getUChar("state",0)==1&&save(2))gate.consumed(now);
}
bool command(const char* line,uint32_t now){
  if(!std::strcmp(line,"jetson_ping")){seen_host=true;host_at=now;return true;}
  if(std::strcmp(line,"backup_on")&&std::strcmp(line,"backup_off"))return false;
  bool requested=!std::strcmp(line,"backup_on");
  if(!storage_ok||prefs.putBool("enabled",requested)!=1){storage_ok=false;protocolSerial().print("BACKUP STORAGE FAULT\n");return true;}
  enabled=requested;protocolSerial().print(enabled?"BACKUP ENABLED\n":"BACKUP DISABLED\n");return true;
}
void tick(uint32_t now){
  if(active&&!bench_v8::busy()){
    active=false;
    if(bench_v8::timed_gate_stop==bench_v8::TimedGateStop::CLOSED&&!bench_v8::cat_inspect_required)save(2);
    // Interrupted or unverified motion stays marked inflight across reboot.
  }
  if(!enabled||!storage_ok||active)return;
  float g=NAN;uint32_t sample=0;
  bool scale=bench_v8::benchScaleSample(now,g,sample);
  bool allowed=!bench_v8::busy()&&!pwm.moving()&&!bench_v8::demo_exited
    &&!bench_v8::cat_inspect_required&&!bench_v8::dog_running&&bench_cal==BenchCal::Idle
    &&bench_v8::timed_gate_stop!=bench_v8::TimedGateStop::OPEN;
  Inputs input{now,hc.raw.sampled_at_ms,offline(now),allowed,
    sensors_enabled&&hc.raw.valid,motion_active&&digitalRead(PIN_PIR)==HIGH,
    scale&&std::fabs(g)<=2.0f,hc.raw.value};
  Action action=gate.step(input);
  if(action==Action::REARM){if(save(0)){gate.used=false;gate.hits=0;}return;}
  if(action!=Action::ATTEMPT||!save(1))return;
  gate.consumed(now);
  bench_v8::beginManualFeed(now,"POWER_BACKUP_E1_PIR");
  if(bench_v8::feed_stage==bench_v8::FeedStage::OPENING){
    bench_v8::manual_feed_active=false;active=true;
    protocolSerial().print("BACKUP: E1<=20cm x3 + PIR, measured35g cycle\n");
  } else bench_v8::cat_inspect_required=true;
}
}

// Display-only view. No actuator commands or changes to control state.
namespace product_oled {
struct View {
  const char* ai;
  bool scale_ok, paused, inspect, dog, calibrating;
  float grams, delta;
  bench_v8::FeedStage stage;
  float cm[4];
};

void text(int x, int y, const char* label, uint8_t size=1,
          uint16_t color=SSD1306_WHITE) {
  oled.setTextSize(size);
  oled.setTextColor(color);
  oled.setCursor(x,y);
  oled.print(label);
}

void paw() {
  oled.fillCircle(3,3,1,SSD1306_WHITE);
  oled.fillCircle(7,1,1,SSD1306_WHITE);
  oled.fillCircle(11,3,1,SSD1306_WHITE);
  oled.fillCircle(1,6,1,SSD1306_WHITE);
  oled.fillRoundRect(4,6,7,6,3,SSD1306_WHITE);
}

void header(const View& v, bool details) {
  if(details) text(0,3,"CAM BIEN");
  else { paw(); text(18,3,"FOR CAT"); }
  const bool backup=power_backup::enabled&&power_backup::storage_ok&&power_backup::offline(millis());
  const bool detected=!backup&&(!std::strcmp(v.ai,"CAT")||!std::strcmp(v.ai,"DOG"));
  char label[12];
  if(backup) std::strcpy(label,"BACKUP");
  else std::snprintf(label,sizeof(label),"AI %s",v.ai);
  if(detected) oled.fillRoundRect(82,0,46,13,3,SSD1306_WHITE);
  else oled.drawRoundRect(82,0,46,13,3,SSD1306_WHITE);
  text(82+(46-int(std::strlen(label))*6)/2,3,label,1,
       detected?SSD1306_BLACK:SSD1306_WHITE);
  oled.drawFastHLine(0,15,128,SSD1306_WHITE);
}

const char* status(const View& v, bool& warning) {
  warning=false;
  if(v.paused) return "TAM DUNG";
  if(v.inspect) { warning=true; return "KIEM TRA CUA"; }
  if(v.calibrating) return "DANG HIEU CHUAN";
  if(v.dog) { warning=true; return "CANH BAO CHO"; }
  using Stage=bench_v8::FeedStage;
  switch(v.stage) {
    case Stage::OPENING: return "DANG MO CUA";
    case Stage::WAIT_WEIGHT: return "DANG CAP 35 G";
    case Stage::CLOSING: return "DANG DONG CUA";
    case Stage::DIAG_OPEN:
    case Stage::DIAG_CLOSE: return "DANG THU CUA";
    default: break;
  }
  if(!v.scale_ok) { warning=true; return "KIEM TRA CAN"; }
  switch(v.stage) {
    case Stage::WAIT_HX: return "DANG DOC CAN";
    case Stage::WAIT_CAT: return "CHO MEO DEN GAN";
    case Stage::DONE: return "DA CAP THUC AN";
    case Stage::FAULT:
      warning=true;
      if(std::isfinite(v.delta))
        return v.delta<bench_v8::CLOSE_AT_G?"LAN CAP CHUA DU":"LUONG AN CAO";
      return "CAN KIEM TRA";
    default: return "SAN SANG";
  }
}

bool showDetails(const View& v, uint32_t now) {
  using Stage=bench_v8::FeedStage;
  const bool idle=v.stage==Stage::IDLE||v.stage==Stage::DONE||v.stage==Stage::FAULT;
  // Calm9s home /3s detail cycle; never leave the home page during an action.
  return idle&&!v.paused&&!v.inspect&&!v.dog&&!v.calibrating&&v.scale_ok
      &&!std::strcmp(v.ai,"FAIL")&&(now%12000u)>=9000u;
}

void home(const View& v) {
  char amount[20];
  if(!v.scale_ok||!std::isfinite(v.grams)) std::strcpy(amount,"--.-");
  else if(std::fabs(v.grams)>=100000.0f) std::strcpy(amount,"QUA TAI");
  else std::snprintf(amount,sizeof(amount),std::fabs(v.grams)<1000?"%.1f":"%.0f",
                     double(v.grams==0.0f?0.0f:v.grams));
  const int size=std::strlen(amount)<=5?3:2;
  const int width=int(std::strlen(amount))*6*size;
  const bool unit=std::strcmp(amount,"QUA TAI")!=0;
  const int x=(128-width-(unit?10:0))/2;
  text(x,size==3?22:26,amount,size);
  if(unit) text(x+width+4,37,"g");
  using Stage=bench_v8::FeedStage;
  if((v.stage==Stage::OPENING||v.stage==Stage::WAIT_WEIGHT||v.stage==Stage::CLOSING)
      &&std::isfinite(v.delta)) {
    float ratio=v.delta/bench_v8::CLOSE_AT_G;
    if(ratio<0) ratio=0;
    if(ratio>1) ratio=1;
    oled.drawFastHLine(0,48,128,SSD1306_WHITE);
    const int fill=int(ratio*126.0f);
    if(fill>0) oled.fillRect(1,47,fill,3,SSD1306_WHITE);
  }
  bool warning=false;
  const char* label=status(v,warning);
  oled.fillRoundRect(0,52,128,12,3,SSD1306_WHITE);
  if(warning) {
    oled.drawTriangle(4,61,8,54,12,61,SSD1306_BLACK);
    oled.drawFastVLine(8,57,2,SSD1306_BLACK);
    oled.drawPixel(8,60,SSD1306_BLACK);
  } else if(v.paused) {
    oled.fillRect(5,55,2,6,SSD1306_BLACK);
    oled.fillRect(9,55,2,6,SSD1306_BLACK);
  } else {
    oled.fillCircle(8,58,2,SSD1306_BLACK);
  }
  text(16+(112-int(std::strlen(label))*6)/2,55,label,1,SSD1306_BLACK);
}

void details(const View& v) {
  const char* names[]={"E1 MEO","E2 THUC AN","D1 CHEN","D2 BINH"};
  for(unsigned i=0;i<4;++i) {
    const int y=20+int(i)*11;
    text(0,y,names[i]);
    char value[16];
    if(std::isfinite(v.cm[i])&&v.cm[i]>=0&&v.cm[i]<=999.9f)
      std::snprintf(value,sizeof(value),"%.1fcm",double(v.cm[i]));
    else std::strcpy(value,"-- cm");
    text(128-int(std::strlen(value))*6,y,value);
  }
}

void render(const View& v, uint32_t now) {
  oled.clearDisplay();
  oled.setFont(nullptr);
  oled.setTextWrap(false);
  const bool detail=showDetails(v,now);
  header(v,detail);
  if(detail) details(v); else home(v);
  oled.display();
}

void boot() {
  oled.clearDisplay();
  oled.setFont(nullptr);
  oled.setTextWrap(false);
  text(22,20,"FOR CAT",2);
  text(22,45,"DANG KHOI DONG");
  oled.display();
}
}

void updateOLED(uint32_t now) {
  if(!oled_ok||uint32_t(now-last_oled_ms)<400) return;
  last_oled_ms=now;
  float grams=NAN;uint32_t stamp=0;
  const bool fresh=bench_v8::benchScaleSample(now,grams,stamp);
  product_oled::View view{};
  view.ai=bench_v8::oledAiLineText(now);
  view.scale_ok=fresh&&hx.display_grams.valid&&std::isfinite(hx.display_grams.value);
  view.grams=view.scale_ok?hx.display_grams.value:NAN;
  view.delta=bench_v8::last_delta_g;
  view.stage=bench_v8::feed_stage;
  view.paused=bench_v8::demo_exited;
  view.inspect=bench_v8::cat_inspect_required;
  view.dog=bench_v8::dog_running;
  view.calibrating=bench_cal!=BenchCal::Idle;
  view.cm[0]=recentCm(hc,now);view.cm[1]=recentCm(hc2,now);
  view.cm[2]=recentCm(bowl_d1,now);view.cm[3]=recentCm(tank_d2,now);
  product_oled::render(view,now);
}

void printSensorSummary(uint32_t now) {
  protocolSerial().printf("SENSORS enabled=%d OLED=%d PIR=%s BUTTON=%s | ",
      sensors_enabled, oled_ok,
      motion_active ? (digitalRead(PIN_PIR) == HIGH ? "MOTION" : "CLEAR") : "OFF",
      button_down ? "PRESSED" : "RELEASED");
  const float cm[] = { recentCm(hc, now), recentCm(hc2, now),
                       recentCm(bowl_d1, now), recentCm(tank_d2, now) };
  protocolSerial().print("E1_CAT/E2_FOOD/D1_BOWL/D2_TANK cm=");
  for (unsigned i = 0; i < 4; ++i) {
    if (i) protocolSerial().print("/");
    if (std::isfinite(cm[i])) protocolSerial().printf("%.1f", double(cm[i]));
    else protocolSerial().print("--");
  }
  const float pct = currentWaterPercent(now);
  protocolSerial().print("  water_pct=");
  if (std::isfinite(pct)) protocolSerial().printf("%.0f", double(pct));
  else protocolSerial().print("-- (water_full + water_empty required)");
  protocolSerial().printf(
    " | LIMIT47=%s | DIAG HC1=%s/%s(e=%d,r=%.1f) HC2=%s/%s(e=%d,r=%.1f) FOOD=%s/%s(e=%d,r=%.1f) WATER=%s/%s(e=%d,r=%.1f)\n",
    USE_CLOSE_LIMIT_SWITCH ? (digitalRead(PIN_CLOSE_LIMIT) == LOW ? "LOW" : "HIGH") : "DISABLED",
    m4::name(hc.status.health), m4::name(hc.status.reason), digitalRead(13), hc.raw.valid ? double(hc.raw.value) : -1.0,
    m4::name(hc2.status.health), m4::name(hc2.status.reason), digitalRead(17), hc2.raw.valid ? double(hc2.raw.value) : -1.0,
    m4::name(bowl_d1.status.health), m4::name(bowl_d1.status.reason), digitalRead(15), bowl_d1.raw.valid ? double(bowl_d1.raw.value) : -1.0,
    m4::name(tank_d2.status.health), m4::name(tank_d2.status.reason), digitalRead(19), tank_d2.raw.valid ? double(tank_d2.raw.value) : -1.0
  );
}

bool stageWaterCalibration(bool full, uint32_t now) {
  const float cm = recentCm(tank_d2, now);
  if (!std::isfinite(cm)) {
    reply(0, false, "WATER_NO_VALID_DISTANCE_CHECK_JSN2_AND_sensors_on");
    return false;
  }
  if (full) {
    water_full_candidate = cm;
    water_full_staged = true;
  } else {
    water_empty_candidate = cm;
    water_empty_staged = true;
  }
  protocolSerial().printf("WATER_%s staged %.2fcm\n", full ? "FULL" : "EMPTY", double(cm));
  if (!water_full_staged || !water_empty_staged) {
    reply(0, true, "WATER_ONE_POINT_STAGED_SET_OTHER_POINT");
    return true;
  }
  m4::LevelCalibration g{};
  g.calibrated = true;
  g.full_cm = water_full_candidate;
  g.empty_cm = water_empty_candidate;
  if (!g.valid() || (g.empty_cm - g.full_cm) < 2.0f) {
    reply(0, false, "WATER_INVALID_FULL_MUST_BE_CLOSER_THAN_EMPTY_BY_2CM");
    return false;
  }
  bench_record.water = g;
  const bool saved = bench_nvs.save(bench_record);
  reply(0, saved, saved ? "WATER_CAL_SAVED_NVS" : "WATER_CAL_RAM_ONLY_NVS_FAILED");
  return saved;
}


char food = 'A';
char rx[384]{};
size_t rxn = 0;
bool discard = false;

void reply(uint32_t seq, bool ok, const char* detail);
void number(float v);
void telemetry(const Sample& s);
void command(char* line, const Sample& s);

void reply(
    uint32_t seq,
    bool ok,
    const char* detail) {

  protocolSerial().printf(
    "{\"type\":\"ack\","
    "\"boot\":%lu,"
    "\"seq\":%lu,"
    "\"ok\":%s,"
    "\"detail\":\"%s\"}\n",
    (unsigned long)boot_id,
    (unsigned long)seq,
    ok ? "true" : "false",
    detail
  );
}

void number(float v) {
  if (std::isfinite(v)) {
    protocolSerial().printf("%.5f", double(v));
  } else {
    protocolSerial().print("null");
  }
}

void telemetry(const Sample& s) {
  auto& out = protocolSerial();

  out.printf(
    "{\"type\":\"status\","
    "\"schema\":\"fc-cr-test-1\","
    "\"boot\":%lu,"
    "\"ms\":%lu,"
    "\"seq\":%lu,"
    "\"state\":\"%s\","
    "\"reason\":%u,"
    "\"configured\":%s,"
    "\"inspected\":%s,"
    "\"permit\":%s,"
    "\"pending\":%s,"
    "\"dose_id\":%lu,"
    "\"food\":\"%c\","
    "\"cal_generation\":%lu,"
    "\"healthy\":%s,"
    "\"calibrated\":%s,"
    "\"sample_ms\":%lu,"
    "\"grams\":",
    (unsigned long)boot_id,
    (unsigned long)s.now_ms,
    (unsigned long)receiver.last(),
    name(control.state()),
    unsigned(control.reason()),
    configured ? "true" : "false",
    inspected ? "true" : "false",
    permit ? "true" : "false",
    journal.pending ? "true" : "false",
    (unsigned long)control.id(),
    food,
    (unsigned long)s.generation,
    s.healthy ? "true" : "false",
    s.calibrated ? "true" : "false",
    (unsigned long)s.sample_at_ms
  );

  number(s.healthy ? s.grams : NAN);
  out.printf(",\"scheduled_protocol\":1,\"ai_oled\":\"%s\",\"inspect_required\":%s,\"demo_exited\":%s",bench_v8::oledAiLineText(s.now_ms),bench_v8::cat_inspect_required?"true":"false",bench_v8::demo_exited?"true":"false");

  out.print(",\"baseline_g\":");
  number(control.baselineGrams());

  out.print(",\"dose_g\":");
  number(control.actualGrams());

  out.print(",\"near_cm\":");
  number(recentCm(hc, s.now_ms));
  out.print(",\"hc2_cm\":");
  number(recentCm(hc2, s.now_ms));
  out.print(",\"food_distance_cm\":");
  number(recentCm(bowl_d1, s.now_ms));
  out.print(",\"water_distance_cm\":");
  number(recentCm(tank_d2, s.now_ms));
  out.print(",\"pcb_profile\":\"HCSR04_E1_E2_D1_D2_PINFIX\",\"pcb_e1_cat_cm\":");
  number(recentCm(hc,s.now_ms));
  out.print(",\"pcb_e2_food_cm\":"); number(recentCm(hc2,s.now_ms));
  out.print(",\"pcb_d1_bowl_cm\":"); number(recentCm(bowl_d1,s.now_ms));
  out.print(",\"pcb_d2_tank_cm\":"); number(recentCm(tank_d2,s.now_ms));
  out.print(",\"water_level_percent\":");
  number(currentWaterPercent(s.now_ms));
  out.printf(",\"motion\":%s,\"button_pressed\":%s,\"button_count\":%lu,\"button_last_ms\":%lu,\"oled_ok\":%s",
      motion_active ? (digitalRead(PIN_PIR) == HIGH ? "true" : "false") : "null",
      button_down ? "true" : "false",
      (unsigned long)bench_v8::button_request_count,
      (unsigned long)bench_v8::button_last_press_ms,
      oled_ok ? "true" : "false");

  out.printf(
    ",\"cat_fresh\":%s,"
    "\"close_trigger_g\":%.3f,"
    "\"calibration_source\":\"%s\","
    "\"tare_counts\":",
    gate.catFresh(s.now_ms) ? "true" : "false",
    double(bench_v8::CLOSE_AT_G),
    calibration_source
  );

  if (hx.calibration.valid()) {
    out.printf(
      "%.17g,\"grams_per_count\":%.17g",
      hx.calibration.tare_counts,
      hx.calibration.grams_per_count
    );
  } else {
    out.print("null,\"grams_per_count\":null");
  }

  // Golden UNO-style fast display; keep unsmoothed "grams" for safety control.
  out.print(",\"display_g\":");
  number(hx.display_grams.valid ? hx.display_grams.value : NAN);
  out.print(",\"signed_g\":");
  number(hx.signed_grams.valid ? hx.signed_grams.value : NAN);

  // New HX711 diagnostic fields.
  out.printf(
    ",\"hx_health\":\"%s\","
    "\"hx_reason\":\"%s\","
    "\"calibration_load\":\"%s\","
    "\"raw_valid\":%s,"
    "\"raw\":",
    m4::name(hx.status.health),
    m4::name(hx.status.reason),
    calibration_load,
    hx.raw.valid ? "true" : "false"
  );

  if (hx.raw.valid) {
    out.printf("%ld", (long)hx.raw.value);
  } else {
    out.print("null");
  }

  out.printf(
    ",\"raw_ms\":%lu,"
    "\"median_raw_valid\":%s",
    (unsigned long)hx.raw.sampled_at_ms,
    hx.median_raw.valid ? "true" : "false"
  );

  // Legacy FC1 state can remain DISARMED during the independent local demo.
  // Expose the actual bench state explicitly to avoid misleading telemetry.
  out.printf(
    ",\"bench_state\":\"%s\",\"bench_servo_armed\":%s,"
    "\"dog_running\":%s,\"bench_delta_g\":",
    bench_v8::stateText(),
    bench_v8::servo_armed ? "true" : "false",
    bench_v8::dog_running ? "true" : "false"
  );
  number(std::isfinite(bench_v8::last_delta_g) ? bench_v8::last_delta_g : NAN);
  out.printf(",\"meal_food\":\"FOOD_%c\",\"meal_starting_g\":", bench_v8::current_food);
  number(bench_v8::meal_starting_g);
  out.print(",\"meal_remaining_g\":");
  number(bench_v8::meal_remaining_g);
  out.print(",\"meal_consumed_g\":");
  number(bench_v8::meal_consumed_g);

  out.printf(",\"backup_enabled\":%s,\"backup_offline\":%s,\"backup_storage_ok\":%s,\"backup_wait_clear\":%s,\"backup_active\":%s",
    power_backup::enabled?"true":"false",power_backup::offline(s.now_ms)?"true":"false",
    power_backup::storage_ok?"true":"false",power_backup::gate.used?"true":"false",power_backup::active?"true":"false");

  out.printf(
    ",\"meal_preference\":\"%s\",\"meal_conclusion\":\"%s\","
    "\"closure_mode\":\"%s\",\"limit_switch_enabled\":%s,"
    "\"limit_switch_gpio\":%s,\"limit_switch_closed\":%s,"
    "\"physical_closed\":%s,\"automatic\":false}\n",
    bench_v8::meal_preference,
    bench_v8::conclusionText(bench_v8::current_food, bench_v8::meal_preference),
    USE_CLOSE_LIMIT_SWITCH ? "LIMIT_SWITCH" : "TIMED",
    USE_CLOSE_LIMIT_SWITCH ? "true" : "false",
    USE_CLOSE_LIMIT_SWITCH ? "47" : "null",
    USE_CLOSE_LIMIT_SWITCH ? (limit_closed ? "true" : "false") : "null",
    USE_CLOSE_LIMIT_SWITCH ? ((limit_closed || physical_closed_verified) ? "true" : "false") : "null"
  );
}

bool startBenchCal(BenchCal kind, double known_g, uint32_t now) {
  // Calibration is a non-actuating bench operation: never allowed during
  // feed runs, permit windows or with a servo PWM channel attached.
  if (bench_cal != BenchCal::Idle || bench_v8::busy() || pwm.moving()) {
    reply(0, false, "CAL_BLOCKED_DISARM_AND_STOP_OUTPUTS");
    return false;
  }
  if (kind == BenchCal::Reference && !hx.calibration.tared) {
    reply(0, false, "CAL_FIRST_TARE_EMPTY_TRAY");
    return false;
  }
  if (kind == BenchCal::Retare && !hx.calibration.valid()) {
    reply(0, false, "REZERO_REQUIRES_VALID_CALIBRATION");
    return false;
  }
  if (!hx.startAverage(15)) {
    reply(0, false, "HX_NOT_READY_TO_AVERAGE");
    return false;
  }
  bench_cal = kind;
  bench_known_g = known_g;
  bench_cal_started = now;
  reply(0, true, kind == BenchCal::Tare ? "TARE_SAMPLING_15_KEEP_EMPTY"
                   : kind == BenchCal::Reference ? "CAL_SAMPLING_15_KEEP_WEIGHT_STILL"
                   : "REZERO_SAMPLING_15_KEEP_EMPTY");
  return true;
}

void serviceBenchCal(uint32_t now) {
  if (bench_cal == BenchCal::Idle) return;
  if (bench_v8::busy() || pwm.moving()) {
    bench_cal = BenchCal::Idle;
    reply(0, false, "CAL_ABORT_OUTPUT_STATE_CHANGED");
    return;
  }
  if (uint32_t(now - bench_cal_started) > 10000u) {
    bench_cal = BenchCal::Idle;
    reply(0, false, "CAL_TIMEOUT_CHECK_HX711_DOUT_SCK");
    return;
  }
  if (!hx.averaged.valid) return;

  const BenchCal done = bench_cal;
  const double known = bench_known_g;
  bench_cal = BenchCal::Idle;
  bool ok = false;
  if (done == BenchCal::Tare) {
    ok = hx.tare();
  } else if (done == BenchCal::Reference) {
    ok = hx.calibrate(known);
    // Reject unrealistic electrical scale (near-zero difference).
    if (ok && std::fabs(1.0 / hx.calibration.grams_per_count) < 5.0) {
      ok = false;
      hx.applyCalibration({});
    }
  } else if (done == BenchCal::Retare) {
    ok = hx.tarePreservingFactor();
  }
  if (!ok) {
    reply(0, false, "CAL_FAILED_CHECK_WEIGHT_AND_WIRING");
    return;
  }

  bench_record.hx711 = hx.calibration;
  const bool saved = bench_nvs.save(bench_record);
  calibration_source = saved ? "SERIAL_BENCH_NVS" : "SERIAL_BENCH_RAM_ONLY";
  calibration_load = saved ? "SAVED" : "SAVE_FAILED";
  const double counts_per_g = hx.calibration.valid()
    ? 1.0 / hx.calibration.grams_per_count : 0.0;
  protocolSerial().printf(
    "{\"type\":\"hx_cal\",\"operation\":\"%s\","
    "\"ok\":true,\"saved\":%s,\"tare_counts\":%.3f,"
    "\"grams_per_count\":%.12g,\"counts_per_gram\":%.5f,"
    "\"reference_grams\":%.3f}\n",
    done == BenchCal::Tare ? "tare" :
    done == BenchCal::Reference ? "cal" : "rezero",
    saved ? "true" : "false",
    hx.calibration.tare_counts,
    hx.calibration.grams_per_count,
    counts_per_g,
    known
  );
  reply(0, saved, saved ? "CAL_DONE_SAVED_NVS" : "CAL_RAM_ONLY_NVS_SAVE_FAILED");
}

void command(char* line, const Sample& s) {
  // Accept whitespace surrounding manual commands; prevent invisible blanks
  // from making the user's '1' silently look like an FC1 packet.
  char* begin = line;
  while (*begin == ' ' || *begin == '\t') ++begin;
  if (begin != line) std::memmove(line, begin, std::strlen(begin) + 1);
  size_t n = std::strlen(line);
  while (n && (line[n - 1] == ' ' || line[n - 1] == '\t')) line[--n] = 0;
  if (!n) return;
  if (scheduled_feed_v1::command(line,s.now_ms)) return;
  if (!std::strcmp(line,"servo_position")) {
    const auto p = bench_v8::timed_gate_stop;
    protocolSerial().printf("SERVO ESTIMATE=%s feedback=NONE inspect_lock=%d moving=%d open_ms=%u close_ms=%u open_us=%u close_us=%u\n",
      p==bench_v8::TimedGateStop::OPEN ? "OPEN" : p==bench_v8::TimedGateStop::CLOSED ? "CLOSED" : "UNKNOWN",
      int(bench_v8::cat_inspect_required),int(pwm.moving()),unsigned(bench_v8::open_ms),unsigned(bench_v8::close_ms),unsigned(bench_v8::SERVO_OPEN_US),unsigned(bench_v8::SERVO_CLOSE_US));
    return;
  }
  // 1/2 retain CAT/DOG semantics used by Jetson; 3/4 are UNO full strokes.
  if (!std::strcmp(line, "3") || !std::strcmp(line, "servo_open")) {
    bench_v8::manualServoMove(true, bench_v8::open_ms, s.now_ms);
    return;
  }
  if (!std::strcmp(line, "4") || !std::strcmp(line, "servo_close")) {
    bench_v8::manualServoMove(false, bench_v8::close_ms, s.now_ms);
    return;
  }
  // Only the supervised BENCH state machine handles numeric 0/1/2 commands.
  if (!std::strcmp(line, "0")) {
    // "Exit" the CAT/DOG DEMO state machine (MCU/OLED continues running).
    bench_v8::cancel("USER 0 EXIT", false);
    bench_v8::buzzerStop();
    bench_v8::demo_exited = true;
    bench_v8::servo_armed = false;
    protocolSerial().print("EXIT 0 V14: CAT/DOG demo OFF; buzzer GPIO1 inactive, servo held at 1500us. Type start to re-enter.\n");
    return;
  }
  if (!std::strcmp(line, "start")) {
    if (bench_v8::busy() || pwm.moving()) {
      protocolSerial().print("START BLOCKED: motor state busy. Check physical mechanism.\n");
      return;
    }
    bench_v8::demo_exited = false;
    if (!sensors_enabled) {
      const bool ok = beginAllSensors();
      protocolSerial().printf("START SENSOR INIT: %s\n", ok ? "OK" : "FAILED");
    }
    protocolSerial().print("DEMO STARTED: use 1 CAT, 2 DOG, 0 EXIT. CAT no longer needs servo_arm.\n");
    return;
  }
  if (!std::strcmp(line, "mode")) {
    protocolSerial().printf("V14 MODE: exited=%d sensor=%d cat=%s dog=%d buzzer_configured=%d inspect_lock=%d servo_moving=%d\n",
      int(bench_v8::demo_exited), int(sensors_enabled), bench_v8::stateText(),
      int(bench_v8::dog_running), int(bench_v8::buzzer_armed),
      int(bench_v8::cat_inspect_required), int(pwm.moving()));
    return;
  }
  if (!std::strcmp(line, "help")) {
    protocolSerial().print(
      "FOR_CAT: mode hx status weight tare cal 38 cal 20 t cal_cancel\n"
      "SENSORS: sensors_on sensors_off sensors oled water_full water_empty water_reset\n"
      "V14 BENCH ONLY: sensor auto-on after verified ECHO level shifting; 1/2/0 work directly\n"
      "1=CAT wait HC1(2..30cm), open, add 35g target, reverse close\n"
      "2=DOG servo OFF, 3 short + 5s long, duplicates during alarm IGNORED\n"
      "0=EXIT demo outputs OFF; start=resume; inspect_ok after interrupted motor motion\n"
      "SERVO DIAG: servo_arm -> servo_test_open OR servo_test_close (motor disconnected!)\n"
      "DOG: choose buzzer_high OR buzzer_low ONCE to match verified hardware\n"
      "BUZZER: buzzer_status, buzzer_off. Duplicate 2 while beeping ignored.\n"
      "SERVO: 3/servo_open=RIGHT 1350us 900ms; 4/servo_close=LEFT 1600us 1450ms\n"
      "STOP: 0/stop = hold 1500us; no fine adjustment\n"
      "SERVO: duplicate full strokes ignored; servo_position shows estimate only\n"
      "AFTER ABORT: align gate CLOSED by hand with servo power OFF, restore power, then inspect_ok\n"
      "TUNE: open_ms 900, close_ms 1450 (100..5000ms), idle only; stop\n"
      "CLOSURE: TIMED; GPIO47 disabled; physical position UNKNOWN.\n"
      "sensors_on: ONLY AFTER checking ALL ECHO and PIR OUT <=3.3V.\n"
      "D2 TANK uses TRIG18 ECHO19. OLED uses SDA8 SCL9 @0x3C.\n"
      "water_full / water_empty: hold water at known FULL / EMPTY positions.\n"
      "Servo/pump/buzzer stay off at boot; GPIO1=buzzer; GPIO6=servo.\n"
      "WARNING: timed reverse is NOT verified mechanical closure. No Jetson AI feed enabled.\n"
    );
    return;
  }
  if (!std::strcmp(line, "inspect_ok")) {
    if (bench_v8::busy() || pwm.moving()) {
      protocolSerial().print("INSPECT LOCK: stop motor, physically verify gate position.\n");
      return;
    }
    power_backup::inspected(s.now_ms);
    bench_v8::cat_inspect_required = false;
    bench_v8::timed_gate_stop = bench_v8::TimedGateStop::CLOSED;
    bench_v8::feed_stage = bench_v8::FeedStage::IDLE;
    protocolSerial().print("BENCH INSPECT ACK: operator confirms gate aligned CLOSED; this is not sensor feedback. CAT may resume.\n");
    return;
  }
  if (!std::strcmp(line, "servo_arm")) {
    if (bench_v8::demo_exited) {
      protocolSerial().print("SERVO ARM BLOCKED: demo exited; type start.\n");
    } else if (bench_v8::busy() || pwm.moving() || bench_v8::cat_inspect_required) {
      protocolSerial().print("SERVO ARM BLOCKED: busy/PWM/inspect_lock\n");
    } else {
      bench_v8::servo_armed = true;
      protocolSerial().print("SERVO ARMED FOR ONE SUPERVISED BENCH CYCLE.\n");
    }
    return;
  }
  if (!std::strcmp(line, "buzzer_high")) {
    bench_v8::buzzerMode(true);
    return;
  }
  if (!std::strcmp(line, "buzzer_low")) {
    bench_v8::buzzerMode(false);
    return;
  }
  if (!std::strcmp(line, "buzzer_off")) {
    bench_v8::buzzerStop();
    // Keep a configured buzzer GPIO driven at INACTIVE, not floating INPUT.
    // A floating active-low input can keep buzzing after a stop command.
    protocolSerial().print("BUZZER OFF V14: GPIO1 driven INACTIVE. If still audible, set buzzer_low/high to match hardware or disconnect power.\n");
    return;
  }
  if (!std::strcmp(line, "buzzer_status")) {
    protocolSerial().printf(
      "BUZZER V14: configured=%d active_%s running=%d pin_on=%d phase=%u elapsed_ms=%lu\n",
      int(bench_v8::buzzer_armed),
      bench_v8::buzzer_active_high ? "HIGH" : "LOW",
      int(bench_v8::dog_running), int(bench_v8::buzzer_output_on),
      (unsigned)bench_v8::dog_phase,
      (unsigned long)(bench_v8::dog_running ? uint32_t(s.now_ms - bench_v8::dog_started_at) : 0u));
    return;
  }
  if (!std::strcmp(line, "servo_test_open")) {
    bench_v8::diagServo(true, s.now_ms);
    return;
  }
  if (!std::strcmp(line, "servo_test_close")) {
    bench_v8::diagServo(false, s.now_ms);
    return;
  }
  if (!std::strcmp(line, "a") || !std::strcmp(line, "A") || !std::strcmp(line, "food_a")) {
    bench_v8::current_food = 'A';
    food = 'A';
    protocolSerial().print("FOOD SELECTED: MON A (FOOD_A - mon meo thich khi an >=18g / con ~2g).\n");
    return;
  }
  if (!std::strcmp(line, "b") || !std::strcmp(line, "B") || !std::strcmp(line, "food_b")) {
    bench_v8::current_food = 'B';
    food = 'B';
    protocolSerial().print("FOOD SELECTED: MON B (FOOD_B - mon meo khong thich khi an <=5g / con ~30..35g).\n");
    return;
  }
  if(power_backup::command(line,s.now_ms)) return;
  if (!std::strcmp(line, "ai_cat")) {
    bench_v8::ai_species = 'C';
    bench_v8::ai_species_ms = s.now_ms;
    return;
  }
  if (!std::strcmp(line, "ai_dog")) {
    bench_v8::ai_species = 'D';
    bench_v8::ai_species_ms = s.now_ms;
    return;
  }
  if (!std::strcmp(line, "ai_none")) {
    bench_v8::ai_species = 'N';
    bench_v8::ai_species_ms = 0;
    return;
  }
  if (!std::strcmp(line, "1a") || !std::strcmp(line, "1A")) {
    bench_v8::current_food = 'A';
    food = 'A';
    protocolSerial().print("FOOD SELECTED: MON A -> Starting CAT feed cycle...\n");
    bench_v8::beginCat(s);
    return;
  }
  if (!std::strcmp(line, "1b") || !std::strcmp(line, "1B")) {
    bench_v8::current_food = 'B';
    food = 'B';
    protocolSerial().print("FOOD SELECTED: MON B -> Starting CAT feed cycle...\n");
    bench_v8::beginCat(s);
    return;
  }
  if (!std::strcmp(line, "eval") || !std::strcmp(line, "ket_luan")) {
    float grams = NAN;
    uint32_t sample_ms = 0;
    if (bench_v8::benchScaleSample(s.now_ms, grams, sample_ms)) {
      const float base = std::isfinite(bench_v8::baseline_g) ? bench_v8::baseline_g : 0.0f;
      bench_v8::meal_remaining_g = std::max(0.0f, grams - base);
      if (!std::isfinite(bench_v8::meal_starting_g) || bench_v8::meal_starting_g <= 0.0f) {
        bench_v8::meal_starting_g = 35.0f;
      }
    }
    bench_v8::meal_logged = true;
    bench_v8::emitMealPreferenceLog(s.now_ms, "MANUAL_EVAL");
    return;
  }
  if (!std::strcmp(line, "limit")) {
    if (!USE_CLOSE_LIMIT_SWITCH) {
      protocolSerial().print("LIMIT SWITCH DISABLED: closing uses close_ms; physical position UNKNOWN.\n");
      return;
    }
    const int lvl = digitalRead(PIN_CLOSE_LIMIT);
    protocolSerial().printf("LIMIT_GPIO47: raw=%s debounced=%s physical_closed=%d\n",
      lvl == LOW ? "LOW(PRESSED)" : "HIGH(RELEASED)",
      limit_closed ? "PRESSED" : "RELEASED", int(physical_closed_verified));
    return;
  }
  if (!std::strcmp(line, "manual_feed") || !std::strcmp(line, "btn")) {
    ++bench_v8::button_request_count;
    bench_v8::button_last_press_ms = s.now_ms;
    bench_v8::beginManualFeed(s.now_ms, "WEB_OR_SCHEDULE");
    return;
  }
  if (!std::strcmp(line, "1")) {
    food = bench_v8::current_food;
    bench_v8::beginCat(s);
    return;
  }
  if (!std::strcmp(line, "2")) {
    bench_v8::dogStart(s.now_ms);
    return;
  }
  if (!std::strncmp(line, "open_ms ", 8)) {
    protocolSerial().print(bench_v8::setMotionTime(line+8, true)
      ? "SERVO OPEN DURATION UPDATED\n" : "Invalid ms: choose 100..5000, idle only.\n");
    return;
  }
  if (!std::strncmp(line, "close_ms ", 9)) {
    protocolSerial().print(bench_v8::setMotionTime(line+9, false)
      ? "SERVO CLOSE DURATION UPDATED\n" : "Invalid ms: choose 100..5000, idle only.\n");
    return;
  }
  if (!std::strcmp(line, "stop")) {
    bench_v8::cancel("MANUAL STOP", false);
    bench_v8::buzzerStop();
    protocolSerial().print("BENCH STOP V14: PWM held at 1500us; buzzer GPIO1 inactive. Physical door closure NOT VERIFIED.\n");
    return;
  }
  if (!std::strcmp(line, "sensors_on")) {
    const bool ok = beginAllSensors();
    reply(0, ok, ok ? "SENSORS_ON_MEASURE_4_ULTRASONIC_PIR" : "SENSOR_PIN_SETUP_FAILED");
    return;
  }
  if (!std::strcmp(line, "sensors_off")) {
    const bool was_enabled = sensors_enabled;
    sensors_enabled = false;
    motion_active = false;
    hc_active = false;
    if (was_enabled) {
      digitalWrite(12, LOW); digitalWrite(16, LOW);
      digitalWrite(14, LOW); digitalWrite(18, LOW);
    }
    reply(0, true, "SENSORS_OFF_TRIG_LOW");
    return;
  }
  if (!std::strcmp(line, "sensors") || !std::strcmp(line, "oled")) {
    printSensorSummary(s.now_ms);
    updateOLED(s.now_ms);
    return;
  }
  if (!std::strcmp(line, "water_full") || !std::strcmp(line, "water_empty")) {
    reply(0,false,"WATER_CALIBRATION_DEFERRED_NEW_PCB_D1_BOWL_D2_TANK");
    return;
  }
  if (!std::strcmp(line, "water_reset")) {
    water_full_staged = water_empty_staged = false;
    water_full_candidate = water_empty_candidate = NAN;
    bench_record.water = {};
    const bool saved = bench_nvs.save(bench_record);
    reply(0, saved, saved ? "WATER_CAL_CLEARED_NVS" : "WATER_CAL_RAM_ONLY");
    return;
  }
  if (!std::strcmp(line, "tare")) {
    startBenchCal(BenchCal::Tare, 0, s.now_ms);
    return;
  }
  if (!std::strcmp(line, "t")) {
    startBenchCal(BenchCal::Retare, 0, s.now_ms);
    return;
  }
  if (!std::strcmp(line, "cal_cancel")) {
    bench_cal = BenchCal::Idle;
    reply(0, true, "CAL_CANCELLED_NO_ACTUATOR_MOTION");
    return;
  }
  if (!std::strncmp(line, "cal ", 4)) {
    char* end = nullptr;
    const double g = std::strtod(line + 4, &end);
    if (end == line + 4 || *end != '\0'
        || !std::isfinite(g) || g < 1.0 || g > 1000.0) {
      reply(0, false, "CAL_USE_KNOWN_GRAMS_EG_cal_38");
    } else {
      startBenchCal(BenchCal::Reference, g, s.now_ms);
    }
    return;
  }
  if (!std::strcmp(line, "hx_diag")) {
    protocolSerial().printf("HX_DIAG DT4=%d SCK5=%d health=%s reason=%s raw_valid=%d last_raw=%ld raw_ms=%lu calibrated=%d\n",
      digitalRead(4), digitalRead(5), m4::name(hx.status.health), m4::name(hx.status.reason),
      int(hx.raw.valid), (long)hx.raw.value, (unsigned long)hx.raw.sampled_at_ms,
      int(hx.calibration.valid()));
    return;
  }
  // Read-only commands remain available.
  if (!std::strcmp(line, "weight") || !std::strcmp(line, "g")) {
    if (hx.display_grams.valid) {
      protocolSerial().printf(
        "WEIGHT = %.1f g | raw=%ld | scale=%+.6f counts/g\n",
        double(hx.display_grams.value),
        hx.raw.valid ? (long)hx.raw.value : 0L,
        1.0 / hx.calibration.grams_per_count
      );
    } else if (!hx.calibration.valid()) {
      protocolSerial().print("WEIGHT NOT CALIBRATED: tare, then cal 38\n");
    } else {
      protocolSerial().print("WEIGHT NOT READY: check HX711 RAW signal\n");
    }
    return;
  }
  if (!std::strcmp(line, "hx")
      || !std::strcmp(line, "status")) {
    telemetry(s);
    return;
  }

  if (!std::strcmp(line, "STOP")) {
    bench_v8::cancel("MANUAL STOP", false);
    bench_v8::buzzerStop();
    protocolSerial().print("STOP: servo held at 1500us / buzzer OFF; physical gate state UNKNOWN.\n");
    return;
  }
  // V14 BENCH ISOLATION: do NOT interpret legacy FC1/Jetson packets here.
  // A typo must never set FC1 FAULT or start an autonomous actuator.
  protocolSerial().printf("UNKNOWN INPUT '%s'. Only manual commands permitted.\n", line);
}

} // end anonymous namespace

// ============================================================
// SETUP
// ============================================================

void setup() {
  protocolSerial().begin(115200);
  protocolSerial().print(
    "FOR_CAT ESP32-S3 OLED + HX711 + 4 ULTRA + PIR + WATER | 115200\n"
    "OLED SDA8 SCL9; HX DT4 SCK5; HC1 12/13; HC2 16/17;\n"
    "D1 BOWL 14/15; D2 TANK 18/19; PIR11; BUTTON21.\n"
    "SAFETY: This V12 bench config AUTO-ENABLES sensors. ALL ECHO/PIR OUT MUST BE <=3.3V!\n"
    "V14 MANUAL BENCH (NO JETSON MOTOR): 1 CAT, 2 DOG, 0 EXIT.\n"
    "1 CAT (HC1 2..30cm -> open -> +35g target -> timed reverse).\n"
    "2 DOG (first set buzzer_high/low; 3 short + long 5s). 0 EXIT.\n"
    "Empty loadcell before CAT; 35g can be PLACED after timed-open.\n"
    "V14: PWM 14bit; signed HX near zero; 4 ultrasonic auto-init; buzzer one-shot.\n"
    "SERVO UNO PROFILE: GPIO6 OPEN RIGHT 1350us/900ms, CLOSE LEFT 1600us/1450ms, STOP 1500us.\n"
    "TIMED CLOSE; GPIO47 disabled; physical position UNKNOWN.\n"
    "Servo/pump/buzzer do NOT run on startup; buzzer polarity must be configured.\n"
  );
  Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);
  Wire.setClock(400000);
  oled_ok = oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  if (oled_ok) product_oled::boot();
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  if (USE_CLOSE_LIMIT_SWITCH) {
    pinMode(PIN_CLOSE_LIMIT, INPUT_PULLUP);
    limit_raw_old = limit_closed = (digitalRead(PIN_CLOSE_LIMIT) == LOW);
    physical_closed_verified = limit_closed;
  }
  // Verified hardware uses ACTIVE_LOW buzzer on GPIO1; drive HIGH (inactive) at boot.
  bench_v8::buzzerMode(false);

  boot_id = esp_random();
  if (!boot_id) boot_id = 1;

  journal.load();

  control.boot(
    journal.initialized,
    journal.pending,
    journal.last
  );

  hx.begin(
    {
      {4, true},
      {5, true},
      500
    },
    millis()
  );

  m4::CalibrationRecord record;
  m4::NvsCalibration nvs;

  const auto loaded = nvs.load(record);
  // Preserve prior food/water geometry when rewriting HX711 calibration.
  if (loaded == m4::CalibrationLoad::LOADED) {
    bench_record = record;
    if (record.water.valid()) {
      water_full_candidate = record.water.full_cm;
      water_empty_candidate = record.water.empty_cm;
      water_full_staged = water_empty_staged = true;
    }
  }

  calibration_load =
    loaded == m4::CalibrationLoad::LOADED
      ? "LOADED"
      : loaded == m4::CalibrationLoad::INVALID
        ? "INVALID"
        : "MISSING";

  if (loaded == m4::CalibrationLoad::LOADED
      && record.hx711.valid()) {
    hx.applyCalibration(record.hx711);
    calibration_source = "NVS_SENSORS_V2";

  } else if (
      user_settings::exact_calibration_import_reviewed
      && std::strcmp(
        user_settings::calibration_provenance,
        "UNSET")
      && std::strlen(
        user_settings::calibration_provenance)) {

    m4::ScaleCalibration c;
    c.tared = true;
    c.calibrated = true;
    c.tare_counts = user_settings::tare_counts;
    c.grams_per_count = user_settings::grams_per_count;

    if (c.valid()) {
      hx.applyCalibration(c);
      calibration_source = "EXACT_REVIEWED_IMPORT";
    }
  }

  // V14 retains tested sensor/HX/OLED drivers, but isolates manual control from legacy FC1.
  // V12 fixes stale OLED '-- cm': auto-start four ultrasonic inputs when
  // configured for this previously-tested BENCH wiring. This does not
  // electrically lower 5V ECHO. GPIO input MUST be <=3.3V in the real rig.
  if (V12_AUTO_ENABLE_SENSORS_IF_LEVEL_SHIFTED) {
    const bool sensors_ok = beginAllSensors();
    protocolSerial().printf("V12 SENSORS AUTO: %s | E1/E2/D1/D2/PIR\n",
      sensors_ok ? "OK" : "FAILED CHECK WIRING");
  } else {
    protocolSerial().print("V12 SENSORS OFF: verify ECHO voltage, then sensors_on\n");
  }
  power_backup::begin(millis());
}

// ============================================================
// LOOP
// ============================================================

void loop() {
  const uint32_t now = millis();

  const uint32_t now_us = micros();
  if (sensors_enabled) {
    hc.poll(now_us, now);
    hc2.poll(now_us, now);
    bowl_d1.poll(now_us, now);
    tank_d2.poll(now_us, now);
  }
  tickButton(now);
  tickLimitSwitch(now);

  if (hc.raw.fresh) {
    gate.near(now, hc.raw.valid, hc.raw.value);
  }

  if (!ultrasonicBusy()) {
    hx.poll(now);
    serviceBenchCal(now);
  }

  const Sample s = adapter.read(hx, now);

  cat_near.observe(now,sensors_enabled&&hc.raw.valid,hc.raw.value,hc.raw.sampled_at_ms);
  bench_v8::tick(s, now);
  scheduled_feed_v1::tick();  // service immediately, even during ultrasonic polls
  power_backup::tick(now);
  // V14: legacy FC1 control.tick disabled in isolated bench test.
  // This avoids two state machines attempting to own the same servo output.

  // V14: no autonomous permit/heartbeat path in manual validation.
  permit = false;

  // RX MUST NOT be blocked by ultrasonic echoes. Immediate 0/2 commands
  // are processed even while an HC-SR04/JSN pulse is in flight.
  {
    unsigned budget = 128;

    while (budget-- && protocolSerial().available()) {
      const int value = protocolSerial().read();
      if (value < 0) break;

      const char c = char(value);

      if (c == '\r') continue;
      if (c == '0' && rxn == 0 && !discard) {
        char stop_line[] = "0";
        command(stop_line, s);
        continue;
      }

      if (c == '\n') {
        if (!discard && rxn) {
          rx[rxn] = 0;
          command(rx, s);
        }

        rxn = 0;
        discard = false;

      } else if (!discard) {
        if (c < 32
            || c > 126
            || rxn + 1 >= sizeof(rx)) {
          discard = true;
          rxn = 0;
          if (bench_v8::busy() || pwm.moving()) {
            bench_v8::cancel("INVALID SERIAL BYTE WHILE MOVING", false);
            bench_v8::buzzerStop();
            protocolSerial().print("SERIAL INVALID BYTE: servo and buzzer stopped; inspect physical gate.\n");
          } else {
            protocolSerial().print("INPUT INVALID BYTE: ignored (no FC1 fault).\n");
          }
        } else {
          rx[rxn++] = c;
        }
      }
    }

  }
  if (!ultrasonicBusy() && now - last_status >= 1000) {
    last_status = now;
    telemetry(s);
  }

  // UART output should drain regardless of acoustic sensor state.
  protocolSerial().drain();
  if (protocolSerial().takeOverflow()) {
    // Noncritical log overflow is reset, not allowed to latch an FC1 fault.
  }
  if (!ultrasonicBusy()) {
    updateOLED(now);
    tickUltrasonic(now);
  }
}
