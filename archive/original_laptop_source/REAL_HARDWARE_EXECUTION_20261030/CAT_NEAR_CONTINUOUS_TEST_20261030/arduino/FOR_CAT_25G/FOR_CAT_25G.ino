// FOR_CAT: single-file Arduino IDE version of CAT_NEAR_CONTINUOUS_TEST.
// Board: ESP32S3 Dev Module, ESP32 Arduino core 3.3.11, USB CDC On Boot Disabled.
// Serial is UART0 / external USB-UART bridge at 115200, not native USB CDC.
// No library install required beyond the ESP32 board package.
#include <Arduino.h>
#include <Preferences.h>
#include <driver/gpio.h>
#include <esp_system.h>
#include <cmath>
#include <cstring>
#include <cstdint>
#include <cstddef>
#include <cstdarg>
#include <cstdio>
#include <esp_arduino_version.h>
#if ESP_ARDUINO_VERSION_MAJOR < 3
#error "Select ESP32 Arduino board package 3.x (tested 3.3.11)"
#endif
#if !defined(CONFIG_IDF_TARGET_ESP32S3)
#error "Select ESP32S3 Dev Module"
#endif
#if ARDUINO_USB_CDC_ON_BOOT
#error "Disable USB CDC On Boot: this project uses Serial0 and the external UART bridge"
#endif
#define M4_SENSOR_BRINGUP 1
#define M4_QUAD_ULTRASONIC 1
#define FORCAT_MANUAL_STATION 1
void setup();
void loop();
namespace current_hardware {
constexpr int SERVO_SIGNAL=6,PUMP_CONTROL=7,OPTIONAL_WATER_INPUT=10;
}
namespace uart_v1 {
inline uint16_t crc16(const uint8_t* p,size_t n){uint16_t c=0xffff;for(size_t i=0;i<n;++i){c^=uint16_t(p[i])<<8;for(unsigned j=0;j<8;++j)c=c&0x8000?uint16_t((c<<1)^0x1021):uint16_t(c<<1);}return c;}
}

#include <cstdint>
namespace m4 {
constexpr int PIN_NOT_ASSIGNED = -1;
enum class Health : uint8_t {
  NOT_CONFIGURED, NOT_CONNECTED, NOT_CALIBRATED, INITIALIZING, HEALTHY, DEGRADED, FAULT
};
enum class Reason : uint8_t {
  NONE, CONFIGURATION_INVALID, TIMEOUT, BUS_ERROR, INVALID_DATA,
  NOT_CALIBRATED, GEOMETRY_INVALID, RANGE_INVALID, ACTUATORS_DISABLED,
  CLOCK_HALTED, RTC_INVALID_TIME, RTC_IO_ERROR, WRITE_PROTECTED, READBACK_MISMATCH, NO_RESPONSE
};
inline const char* name(Health health) {
  switch (health) {
    case Health::NOT_CONFIGURED: return "NOT_CONFIGURED";
    case Health::NOT_CONNECTED: return "NOT_CONNECTED";
    case Health::NOT_CALIBRATED: return "NOT_CALIBRATED";
    case Health::INITIALIZING: return "INITIALIZING";
    case Health::HEALTHY: return "HEALTHY";
    case Health::DEGRADED: return "DEGRADED";
    default: return "FAULT";
  }
}
inline const char* name(Reason reason) {
  switch (reason) {
    case Reason::NONE: return "NONE";
    case Reason::CONFIGURATION_INVALID: return "CONFIGURATION_INVALID";
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
template<class T> struct Reading {
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
}

#include <cstddef>
namespace m4 {
enum class Pull : uint8_t { NONE, UP, DOWN };
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
inline bool inputValid(PinIO& io, Pin pin) { return pin.reviewed && io.inputAllowed(pin.number); }
inline bool outputValid(PinIO& io, Pin pin) { return pin.reviewed && io.outputAllowed(pin.number); }
class I2CBus {
 public:
  virtual ~I2CBus() = default;
  virtual bool begin(Pin sda, Pin scl, uint16_t timeout_ms) = 0;
  virtual bool configured() const = 0;
  virtual bool ping(uint8_t address) = 0;
  virtual bool readRegisters(uint8_t address, uint8_t first, uint8_t* output, size_t count) = 0;
  virtual bool writeRegisters(uint8_t address, uint8_t first, const uint8_t* data, size_t count) = 0;
  virtual bool packet(uint8_t address, uint8_t control, const uint8_t* data, size_t count) = 0;
};
}

#include <cmath>
#include <cstdint>
namespace m4 {
inline bool rawValid(double raw) { return std::isfinite(raw) && raw >= -8388608 && raw <= 8388607; }
class RawAverage {
 public:
  bool begin(uint8_t count) {
    if (!count || count > 64) return false;
    needed_ = count; count_ = 0; sum_ = 0; return true;
  }
  bool add(int32_t raw) {
    if (!rawValid(raw) || !needed_ || count_ >= needed_) return false;
    sum_ += raw; ++count_; return true;
  }
  bool ready() const { return needed_ && count_ == needed_; }
  double mean() const { return ready() ? static_cast<double>(sum_) / count_ : 0; }
  uint8_t count() const { return count_; }
 private:
  uint8_t needed_ = 0, count_ = 0;
  int64_t sum_ = 0;
};
struct ScaleCalibration {
  bool tared = false, calibrated = false;
  double tare_counts = 0, grams_per_count = 0;
  bool tare(double empty_average) {
    if (!rawValid(empty_average)) return false;
    tared = true; calibrated = false; tare_counts = empty_average; grams_per_count = 0; return true;
  }
  bool reference(double loaded_average, double known_grams) {
    if (!tared || !rawValid(loaded_average) || !std::isfinite(known_grams) || known_grams <= 0 ||
        loaded_average == tare_counts) return false;
    const double factor = known_grams / (loaded_average - tare_counts);
    if (!std::isfinite(factor) || factor == 0) return false;
    grams_per_count = factor; calibrated = true; return true;
  }
  bool valid() const {
    return calibrated && tared && rawValid(tare_counts) && std::isfinite(grams_per_count) && grams_per_count != 0;
  }
  Reading<float> grams(double raw, uint32_t now) const {
    Reading<float> result;
    if (!valid() || !rawValid(raw)) return result;
    const double value = (raw - tare_counts) * grams_per_count;
    if (!std::isfinite(value) || value < 0 || value > 100000) return result;
    result = {true, static_cast<float>(value), now, true};
    return result;
  }
};
struct CalibrationError {
  bool valid = false;
  double absolute_grams = 0, relative_percent = 0;
};
inline CalibrationError compareMass(double measured, double reference) {
  if (!std::isfinite(measured) || !std::isfinite(reference) || measured < 0 || reference <= 0) return {};
  const double error = std::fabs(measured - reference);
  return {true, error, 100 * error / reference};
}
struct LevelCalibration {
  bool calibrated = false;
  float full_cm = 0, empty_cm = 0;
  bool valid() const { return calibrated && std::isfinite(full_cm) && std::isfinite(empty_cm) &&
                             full_cm > 0 && empty_cm > full_cm; }
  bool set(float full, float empty) {
    LevelCalibration next{true, full, empty};
    if (!next.valid()) return false;
    *this = next; return true;
  }
  Reading<float> percent(const Reading<float>& distance, float minimum, float maximum) const {
    if (!valid() || !distance.valid || !std::isfinite(distance.value) ||
        !std::isfinite(minimum) || !std::isfinite(maximum) || minimum <= 0 || maximum <= minimum ||
        distance.value < minimum || distance.value > maximum) return {};
    float value = 100 * (empty_cm - distance.value) / (empty_cm - full_cm);
    if (value < 0) value = 0;
    if (value > 100) value = 100;
    return {true, value, distance.sampled_at_ms, distance.fresh};
  }
};
}

namespace m4 {
class Hx711Median3 {
 public:
  void reset() { count_ = 0; }
  bool add(int32_t raw, int32_t& result) {
    values_[count_++] = raw;
    if (count_ != 3) return false;
    count_ = 0;
    int32_t a=values_[0], b=values_[1], c=values_[2], t;
    if (a>b) { t=a; a=b; b=t; }
    if (b>c) { t=b; b=c; c=t; }
    if (a>b) { t=a; a=b; b=t; }
    result=b; return true;
  }
 private:
  int32_t values_[3]{};
  uint8_t count_=0;
};
inline Reading<float> hx711SignedGrams(const ScaleCalibration& calibration, double raw, uint32_t now) {
  if (!calibration.valid() || !rawValid(raw)) return {};
  const double scale_factor=1.0/calibration.grams_per_count;
  const double grams=(raw-calibration.tare_counts)/scale_factor;
  if (!std::isfinite(scale_factor) || scale_factor==0 || !std::isfinite(grams) || std::fabs(grams)>100000) return {};
  return {true,static_cast<float>(grams),now,true};
}
class Hx711ReferenceDisplay {
 public:
  static constexpr float ZERO_DEADBAND=0.20f;
  static constexpr float FAST_CHANGE_THRESHOLD=1.0f;
  static constexpr float STABLE_ALPHA=0.40f;
  void reset() { displayed_=0; }
  Reading<float> update(const Reading<float>& measurement) {
    if (!measurement.valid || !std::isfinite(measurement.value)) { reset(); return {}; }
    if (!measurement.fresh) return {};
    float current=measurement.value;
    if (current>-ZERO_DEADBAND && current<ZERO_DEADBAND) current=0;
    if (current<0 && current>-0.5f) current=0;
    if (std::fabs(current-displayed_)>=FAST_CHANGE_THRESHOLD) displayed_=current;
    else displayed_=STABLE_ALPHA*current+(1.0f-STABLE_ALPHA)*displayed_;
    if (displayed_>-ZERO_DEADBAND && displayed_<ZERO_DEADBAND) displayed_=0;
    return {true,displayed_,measurement.sampled_at_ms,true};
  }
 private:
  float displayed_=0;
};
}

namespace m4 {
struct Hx711Config { Pin dout{}, sck{}; uint32_t ready_timeout_ms = 500; };
class Hx711 {
 public:
  explicit Hx711(PinIO& io) : io_(io) {}
  bool begin(Hx711Config config, uint32_t now) {
    active_ = averaging_ = false; raw = {}; averaged = {}; resetMeasurement();
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
    median_raw.fresh = signed_grams.fresh = display_grams.fresh = false;
    if (!active_) return;
    if (io_.read(config_.dout.number)) {
      if (static_cast<uint32_t>(now - waiting_at_) >= config_.ready_timeout_ms) {
        raw.valid = averaged.valid = false; resetMeasurement();
        averaging_ = false;
        status = {Health::NOT_CONNECTED, Reason::TIMEOUT};
      }
      return;
    }
    uint32_t bits = 0;
    io_.enterCritical();
    for (uint8_t bit = 0; bit < 24; ++bit) {
      io_.write(config_.sck.number, true); io_.pauseMicros(2);
      bits = (bits << 1) | (io_.read(config_.dout.number) ? 1u : 0u);
      io_.write(config_.sck.number, false); io_.pauseMicros(2);
    }
    io_.write(config_.sck.number, true); io_.pauseMicros(2);
    io_.write(config_.sck.number, false); io_.pauseMicros(2);
    io_.exitCritical();
    const int32_t signed_raw = bits & 0x800000 ? static_cast<int32_t>(bits) - 16777216 : static_cast<int32_t>(bits);
    raw = {true, signed_raw, now, true}; waiting_at_ = now;
    if (signed_raw == 0 || signed_raw == -1 || signed_raw == -8388608 || signed_raw == 8388607) {
      raw.valid = false;
      resetMeasurement(); averaged = {}; averaging_ = false;
      status = {Health::FAULT, Reason::INVALID_DATA}; return;
    }
    if (averaging_ && average_.add(signed_raw) && average_.ready()) {
      averaged = {true, average_.mean(), now, true}; averaging_ = false;
    }
    int32_t median=0;
    if (!median_.add(signed_raw,median)) {
      if (!median_raw.valid) status = calibration.valid() ? Status{Health::INITIALIZING, Reason::NONE} :
                                                          Status{Health::NOT_CALIBRATED, Reason::NOT_CALIBRATED};
      return;
    }
    median_raw = {true,median,now,true};
    signed_grams = hx711SignedGrams(calibration,median,now);
    display_grams = display_.update(signed_grams);
    grams = calibration.grams(median, now);
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
    resetMeasurement();
    status = {Health::NOT_CALIBRATED, Reason::NOT_CALIBRATED};
    return true;
  }
  bool calibrate(double known_grams) {
    if (!averaged.valid || !calibration.reference(averaged.value, known_grams)) return false;
    resetMeasurement(); status = {Health::INITIALIZING, Reason::NONE};
    return true;
  }
  void applyCalibration(const ScaleCalibration& next) {
    calibration = next; resetMeasurement(); averaged = {}; averaging_ = false;
    if (active_ && raw.valid)
      status = calibration.valid() ? Status{Health::INITIALIZING, Reason::NONE} :
                                    Status{Health::NOT_CALIBRATED, Reason::NOT_CALIBRATED};
  }
  bool tarePreservingFactor() {
    if (!averaged.valid || !calibration.valid()) return false;
    ScaleCalibration next=calibration; next.tare_counts=averaged.value;
    if (!next.valid()) return false;
    applyCalibration(next); return true;
  }
  Status status{};
  ScaleCalibration calibration{};
  Reading<int32_t> raw{};
  Reading<double> averaged{};
  Reading<float> grams{};
  Reading<int32_t> median_raw{};
  Reading<float> signed_grams{}, display_grams{};
 private:
  void resetMeasurement() {
    grams={}; median_raw={}; signed_grams={}; display_grams={};
    median_.reset(); display_.reset();
  }
  PinIO& io_;
  Hx711Config config_{};
  RawAverage average_{};
  Hx711Median3 median_{};
  Hx711ReferenceDisplay display_{};
  bool active_ = false, averaging_ = false;
  uint32_t waiting_at_ = 0;
};
}

#include <cstring>
namespace m4 {
struct CalibrationRecord {
  ScaleCalibration hx711{};
  LevelCalibration food{}, water{};
};
namespace calibration_record {
constexpr size_t SIZE = 39;
inline bool valid(const CalibrationRecord& record) {
  if (record.hx711.tared && !rawValid(record.hx711.tare_counts)) return false;
  if (!record.hx711.tared && (record.hx711.tare_counts != 0 || record.hx711.calibrated)) return false;
  if (record.hx711.calibrated && !record.hx711.valid()) return false;
  if (!record.hx711.calibrated && record.hx711.grams_per_count != 0) return false;
  const LevelCalibration* geometries[] = {&record.food, &record.water};
  for (const auto* geometry : geometries) {
    if (geometry->calibrated && !geometry->valid()) return false;
    if (!geometry->calibrated && (geometry->full_cm != 0 || geometry->empty_cm != 0)) return false;
  }
  return true;
}
inline void put(uint8_t* output, uint64_t bits, size_t count) {
  for (size_t i = 0; i < count; ++i) output[i] = static_cast<uint8_t>(bits >> (8*i));
}
inline uint64_t get(const uint8_t* input, size_t count) {
  uint64_t result = 0;
  for (size_t i = 0; i < count; ++i) result |= static_cast<uint64_t>(input[i]) << (8*i);
  return result;
}
inline bool encode(const CalibrationRecord& record, uint8_t (&bytes)[SIZE]) {
  static_assert(sizeof(double)==8 && sizeof(float)==4, "explicit sensor calibration numeric layout");
  if (!valid(record)) return false;
  bytes[0]='M'; bytes[1]='4'; bytes[2]='C'; bytes[3]=1;
  bytes[4] = (record.hx711.tared ? 1 : 0) | (record.hx711.calibrated ? 2 : 0) |
             (record.food.calibrated ? 4 : 0) | (record.water.calibrated ? 8 : 0);
  uint64_t bits;
  std::memcpy(&bits, &record.hx711.tare_counts, 8); put(bytes+5, bits, 8);
  std::memcpy(&bits, &record.hx711.grams_per_count, 8); put(bytes+13, bits, 8);
  const float values[] = {record.food.full_cm, record.food.empty_cm, record.water.full_cm, record.water.empty_cm};
  for (size_t i=0; i<4; ++i) { uint32_t word; std::memcpy(&word, values+i, 4); put(bytes+21+i*4, word, 4); }
  put(bytes+SIZE-2, uart_v1::crc16(bytes, SIZE-2), 2); return true;
}
inline bool decode(const uint8_t (&bytes)[SIZE], CalibrationRecord& record) {
  if (bytes[0]!='M' || bytes[1]!='4' || bytes[2]!='C' || bytes[3]!=1 || (bytes[4]&0xf0) ||
      get(bytes+SIZE-2,2) != uart_v1::crc16(bytes,SIZE-2)) return false;
  CalibrationRecord next;
  next.hx711.tared=bytes[4]&1; next.hx711.calibrated=bytes[4]&2;
  next.food.calibrated=bytes[4]&4; next.water.calibrated=bytes[4]&8;
  uint64_t bits=get(bytes+5,8); std::memcpy(&next.hx711.tare_counts,&bits,8);
  bits=get(bytes+13,8); std::memcpy(&next.hx711.grams_per_count,&bits,8);
  float* values[]={&next.food.full_cm,&next.food.empty_cm,&next.water.full_cm,&next.water.empty_cm};
  for (size_t i=0;i<4;++i) { uint32_t word=static_cast<uint32_t>(get(bytes+21+i*4,4)); std::memcpy(values[i],&word,4); }
  if (!valid(next)) return false;
  record=next; return true;
}
}
}

namespace m4 {
class ArduinoPins final : public PinIO {
 public:
  bool inputAllowed(int pin) const override {
    if (pin < 0 || pin > 48 || !GPIO_IS_VALID_GPIO(pin)) return false;
#if M4_SENSOR_BRINGUP || DISPENSE_BENCH_MODE
    if (pin==current_hardware::SERVO_SIGNAL || pin==current_hardware::PUMP_CONTROL ||
        (!M4_QUAD_ULTRASONIC && pin==current_hardware::OPTIONAL_WATER_INPUT)) return false;
#endif
#if defined(CONFIG_IDF_TARGET_ESP32S3)
    if ((pin >= 26 && pin <= 38) || pin==0 || pin==3 || pin==19 || pin==20 ||
        (pin >= 39 && pin <= 46)) return false;
#else
    if ((pin >= 6 && pin <= 11) || pin==0 || pin==2 || pin==5 || pin==12 || pin==15 || pin==1 || pin==3) return false;
#endif
    return true;
  }
  bool outputAllowed(int pin) const override { return inputAllowed(pin) && !(M4_QUAD_ULTRASONIC && pin==10) && GPIO_IS_VALID_OUTPUT_GPIO(pin); }
  void input(int pin, Pull pull) override { pinMode(pin, pull==Pull::UP ? INPUT_PULLUP : pull==Pull::DOWN ? INPUT_PULLDOWN : INPUT); }
  void output(int pin) override { pinMode(pin, OUTPUT); }
  bool read(int pin) override { return digitalRead(pin)==HIGH; }
  void write(int pin, bool high) override { digitalWrite(pin, high ? HIGH : LOW); }
  void pauseMicros(uint32_t short_us) override { if (short_us <= 10) delayMicroseconds(short_us); }
  void enterCritical() override { portENTER_CRITICAL(&mux_); }
  void exitCritical() override { portEXIT_CRITICAL(&mux_); }
 private:
  portMUX_TYPE mux_ = portMUX_INITIALIZER_UNLOCKED;
};

enum class CalibrationLoad : uint8_t { MISSING, INVALID, LOADED };
class NvsCalibration {
 public:
  static const char* key() {
#if M4_SENSOR_BRINGUP || DISPENSE_BENCH_MODE
    return "sensors-v2";
#else
    return "sensors-v1";
#endif
  }
  CalibrationLoad load(CalibrationRecord& record) {
    record = {};
    Preferences prefs;
    if (!prefs.begin("m4-calibration",true)) return CalibrationLoad::MISSING;
    if (!prefs.isKey(key())) { prefs.end(); return CalibrationLoad::MISSING; }
    uint8_t bytes[calibration_record::SIZE];
    const bool read=prefs.getBytesLength(key())==sizeof(bytes) &&
                    prefs.getBytes(key(),bytes,sizeof(bytes))==sizeof(bytes);
    prefs.end();
    return read && calibration_record::decode(bytes,record) ? CalibrationLoad::LOADED : CalibrationLoad::INVALID;
  }
  bool save(const CalibrationRecord& record) {
#if defined(FORCAT_MANUAL_STATION)
    (void)record; return false;
#else
    uint8_t bytes[calibration_record::SIZE];
    if (!calibration_record::encode(record,bytes)) return false;
    Preferences prefs;
    if (!prefs.begin("m4-calibration",false)) return false;
    const bool ok=prefs.putBytes(key(),bytes,sizeof(bytes))==sizeof(bytes);
    prefs.end(); return ok;
#endif
  }
};
}

namespace m4 { namespace servo_bench {
constexpr int pin=6;
constexpr uint16_t electrical_min_us=1000,electrical_max_us=2000;
class Output {public:virtual ~Output()=default;virtual bool start(uint16_t)=0;virtual bool write(uint16_t)=0;virtual bool off()=0;};
}}

#include <Arduino.h>
namespace m4 {
class LedcServoOutput final : public servo_bench::Output {
 public:
  bool off() override {
    bool stopped=true;
    if (attached_) {
      const bool zero=ledcWrite(servo_bench::pin,0);
      const bool detached=ledcDetach(servo_bench::pin);
      attached_=!detached;
      stopped=zero && detached;
    }
    digitalWrite(servo_bench::pin,LOW);
    pinMode(servo_bench::pin,OUTPUT);
    digitalWrite(servo_bench::pin,LOW);
    return stopped;
  }
  bool start(uint16_t pulse_us) override {
    if (attached_ || !valid(pulse_us)) return false;
    if (!ledcAttach(servo_bench::pin,50,16)) { off(); return false; }
    attached_=true;
    if (!write(pulse_us)) { off(); return false; }
    return true;
  }
  bool write(uint16_t pulse_us) override {
    if (!attached_ || !valid(pulse_us)) return false;
    const uint32_t duty=(static_cast<uint32_t>(pulse_us)*65536u+10000u)/20000u;
    return ledcWrite(servo_bench::pin,duty);
  }
  bool attached() const { return attached_; }
 private:
  static bool valid(uint16_t us) {
    return us>=servo_bench::electrical_min_us && us<=servo_bench::electrical_max_us;
  }
  bool attached_=false;
};
static_assert(current_hardware::SERVO_SIGNAL==servo_bench::pin,"GPIO6 servo contract");
}

#include <Arduino.h>
#if (defined(M4_DOG_WARNING) && M4_DOG_WARNING) || defined(FORCAT_MANUAL_STATION)
#include <cstdarg>
#include <cstdio>
#include <cstring>
class DogNonblockingSerial {
  uint8_t bytes_[8192]{};size_t head_=0,count_=0;bool overflow_=false;
 public:
  void begin(unsigned long baud){Serial0.begin(baud);}
  int available(){return Serial0.available();}int read(){return Serial0.read();}
  size_t write(const uint8_t* bytes,size_t n){
    if(n>sizeof(bytes_)-count_){overflow_=true;return 0;}
    for(size_t i=0;i<n;++i)bytes_[(head_+count_++)%sizeof(bytes_)]=bytes[i];
    return n;
  }
  void print(const char* text){write(reinterpret_cast<const uint8_t*>(text),std::strlen(text));}
  void println(const char* text){print(text);print("\r\n");}
  void printf(const char* format,...){char text[2048];va_list args;va_start(args,format);
    const int n=std::vsnprintf(text,sizeof(text),format,args);va_end(args);
    if(n<0 || static_cast<size_t>(n)>=sizeof(text)){overflow_=true;return;}
    write(reinterpret_cast<const uint8_t*>(text),static_cast<size_t>(n));
  }
  void drain(){
    const int room=Serial0.availableForWrite();size_t n=room>0?static_cast<size_t>(room):0;
    if(n>64)n=64;
    if(n>count_)n=count_;
    if(n>sizeof(bytes_)-head_)n=sizeof(bytes_)-head_;
    if(n){const size_t done=Serial0.write(bytes_+head_,n);head_=(head_+done)%sizeof(bytes_);count_-=done;}
  }
  bool overflowed()const{return overflow_;}
  bool empty()const{return count_==0;}
};
#endif
inline auto& protocolSerial() {
#if (defined(M4_DOG_WARNING) && M4_DOG_WARNING) || defined(FORCAT_MANUAL_STATION)
  static DogNonblockingSerial port;return port;
#elif defined(FORR_NATIVE_USB) && FORR_NATIVE_USB
  return Serial;
#else
  return Serial0;
#endif
}

#include <cstdint>
namespace forcat_continuous {
struct PulseCalibration {
    uint16_t safe_min_us=0,safe_max_us=0,neutral_us=0,neutral_low_us=0,neutral_high_us=0;
    uint16_t open_rotation_us=0,close_rotation_us=0;
    bool continuous_type_verified=false,neutral_verified=false,directions_verified=false;
    bool valid()const{
        return continuous_type_verified && neutral_verified && directions_verified &&
          safe_min_us>=1000 && safe_max_us<=2000 && safe_min_us<safe_max_us && safe_max_us-safe_min_us<=100 &&
          neutral_low_us>=safe_min_us && neutral_high_us<=safe_max_us && neutral_low_us<=neutral_us && neutral_us<=neutral_high_us &&
          open_rotation_us>=safe_min_us && open_rotation_us<=safe_max_us && close_rotation_us>=safe_min_us && close_rotation_us<=safe_max_us &&
          ((open_rotation_us>neutral_high_us && close_rotation_us<neutral_low_us) ||
           (open_rotation_us<neutral_low_us && close_rotation_us>neutral_high_us));
    }
};
enum class Rotation {Detached,Neutral,OpenDirection,CloseDirection,Unknown};
class Driver {
    m4::servo_bench::Output& pwm_;PulseCalibration calibration_{};
    bool configured_=false,attached_=false;Rotation rotation_=Rotation::Detached;
    bool rotate(uint16_t us,Rotation direction){
        if(!configured_ || !attached_)return false;
        const bool ok=pwm_.write(us);rotation_=ok?direction:Rotation::Unknown;return ok;
    }
 public:
    explicit Driver(m4::servo_bench::Output& pwm):pwm_(pwm){}
    bool boot(){configured_=false;calibration_={};return detach();}
    bool configure(PulseCalibration calibration){if(configured_ || attached_ || !calibration.valid())return false;calibration_=calibration;configured_=true;return true;}
    bool attachNeutral(){
        if(!configured_ || attached_)return false;
        attached_=true;
        const bool ok=pwm_.start(calibration_.neutral_us);rotation_=ok?Rotation::Neutral:Rotation::Unknown;return ok;
    }
    bool rotateOpen(){return rotate(calibration_.open_rotation_us,Rotation::OpenDirection);}
    bool rotateClose(){return rotate(calibration_.close_rotation_us,Rotation::CloseDirection);}
    bool neutral(){
        if(!attached_)return true;
        const bool ok=pwm_.write(calibration_.neutral_us);rotation_=ok?Rotation::Neutral:Rotation::Unknown;return ok;
    }
    bool detach(){const bool ok=pwm_.off();if(ok){attached_=false;rotation_=Rotation::Detached;}else rotation_=Rotation::Unknown;return ok;}
    bool attached()const{return attached_;}
    Rotation rotation()const{return rotation_;}
};
}

#include <cmath>
#include <cstdint>
namespace forcat_continuous {
enum class Mode {Supervised,Automatic};
enum class State {Disarmed,Armed,Baseline,Opening,WaitingMass,Closing,NeutralHold,Settling,AwaitingOwner,Complete,FaultClosing,FaultNeutral,Fault};
enum class Reason {None,Config,Approval,Position,Weight,Calibration,Clock,ConflictingSample,Lease,Timeout,NoProgress,Overshoot,UnderTarget,Stopped,Output,Persistence,Inspection,Duplicate,Busy};
inline const char* name(State s){switch(s){
    case State::Disarmed:return "DISARMED";case State::Armed:return "ARMED_NO_MOTION";
    case State::Baseline:return "WAIT_BASELINE";case State::Opening:return "ROTATE_OPEN_DIRECTION";
    case State::WaitingMass:return "NEUTRAL_WAIT_MASS";case State::Closing:return "ROTATE_CLOSE_DIRECTION";
    case State::NeutralHold:return "NEUTRAL_STOP_COMMAND";case State::Settling:return "WAIT_STABLE_MASS";
    case State::AwaitingOwner:return "MEASURED_NEEDS_OWNER_CONFIRMATION";case State::Complete:return "COMPLETE_WITH_POSITION_FEEDBACK";
    case State::FaultClosing:return "FAULT_BOUNDED_CLOSE_UNVERIFIED";case State::FaultNeutral:return "FAULT_NEUTRAL_COMMAND";default:return "FAULT";
}}
struct Sample {uint32_t now_ms=0,sample_at_ms=0,generation=0;bool healthy=false,calibrated=false,fresh=false;float grams=0;};
struct Position {bool available=false,healthy=false,qualified=false,closed=false,opened=false;uint32_t observed_ms=0;};
struct Settings {
    PulseCalibration pulses{};
    uint32_t opening_ms=0,closing_ms=0,neutral_hold_ms=0,settle_ms=0,stable_span_ms=0;
    uint32_t baseline_timeout_ms=0,settle_timeout_ms=0,no_progress_ms=0,total_timeout_ms=0;
    float stable_range_g=0,closing_lead_g=0;
    bool travel_timing_verified=false,closing_lead_verified=false,detach_after_neutral=false,pwm_loss_stop_verified=false;
    bool supervised_bounded_fault_close=false;
    bool supervised_early_close_trial=false;
    bool valid()const{return pulses.valid() && travel_timing_verified && opening_ms>=20 && opening_ms<=5000 &&
        closing_ms>=20 && closing_ms<=3000 && neutral_hold_ms>=20 && neutral_hold_ms<=500 && settle_ms>=500 && settle_ms<=5000 &&
        stable_span_ms>=100 && stable_span_ms<=1500 && baseline_timeout_ms>=1000 && baseline_timeout_ms<=10000 &&
        settle_timeout_ms>=settle_ms+stable_span_ms && settle_timeout_ms<=10000 && no_progress_ms>=500 && no_progress_ms<=10000 &&
        total_timeout_ms>opening_ms+closing_ms+neutral_hold_ms+settle_ms+stable_span_ms && total_timeout_ms<=60000 &&
        std::isfinite(stable_range_g) && stable_range_g>0 && stable_range_g<=2 &&
        std::isfinite(closing_lead_g) && closing_lead_g>=0 &&
        (supervised_early_close_trial ? closing_lead_g<=15 : closing_lead_g<=3) &&
        (closing_lead_g==0 || closing_lead_verified || supervised_early_close_trial) && (!detach_after_neutral || pwm_loss_stop_verified);}
};
class Journal {public:virtual ~Journal()=default;virtual bool write(bool pending,uint32_t id)=0;};
class Controller {
    Driver& driver_;Journal& journal_;Settings settings_{};Mode mode_=Mode::Supervised;
    State state_=State::Disarmed;Reason reason_=Reason::None;
    bool configured_=false,locked_=true,have_clock_=false,have_sample_=false,baseline_valid_=false,actual_valid_=false;
    bool in_effect_=false,new_sample_=false,left_closed_=false,open_confirmed_=false,close_started_=false;
    uint32_t epoch_=0,last_now_=0,observed_at_=0,generation_=0,phase_at_=0,started_at_=0,lease_at_=0;
    uint32_t opening_at_=0,closing_at_=0,last_progress_=0,highwater_=0,id_=0;
    unsigned arms_=0,window_count_=0;float observed_grams_=0,baseline_=0,actual_=0,latest_=0,last_progress_mass_=0;
    float window_[4]{};uint32_t window_time_[4]{};
    struct Effect {bool& flag;explicit Effect(bool& f):flag(f){flag=true;}~Effect(){flag=false;}};
    template<class F> bool effect(F f){Effect guard(in_effect_);return f();}
    bool terminal()const{return state_==State::Disarmed || state_==State::AwaitingOwner || state_==State::Complete || state_==State::Fault;}
    bool faultState()const{return state_==State::FaultClosing || state_==State::FaultNeutral || state_==State::Fault;}
    void resetWindow(){window_count_=0;}
    bool clock(uint32_t now){
        if(have_clock_ && static_cast<uint32_t>(now-last_now_)>0x7fffffffu)return false;
        have_clock_=true;last_now_=now;return true;
    }
    bool positionUsable(const Sample& s,const Position& p)const{return p.available&&p.healthy&&p.qualified&&
        !(p.closed&&p.opened)&&static_cast<uint32_t>(s.now_ms-p.observed_ms)<=1500;}
    bool closedNow(const Sample& s,const Position& p)const{return positionUsable(s,p)&&p.closed&&close_started_&&
        static_cast<uint32_t>(p.observed_ms-closing_at_)<=0x7fffffffu;}
    Reason sample(const Sample& s,bool require_new){
        new_sample_=false;
        if(!s.calibrated || !s.generation)return Reason::Calibration;
        if(!s.healthy || !std::isfinite(s.grams) || std::fabs(s.grams)>100000 || static_cast<uint32_t>(s.now_ms-s.sample_at_ms)>1500)return Reason::Weight;
        if(have_sample_){
            const auto delta=static_cast<uint32_t>(s.sample_at_ms-observed_at_);
            if(delta>0x7fffffffu || (delta==0 && s.grams!=observed_grams_))return Reason::ConflictingSample;
            if(!s.fresh && (delta || s.grams!=observed_grams_))return Reason::Weight;
            new_sample_=s.fresh && delta!=0;
        }else new_sample_=s.fresh;
        if(require_new && !s.fresh)return Reason::Weight;
        if(s.fresh){have_sample_=true;observed_at_=s.sample_at_ms;observed_grams_=s.grams;}
        return Reason::None;
    }
    bool stable(float& mean){
        if(window_count_<4)return false;
        const unsigned last=(window_count_-1)%4,first=window_count_%4;
        if(static_cast<uint32_t>(window_time_[last]-window_time_[first])<settings_.stable_span_ms)return false;
        float lo=window_[0],hi=lo,total=0;
        for(float v:window_){if(v<lo)lo=v;if(v>hi)hi=v;total+=v;}
        mean=total/4;return hi-lo<=settings_.stable_range_g;
    }
    void add(const Sample& s){if(!new_sample_)return;const auto i=window_count_%4;window_[i]=s.grams;window_time_[i]=s.sample_at_ms;++window_count_;}
    void compensateNeutral(){
        const bool neutral=effect([&]{return driver_.neutral();});
        if(!neutral){reason_=Reason::Output;effect([&]{return driver_.detach();});state_=State::Fault;}
    }
    void neutral(uint32_t now,bool fault){
        ++epoch_;phase_at_=now;state_=fault?State::FaultNeutral:State::NeutralHold;
        if(in_effect_)return;
        compensateNeutral();
    }
    void fault(Reason why,uint32_t now,bool force_neutral=false){
        if(faultState())return;
        reason_=why;locked_=true;
        if(why!=Reason::UnderTarget && !(why==Reason::Overshoot && state_==State::Settling && actual_valid_))actual_valid_=false;
        const bool can_close=!force_neutral && settings_.supervised_bounded_fault_close && mode_==Mode::Supervised &&
            (state_==State::Opening || state_==State::WaitingMass || state_==State::Closing) &&
            why!=Reason::Clock && why!=Reason::Position && why!=Reason::Output && !in_effect_;
        if(can_close){
            ++epoch_;
            if(state_!=State::Closing){closing_at_=now;close_started_=true;}
            state_=State::FaultClosing;const auto epoch=epoch_;
            const bool ok=effect([&]{return driver_.rotateClose();});
            if(epoch!=epoch_){compensateNeutral();return;}
            if(!ok){reason_=Reason::Output;neutral(now,true);}return;
        }
        neutral(now,true);
    }
    void open(const Sample& s){
        ++epoch_;state_=State::Opening;opening_at_=s.now_ms;last_progress_=s.now_ms;last_progress_mass_=0;resetWindow();
        const auto epoch=epoch_;const bool attached=driver_.attached()?driver_.rotation()==Rotation::Neutral:effect([&]{return driver_.attachNeutral();});
        if(epoch!=epoch_ || state_!=State::Opening){compensateNeutral();return;}
        if(!attached){fault(Reason::Output,s.now_ms,true);return;}
        const bool ok=effect([&]{return driver_.rotateOpen();});
        if(epoch!=epoch_ || state_!=State::Opening){compensateNeutral();return;}
        if(!ok)fault(Reason::Output,s.now_ms,true);
    }
    void close(const Sample& s){
        ++epoch_;state_=State::Closing;closing_at_=s.now_ms;close_started_=true;
        const auto epoch=epoch_;const bool ok=effect([&]{return driver_.rotateClose();});
        if(epoch!=epoch_ || state_!=State::Closing){compensateNeutral();return;}
        if(!ok)fault(Reason::Output,s.now_ms,true);
    }
 public:
    Controller(Driver& driver,Journal& journal):driver_(driver),journal_(journal){}
    void boot(bool initialized,bool pending,uint32_t last_id){
        if(in_effect_)return;
        ++epoch_;state_=State::Disarmed;reason_=Reason::None;configured_=false;locked_=!initialized||pending;
        have_clock_=have_sample_=baseline_valid_=actual_valid_=left_closed_=open_confirmed_=close_started_=false;
        highwater_=last_id;id_=0;arms_=0;resetWindow();
        if(!effect([&]{return driver_.boot();})){state_=State::Fault;reason_=Reason::Output;locked_=true;}
    }
    bool configure(Settings s){
        if(in_effect_||state_!=State::Disarmed||locked_||configured_||arms_||!s.valid())return false;
        if(!driver_.configure(s.pulses))return false;
        settings_=s;configured_=true;return true;
    }
    Reason arm(const Sample& s,const Position& p,Mode mode,bool owner_approved){
        if(in_effect_)return Reason::Busy;
        if(locked_)return Reason::Inspection;
        if(!configured_)return Reason::Config;
        if(mode==Mode::Automatic && settings_.supervised_early_close_trial)return Reason::Config;
        if(!owner_approved)return Reason::Approval;
        if((state_!=State::Disarmed&&state_!=State::Complete)||arms_>=3)return Reason::Busy;
        if(!clock(s.now_ms))return Reason::Clock;
        const auto ok=sample(s,true);if(ok!=Reason::None)return ok;
        if(p.available && !positionUsable(s,p))return Reason::Position;
        if(mode==Mode::Automatic && (!positionUsable(s,p)||!p.closed))return Reason::Position;
        mode_=mode;generation_=s.generation;state_=State::Armed;phase_at_=lease_at_=s.now_ms;++arms_;return Reason::None;
    }
    Reason start(uint32_t id,const Sample& s){
        if(in_effect_)return Reason::Busy;
        if(!id||id>0xffffffu||id<=highwater_)return Reason::Duplicate;
        if(state_!=State::Armed)return Reason::Busy;
        if(!clock(s.now_ms)){fault(Reason::Clock,last_now_,true);return reason_;}
        if(s.now_ms-lease_at_>=1500){fault(Reason::Lease,s.now_ms,true);return reason_;}
        if(s.now_ms-phase_at_>=2000){fault(Reason::Timeout,s.now_ms,true);return reason_;}
        const auto ok=sample(s,true);if(ok!=Reason::None || s.generation!=generation_){fault(ok==Reason::None?Reason::Calibration:ok,s.now_ms,true);return reason_;}
        highwater_=id;id_=id;locked_=true;state_=State::Baseline;started_at_=phase_at_=lease_at_=s.now_ms;
        baseline_valid_=actual_valid_=left_closed_=open_confirmed_=close_started_=false;resetWindow();
        const auto epoch=epoch_;const bool saved=effect([&]{return journal_.write(true,id);});
        if(epoch!=epoch_ || state_!=State::Baseline){compensateNeutral();return reason_;}
        if(!saved){fault(Reason::Persistence,s.now_ms,true);return reason_;}
        return Reason::None;
    }
    void heartbeat(uint32_t now){
        if(in_effect_||terminal()||faultState())return;
        if(!clock(now)){fault(Reason::Clock,last_now_,true);return;}
        lease_at_=now;
    }
    void stop(uint32_t now){
        if(state_==State::FaultNeutral || state_==State::Fault)return;
        reason_=Reason::Stopped;locked_=true;actual_valid_=false;neutral(now,true);
    }
    void tick(const Sample& s,const Position& p){
        if(in_effect_||terminal())return;
        if(!clock(s.now_ms)){
            reason_=Reason::Clock;locked_=true;++epoch_;state_=State::Fault;
            effect([&]{return driver_.neutral();});effect([&]{return driver_.detach();});return;
        }
        if(state_==State::FaultClosing){
            if(s.now_ms-started_at_>=settings_.total_timeout_ms || closedNow(s,p) || s.now_ms-closing_at_>=settings_.closing_ms)neutral(s.now_ms,true);
            return;
        }
        if(state_==State::FaultNeutral){
            if(s.now_ms-phase_at_<settings_.neutral_hold_ms)return;
            const auto epoch=epoch_;
            if(settings_.detach_after_neutral){
                const bool off=effect([&]{return driver_.detach();});
                if(epoch!=epoch_){compensateNeutral();return;}
                if(!off){reason_=Reason::Output;state_=State::Fault;locked_=true;return;}
            }
            state_=State::Fault;return;
        }
        if(s.now_ms-lease_at_>=1500){fault(Reason::Lease,s.now_ms,true);return;}
        if(state_==State::Armed){if(s.now_ms-phase_at_>=2000)fault(Reason::Timeout,s.now_ms,true);return;}
        if(s.now_ms-started_at_>=settings_.total_timeout_ms){fault(Reason::Timeout,s.now_ms,true);return;}
        const auto ok=sample(s,false);
        if(ok!=Reason::None || s.generation!=generation_){fault(ok==Reason::None?Reason::Calibration:ok,s.now_ms);return;}
        if(p.available && !positionUsable(s,p)){fault(Reason::Position,s.now_ms,true);return;}
        if(mode_==Mode::Automatic && !positionUsable(s,p)){fault(Reason::Position,s.now_ms,true);return;}
        if(baseline_valid_){
            latest_=s.grams-baseline_;
            if(latest_>40.f){fault(Reason::Overshoot,s.now_ms);return;}
            if(latest_<-settings_.stable_range_g){fault(Reason::Weight,s.now_ms,true);return;}
        }
        if(state_==State::NeutralHold){
            if(mode_==Mode::Automatic && !closedNow(s,p)){fault(Reason::Position,s.now_ms,true);return;}
            if(s.now_ms-phase_at_<settings_.neutral_hold_ms)return;
            const auto epoch=epoch_;
            if(settings_.detach_after_neutral){
                const bool off=effect([&]{return driver_.detach();});
                if(epoch!=epoch_){compensateNeutral();return;}
                if(!off){reason_=Reason::Output;state_=State::Fault;locked_=true;return;}
            }
            state_=State::Settling;phase_at_=s.now_ms;resetWindow();return;
        }
        if(state_==State::Baseline){
            if(mode_==Mode::Automatic && !p.closed){fault(Reason::Position,s.now_ms,true);return;}
            if(s.now_ms-phase_at_>=settings_.baseline_timeout_ms){fault(Reason::Timeout,s.now_ms,true);return;}
            add(s);float mean=0;if(stable(mean)){baseline_=mean;baseline_valid_=true;latest_=0;open(s);}return;
        }
        if(positionUsable(s,p) && static_cast<uint32_t>(p.observed_ms-opening_at_)<=0x7fffffffu){
            if(!p.closed)left_closed_=true;
            if(p.opened)open_confirmed_=true;
        }
        if(state_==State::Opening || state_==State::WaitingMass){
            if(new_sample_ && latest_>=35.f-settings_.closing_lead_g){close(s);return;}
            if(new_sample_ && latest_-last_progress_mass_>=settings_.stable_range_g/4){last_progress_=s.now_ms;last_progress_mass_=latest_;}
            if(s.now_ms-last_progress_>=settings_.no_progress_ms){fault(Reason::NoProgress,s.now_ms);return;}
            if(state_==State::Opening && (open_confirmed_ || s.now_ms-opening_at_>=settings_.opening_ms)){
                if(mode_==Mode::Automatic && !open_confirmed_){fault(Reason::Position,s.now_ms,true);return;}
                state_=State::WaitingMass;const auto epoch=epoch_;const bool neutral_ok=effect([&]{return driver_.neutral();});
                if(epoch!=epoch_){compensateNeutral();return;}if(!neutral_ok)fault(Reason::Output,s.now_ms,true);
            }return;
        }
        if(state_==State::Closing){
            if(closedNow(s,p)){neutral(s.now_ms,false);return;}
            if(s.now_ms-closing_at_>=settings_.closing_ms){
                if(mode_==Mode::Automatic){fault(Reason::Position,s.now_ms,true);return;}
                neutral(s.now_ms,false);
            }return;
        }
        if(state_==State::Settling){
            if(mode_==Mode::Automatic && !closedNow(s,p)){fault(Reason::Position,s.now_ms,true);return;}
            if(s.now_ms-phase_at_>=settings_.settle_timeout_ms){fault(Reason::Timeout,s.now_ms,true);return;}
            if(s.now_ms-phase_at_<settings_.settle_ms)return;
            add(s);float mean=0;if(!stable(mean))return;
            actual_=mean-baseline_;actual_valid_=true;
            if(actual_<30.f){fault(Reason::UnderTarget,s.now_ms,true);return;}
            if(actual_>40.f){fault(Reason::Overshoot,s.now_ms,true);return;}
            if(mode_==Mode::Supervised){state_=State::AwaitingOwner;locked_=true;return;}
            if(!left_closed_ || !open_confirmed_ || !closedNow(s,p)){fault(Reason::Position,s.now_ms,true);return;}
            const auto epoch=epoch_;const bool saved=effect([&]{return journal_.write(false,id_);});
            if(epoch!=epoch_ || state_!=State::Settling){
                locked_=true;const bool restored=effect([&]{return journal_.write(true,id_);});if(!restored)reason_=Reason::Persistence;compensateNeutral();return;
            }
            if(!saved){fault(Reason::Persistence,s.now_ms,true);return;}
            locked_=false;state_=State::Complete;
        }
    }
    State state()const{return state_;}Reason reason()const{return reason_;}
    uint32_t id()const{return id_;}uint32_t highwater()const{return highwater_;}
    bool inspectionRequired()const{return locked_;}bool baselineValid()const{return baseline_valid_;}
    float closeTriggerGrams()const{return 35.f-settings_.closing_lead_g;}
    float baselineGrams()const{return baseline_valid_?baseline_:NAN;}
    float latestGrams()const{return baseline_valid_?latest_:NAN;}
    float actualGrams()const{return actual_valid_?actual_:NAN;}
};
}

#include <cstring>
namespace forcat_continuous {
class HxAdapter {
    m4::ScaleCalibration previous_{};bool have_=false,exhausted_=false;uint32_t generation_=0;
 public:
    Sample read(const m4::Hx711& hx,uint32_t now){
        const auto& cal=hx.calibration;
        const bool changed=!have_ || previous_.tared!=cal.tared || previous_.calibrated!=cal.calibrated ||
            std::memcmp(&previous_.tare_counts,&cal.tare_counts,sizeof(double)) ||
            std::memcmp(&previous_.grams_per_count,&cal.grams_per_count,sizeof(double));
        if(changed){if(generation_==UINT32_MAX)exhausted_=true;else ++generation_;previous_=cal;have_=true;}
        return {now,hx.grams.sampled_at_ms,exhausted_?0:generation_,
            hx.status.health==m4::Health::HEALTHY && hx.grams.valid,cal.valid()&&!exhausted_,hx.grams.fresh,
            hx.grams.valid?hx.grams.value:0};
    }
};
}

namespace m4 {
class MedianFilter {
 public:
  bool add(float value) {
    if (!std::isfinite(value)) return false;
    values_[cursor_] = value; cursor_ = (cursor_ + 1) % 5;
    if (count_ < 5) ++count_;
    return true;
  }
  void clear() { count_ = cursor_ = 0; }
  bool ready() const { return count_ > 0; }
  float median() const {
    if (!count_) return 0;
    float sorted[5];
    for (uint8_t i = 0; i < count_; ++i) sorted[i] = values_[i];
    for (uint8_t i = 1; i < count_; ++i) {
      float value = sorted[i]; int j = i-1;
      while (j >= 0 && sorted[j] > value) { sorted[j+1] = sorted[j]; --j; }
      sorted[j+1] = value;
    }
    return sorted[count_/2];
  }
 private:
  float values_[5]{};
  uint8_t count_ = 0, cursor_ = 0;
};
struct UltrasonicConfig {
  Pin trigger{}, echo{};
  float minimum_cm = 0, maximum_cm = 0;
  uint32_t echo_timeout_us = 30000;
  float sound_cm_per_us = 0.0343f;
};
enum class EchoPhase : uint8_t { IDLE, PULSE_LOW, PULSE_HIGH, WAIT_RISE, WAIT_FALL };
class Ultrasonic {
 public:
  explicit Ultrasonic(PinIO& io) : io_(io) {}
  bool begin(UltrasonicConfig config) {
    active_ = false; phase_ = EchoPhase::IDLE; raw = filtered = {}; config_ = config;
    timeout_count_ = 0;
    if (!outputValid(io_, config.trigger) || !inputValid(io_, config.echo) ||
        config.trigger.number == config.echo.number || !std::isfinite(config.minimum_cm) ||
        !std::isfinite(config.maximum_cm) || config.minimum_cm <= 0 || config.maximum_cm <= config.minimum_cm ||
        !std::isfinite(config.sound_cm_per_us) || config.sound_cm_per_us <= 0 ||
        config.echo_timeout_us < 100 || config.echo_timeout_us > 100000) {
      status = {}; return false;
    }
    io_.output(config.trigger.number); io_.write(config.trigger.number, false);
    io_.input(config.echo.number, Pull::NONE);
    active_ = true; phase_ = EchoPhase::IDLE; filter_.clear();
    status = {Health::INITIALIZING, Reason::NONE}; return true;
  }
  bool trigger(uint32_t now_us) {
    if (!active_ || phase_ != EchoPhase::IDLE) return false;
    raw.fresh = filtered.fresh = false;
    if (io_.read(config_.echo.number)) { fail(Reason::INVALID_DATA); return false; }
    io_.write(config_.trigger.number, false); phase_ = EchoPhase::PULSE_LOW;
    began_ = phase_at_ = now_us; return true;
  }
  void poll(uint32_t now_us, uint32_t now_ms) {
    raw.fresh = filtered.fresh = false;
    if (!active_ || phase_ == EchoPhase::IDLE) return;
    if (static_cast<uint32_t>(now_us - began_) >= config_.echo_timeout_us) { fail(Reason::TIMEOUT); return; }
    switch (phase_) {
      case EchoPhase::PULSE_LOW:
        if (static_cast<uint32_t>(now_us - phase_at_) >= 2) {
          io_.write(config_.trigger.number, true); phase_ = EchoPhase::PULSE_HIGH; phase_at_ = now_us;
        }
        break;
      case EchoPhase::PULSE_HIGH:
        if (static_cast<uint32_t>(now_us - phase_at_) >= 10) {
          io_.write(config_.trigger.number, false); phase_ = EchoPhase::WAIT_RISE;
        }
        break;
      case EchoPhase::WAIT_RISE:
        if (io_.read(config_.echo.number)) { rise_at_ = now_us; phase_ = EchoPhase::WAIT_FALL; }
        break;
      case EchoPhase::WAIT_FALL:
        if (!io_.read(config_.echo.number)) {
          const auto width = static_cast<uint32_t>(now_us - rise_at_);
          const float distance = static_cast<float>(width) * config_.sound_cm_per_us / 2;
          phase_ = EchoPhase::IDLE;
          if (!width || !std::isfinite(distance) || distance < config_.minimum_cm || distance > config_.maximum_cm) {
            fail(Reason::RANGE_INVALID); return;
          }
          raw = {true, distance, now_ms, true}; filter_.add(distance);
          filtered = {true, filter_.median(), now_ms, true}; status = {Health::HEALTHY, Reason::NONE};
        }
        break;
      default: break;
    }
  }
  const UltrasonicConfig& config() const { return config_; }
  bool busy() const { return phase_ != EchoPhase::IDLE; }
  uint32_t timeoutCount() const { return timeout_count_; }
  Status status{};
  Reading<float> raw{}, filtered{};
 private:
  void fail(Reason reason) {
    if (reason == Reason::TIMEOUT && timeout_count_ != UINT32_MAX) ++timeout_count_;
    if (active_) io_.write(config_.trigger.number, false);
    raw = filtered = {}; filter_.clear(); phase_ = EchoPhase::IDLE;
    status = {reason == Reason::TIMEOUT ? Health::NOT_CONNECTED : Health::FAULT, reason};
  }
  PinIO& io_;
  UltrasonicConfig config_{};
  MedianFilter filter_{};
  EchoPhase phase_ = EchoPhase::IDLE;
  uint32_t began_ = 0, phase_at_ = 0, rise_at_ = 0;
  bool active_ = false;
  uint32_t timeout_count_ = 0;
};
class LevelSensor {
 public:
  explicit LevelSensor(PinIO& io) : distance(io) {}
  void update() {
    percent = calibration.percent(distance.filtered, distance.config().minimum_cm, distance.config().maximum_cm);
    status = distance.status;
    if (distance.status.health == Health::HEALTHY && !calibration.valid())
      status = {Health::NOT_CALIBRATED, Reason::NOT_CALIBRATED};
    else if (distance.status.health == Health::HEALTHY && !percent.valid)
      status = {Health::FAULT, Reason::RANGE_INVALID};
  }
  Ultrasonic distance;
  LevelCalibration calibration{};
  Reading<float> percent{};
  Status status{};
};
}

#include <cmath>
#include <cstdint>
namespace cat_test {
class Gate {
    uint32_t ai_at_=0,near_at_=0,source_seq_=0;unsigned near_count_=0;
    bool cat_=false,visited_=false;
 public:
    bool ai(uint32_t now,uint32_t seq,uint32_t age,uint32_t transport_age,unsigned confidence,bool cat){
        if(!seq || seq<=source_seq_ || age>750 || transport_age>750 || age+transport_age>750 || confidence>1000)return false;
        source_seq_=seq;ai_at_=now-age-transport_age;cat_=cat&&confidence>=800;
        if(!cat_)near_count_=0;
        return true;
    }
    bool catFresh(uint32_t now)const{return cat_&&uint32_t(now-ai_at_)<=750;}
    void near(uint32_t now,bool valid,float cm){
        if(!catFresh(now)||!valid||!std::isfinite(cm)||cm<2||cm>20){near_count_=0;return;}
        if(near_count_&&uint32_t(now-near_at_)>250)near_count_=0;
        near_at_=now;if(near_count_<3)++near_count_;
    }
    bool ready(uint32_t now)const{return !visited_&&catFresh(now)&&near_count_>=3&&uint32_t(now-near_at_)<=200;}
    void consume(){visited_=true;}
    bool visited()const{return visited_;}
    void inspected(){visited_=false;near_count_=0;cat_=false;}
};
inline uint16_t crc(const char* p,unsigned n){uint16_t c=0xffff;for(unsigned i=0;i<n;++i){c^=uint16_t(uint8_t(p[i]))<<8;for(unsigned j=0;j<8;++j)c=c&0x8000?uint16_t((c<<1)^0x1021):uint16_t(c<<1);}return c;}
}

#include <cstring>
namespace cat_test {
inline bool number(const char* s,uint32_t& v){
    if(!s||!*s)return false;v=0;
    for(;*s;++s){if(*s<'0'||*s>'9'||v>(UINT32_MAX-unsigned(*s-'0'))/10)return false;v=v*10+unsigned(*s-'0');}return true;
}
struct Packet {char* op=nullptr;char* args[5]{};unsigned count=0;uint32_t seq=0,echo=0;};
class Receiver {
    uint32_t last_=0;
 public:
    uint32_t last()const{return last_;}
    bool parse(char* line,uint32_t boot,uint32_t now,Packet& p){
        p={};char* star=std::strchr(line,'*');if(!star||std::strlen(star+1)!=4)return false;
        uint16_t expected=0;for(char* c=star+1;*c;++c){unsigned n;if(*c>='0'&&*c<='9')n=*c-'0';else if(*c>='A'&&*c<='F')n=*c-'A'+10;else return false;expected=uint16_t(expected*16+n);}
        if(crc(line,unsigned(star-line))!=expected)return false;*star=0;
        char* words[10]{};unsigned n=0;char* save=nullptr;
        for(char* s=strtok_r(line," ",&save);s;s=strtok_r(nullptr," ",&save)){if(n==10)return false;words[n++]=s;}
        uint32_t b=0;if(n<5||std::strcmp(words[0],"FC1")||!number(words[1],b)||b!=boot||
            !number(words[2],p.seq)||!p.seq||p.seq<=last_||!number(words[3],p.echo)||uint32_t(now-p.echo)>750)return false;
        p.op=words[4];p.count=n-5;for(unsigned i=0;i<p.count;++i)p.args[i]=words[i+5];last_=p.seq;return true;
    }
};
}

namespace user_settings {
inline forcat_continuous::Settings settings(){
    forcat_continuous::Settings s;
    s.pulses.safe_min_us=0; s.pulses.safe_max_us=0;
    s.pulses.neutral_us=0; s.pulses.neutral_low_us=0; s.pulses.neutral_high_us=0;
    s.pulses.open_rotation_us=0; s.pulses.close_rotation_us=0;
    s.pulses.continuous_type_verified=false;
    s.pulses.neutral_verified=false; s.pulses.directions_verified=false;
    s.opening_ms=0; s.closing_ms=0; s.travel_timing_verified=false;
    s.neutral_hold_ms=100; s.settle_ms=1000; s.stable_span_ms=200;
    s.baseline_timeout_ms=5000; s.settle_timeout_ms=6000;
    s.no_progress_ms=3000; s.total_timeout_ms=20000; s.stable_range_g=1;
    s.closing_lead_g=10;
    s.supervised_early_close_trial=true;
    s.detach_after_neutral=false;
    s.supervised_bounded_fault_close=false;
    return s;
}
constexpr bool exact_calibration_import_reviewed=false;
constexpr double tare_counts=0, grams_per_count=0;
constexpr const char* calibration_provenance="UNSET";
constexpr bool hc_sr04_wiring_reviewed=false;
constexpr float hc_min_cm=2, hc_max_cm=400;
}

#include <Arduino.h>
#include <Preferences.h>
using namespace forcat_continuous;
namespace {
class PersistentJournal:public Journal {
 public:
    bool initialized=false,pending=false,corrupt=false;uint32_t last=0;
    void load(){
        Preferences p;if(!p.begin("fc-cr-test",true))return;
        if(p.isKey("journal")){
            uint8_t b[12]{};
            if(p.getBytesLength("journal")!=12||p.getBytes("journal",b,12)!=12||b[0]!='C'||b[1]!='R'||b[2]!=1||b[3]>1||
                m4::calibration_record::get(b+10,2)!=uart_v1::crc16(b,10))corrupt=true;
            else {last=uint32_t(m4::calibration_record::get(b+4,4));pending=b[3];initialized=last<=0xffffffu;if(!initialized)corrupt=true;}
        }p.end();
    }
    bool write(bool value,uint32_t id)override{
        if(corrupt||id<last||id>0xffffffu)return false;
        uint8_t b[12]{'C','R',1,uint8_t(value)};m4::calibration_record::put(b+4,id,4);
        m4::calibration_record::put(b+10,uart_v1::crc16(b,10),2);
        Preferences p;if(!p.begin("fc-cr-test",false))return false;
        bool ok=p.putBytes("journal",b,12)==12;p.end();
        if(ok){initialized=true;pending=value;last=id;}return ok;
    }
};
m4::ArduinoPins pins;m4::Hx711 hx(pins);m4::Ultrasonic hc(pins);
m4::LedcServoOutput pwm;Driver motor(pwm);PersistentJournal journal;Controller control(motor,journal);
HxAdapter adapter;cat_test::Gate gate;cat_test::Receiver receiver;
uint32_t boot_id=0,last_hb=0,permit_at=0,last_ping=0,last_status=0;
bool configured=false,inspected=false,permit=false,hc_active=false,have_hb=false;
const char* calibration_source="NOT_CALIBRATED";
const char* calibration_load="NOT_ATTEMPTED";
char food='?';char rx[384]{};size_t rxn=0;bool discard=false;
bool quiet();
void stop();
void reply(uint32_t,bool,const char*);
void number(float);
void telemetry(const Sample&);
void command(char*,const Sample&);
bool quiet(){const auto s=control.state();return s==State::Disarmed||s==State::Fault||s==State::AwaitingOwner;}
void stop(){permit=false;control.stop(millis());}
void reply(uint32_t seq,bool ok,const char* detail){protocolSerial().printf("{\"type\":\"ack\",\"boot\":%lu,\"seq\":%lu,\"ok\":%s,\"detail\":\"%s\"}\n",(unsigned long)boot_id,(unsigned long)seq,ok?"true":"false",detail);}
void number(float v){if(std::isfinite(v))protocolSerial().printf("%.5f",double(v));else protocolSerial().print("null");}
void telemetry(const Sample& s){
    auto& out=protocolSerial();
    out.printf("{\"type\":\"status\",\"schema\":\"fc-cr-test-1\",\"boot\":%lu,\"ms\":%lu,\"seq\":%lu,\"state\":\"%s\",\"reason\":%u,\"configured\":%s,\"inspected\":%s,\"permit\":%s,\"pending\":%s,\"dose_id\":%lu,\"food\":\"%c\",\"cal_generation\":%lu,\"healthy\":%s,\"calibrated\":%s,\"sample_ms\":%lu,\"grams\":",
        (unsigned long)boot_id,(unsigned long)s.now_ms,(unsigned long)receiver.last(),name(control.state()),unsigned(control.reason()),configured?"true":"false",inspected?"true":"false",permit?"true":"false",journal.pending?"true":"false",(unsigned long)control.id(),food,(unsigned long)s.generation,s.healthy?"true":"false",s.calibrated?"true":"false",(unsigned long)s.sample_at_ms);
    number(s.healthy?s.grams:NAN);out.print(",\"baseline_g\":");number(control.baselineGrams());out.print(",\"dose_g\":");number(control.actualGrams());
    out.print(",\"near_cm\":");number(hc.raw.valid&&uint32_t(s.now_ms-hc.raw.sampled_at_ms)<=250?hc.raw.value:NAN);
    out.printf(",\"cat_fresh\":%s,\"close_trigger_g\":%.3f,\"calibration_source\":\"%s\",\"tare_counts\":",gate.catFresh(s.now_ms)?"true":"false",double(35-user_settings::settings().closing_lead_g),calibration_source);
    if(hx.calibration.valid())out.printf("%.17g,\"grams_per_count\":%.17g",hx.calibration.tare_counts,hx.calibration.grams_per_count);
    else out.print("null,\"grams_per_count\":null");
    out.printf(",\"hx_health\":\"%s\",\"hx_reason\":\"%s\",\"calibration_load\":\"%s\",\"raw_valid\":%s,\"raw\":",m4::name(hx.status.health),m4::name(hx.status.reason),calibration_load,hx.raw.valid?"true":"false");
    if(hx.raw.valid)out.printf("%ld",(long)hx.raw.value);else out.print("null");
    out.printf(",\"raw_ms\":%lu,\"median_raw_valid\":%s",(unsigned long)hx.raw.sampled_at_ms,hx.median_raw.valid?"true":"false");
    out.print(",\"physical_closed\":null,\"automatic\":false}\n");
}
void command(char* line,const Sample& s){
    if(!std::strcmp(line,"hx")||!std::strcmp(line,"status")){telemetry(s);return;}
    if(!std::strcmp(line,"STOP")){stop();reply(0,true,"NEUTRAL_REQUESTED_CLOSURE_UNKNOWN");return;}
    cat_test::Packet p;if(!receiver.parse(line,boot_id,s.now_ms,p)){stop();reply(0,false,"BAD_FRAME_STOPPED");return;}
    bool ok=false;const char* detail="REJECTED";
    if(!std::strcmp(p.op,"HB")&&p.count==0){have_hb=true;last_hb=s.now_ms;control.heartbeat(s.now_ms);ok=true;}
    else if(!std::strcmp(p.op,"STOP")&&p.count==0){stop();ok=true;detail="NEUTRAL_REQUESTED_CLOSURE_UNKNOWN";}
    else if(!std::strcmp(p.op,"CAT")&&p.count==4){
        uint32_t seq,age,confidence,cat;
        ok=cat_test::number(p.args[0],seq)&&cat_test::number(p.args[1],age)&&cat_test::number(p.args[2],confidence)&&cat_test::number(p.args[3],cat)&&cat<=1&&
            gate.ai(s.now_ms,seq,age,s.now_ms-p.echo,confidence,cat);
    }else if(!std::strcmp(p.op,"INSPECT")&&p.count==1&&!std::strcmp(p.args[0],"CLOSED")&&quiet()){
        permit=false;configured=false;inspected=false;
        if(journal.write(false,journal.last)){
            control.boot(true,false,journal.last);gate.inspected();inspected=true;
            configured=control.configure(user_settings::settings());ok=true;
            detail=configured?"OWNER_INSPECTION_RECORDED":"INSPECTION_RECORDED_SETTINGS_INVALID";
        }else detail="JOURNAL_WRITE_FAILED";
    }else if(!std::strcmp(p.op,"ARM")&&p.count==1&&std::strlen(p.args[0])==1&&(p.args[0][0]=='A'||p.args[0][0]=='B')){
        ok=inspected&&configured&&hc_active&&!journal.pending&&!permit&&control.state()==State::Disarmed&&s.healthy&&s.calibrated&&have_hb&&s.now_ms-last_hb<1000;
        if(ok){food=p.args[0][0];permit=true;permit_at=s.now_ms;detail="PERMIT_30_SECONDS_NO_MOTION";}
    }
    reply(p.seq,ok,detail);
}
}
void setup(){
    protocolSerial().begin(115200);boot_id=esp_random();if(!boot_id)boot_id=1;
    journal.load();control.boot(journal.initialized,journal.pending,journal.last);
    hx.begin({{4,true},{5,true},500},millis());
    m4::CalibrationRecord record;m4::NvsCalibration nvs;
    const auto loaded=nvs.load(record);
    calibration_load=loaded==m4::CalibrationLoad::LOADED?"LOADED":loaded==m4::CalibrationLoad::INVALID?"INVALID":"MISSING";
    if(loaded==m4::CalibrationLoad::LOADED&&record.hx711.valid()){hx.applyCalibration(record.hx711);calibration_source="NVS_SENSORS_V2";}
    else if(user_settings::exact_calibration_import_reviewed&&std::strcmp(user_settings::calibration_provenance,"UNSET")&&std::strlen(user_settings::calibration_provenance)){
        m4::ScaleCalibration c;c.tared=c.calibrated=true;c.tare_counts=user_settings::tare_counts;c.grams_per_count=user_settings::grams_per_count;
        if(c.valid()){hx.applyCalibration(c);calibration_source="EXACT_REVIEWED_IMPORT";}
    }
    if(user_settings::hc_sr04_wiring_reviewed)hc_active=hc.begin({{12,true},{13,true},user_settings::hc_min_cm,user_settings::hc_max_cm,30000,0.0343f});
}
void loop(){
    const uint32_t now=millis();hc.poll(micros(),now);
    if(hc.raw.fresh)gate.near(now,hc.raw.valid,hc.raw.value);
    if(!hc.busy())hx.poll(now);
    const Sample s=adapter.read(hx,now);control.tick(s,Position{});
    if(permit&&(uint32_t(now-permit_at)>=30000||!have_hb||uint32_t(now-last_hb)>=1500))permit=false;
    if(!hc.busy()){
        unsigned budget=128;
        while(budget--&&protocolSerial().available()){
            const int value=protocolSerial().read();if(value<0)break;const char c=char(value);
            if(c=='\r')continue;
            if(c=='\n'){if(!discard&&rxn){rx[rxn]=0;command(rx,s);}rxn=0;discard=false;}
            else if(!discard){if(c<32||c>126||rxn+1>=sizeof(rx)){discard=true;rxn=0;stop();}else rx[rxn++]=c;}
        }
        if(permit&&gate.ready(now)&&s.fresh&&s.healthy){
            permit=false;gate.consume();
            if(control.arm(s,Position{},Mode::Supervised,true)==Reason::None){
                control.start(journal.last+1,s);inspected=false;
            }
        }
        if(now-last_status>=250){last_status=now;telemetry(s);}
        protocolSerial().drain();if(protocolSerial().overflowed())stop();
        if(hc_active&&gate.catFresh(now)&&now-last_ping>=70){last_ping=now;hc.trigger(micros());}
    }
}
