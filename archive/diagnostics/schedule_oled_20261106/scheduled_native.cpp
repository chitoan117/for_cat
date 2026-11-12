
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#undef isfinite
namespace std { using ::strtol; inline bool isfinite(float v){return __builtin_isfinite(v);} inline float fabs(float v){return __builtin_fabsf(v);} }
void operator delete(void* p) noexcept { free(p); }
void operator delete(void* p, size_t) noexcept { free(p); }
constexpr int LOW=0,OUTPUT=1,PIN_CLOSE_LIMIT=47;
unsigned gpio_reads=0, attaches=0, detaches=0, writes=0;
bool hw_attached=false, fail_write=false;
uint32_t duty=0;
bool ledcAttach(int pin,int hz,int bits){assert(pin==6&&hz==50&&bits==14);++attaches;hw_attached=true;return true;}
bool ledcDetach(int pin){assert(pin==6);++detaches;hw_attached=false;return true;}
bool ledcWrite(int pin,uint32_t value){assert(pin==6);++writes;if(fail_write)return false;duty=value;return true;}
void digitalWrite(int,int){}
void pinMode(int,int){}
int digitalRead(int){++gpio_reads;return LOW;}
#include <string.h>
#include <stdarg.h>
char uart_log[16000];size_t uart_n=0;
struct Serial { void printf(const char* fmt,...){va_list args;va_start(args,fmt);uart_n+=vsnprintf(uart_log+uart_n,sizeof(uart_log)-uart_n,fmt,args);va_end(args);} void print(const char* s){printf("%s",s);} } serial;

Serial& protocolSerial(){return serial;}
namespace servo_bench {
constexpr int pin=6;
constexpr uint16_t electrical_min_us=1000,electrical_max_us=2000;
class Output { public: virtual ~Output()=default; virtual bool start(uint16_t)=0; virtual bool write(uint16_t)=0; virtual bool off()=0; };
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
LedcServoOutput pwm;

enum class FeedStage { IDLE, FAULT, OPENING, WAIT_WEIGHT, WAIT_HX, WAIT_CAT, CLOSING, DIAG_OPEN, DIAG_CLOSE, DONE };
enum class BenchCal { Idle, Tare };
BenchCal bench_cal=BenchCal::Idle;
constexpr bool USE_CLOSE_LIMIT_SWITCH=false;
constexpr uint16_t SERVO_OPEN_US = 1350; // Faster OPEN trial; needs physical travel verification.
constexpr uint16_t SERVO_CLOSE_US = 1600; // UNO-tested: close LEFT.
constexpr uint16_t SERVO_NEUTRAL_US = 1500;
constexpr uint32_t MAX_SERVO_ACTIVE_MS = 5000;
constexpr float CLOSE_AT_G = 35.0f;  // Target: close on the first measured added-mass sample >=35g.
constexpr float MAX_NORMAL_G = 40.0f;
constexpr float CAT_MIN_CM = 2.0f;
constexpr float CAT_MAX_CM = 30.0f;
constexpr uint32_t CAT_WAIT_TIMEOUT_MS = 30000;
constexpr uint32_t HX_WAIT_TIMEOUT_MS = 25000;
constexpr uint32_t WEIGHT_WAIT_TIMEOUT_MS = 25000;
uint16_t open_ms = 900; // Shorter OPEN for the faster pulse; initial physical trial.
uint16_t close_ms = 1450; // Owner requested a small additional closing travel (owner-supervised relative travel calibration).

FeedStage feed_stage=FeedStage::IDLE;
bool manual_feed_active=false,close_on_weight=false,limit_closed=true,physical_closed_verified=false;
bool cat_inspect_required=false,servo_armed=false,dog_running=false,demo_exited=false;
bool meal_logged=false,meal_start_locked=false;
float last_delta_g=35,meal_starting_g=0,meal_remaining_g=0,meal_consumed_g=0;
float baseline_g=0;
struct Measurement { bool valid=false; float value=0; };
struct Hx { Measurement signed_grams; } hx;
bool scale_ready=false; float scale_value=0; uint32_t scale_stamp=1;
bool benchScaleSample(uint32_t,float& grams,uint32_t& stamp){if(!scale_ready)return false;grams=scale_value;stamp=scale_stamp;return true;}
struct Sample { uint32_t now_ms=0; };
struct RawDistance { bool valid=false,fresh=false; uint32_t sampled_at_ms=0; float value=0; };
struct Hc { RawDistance raw; } hc;
void buzzerStop(){dog_running=false;}
float meal_plateau_ref_g=0,meal_stable_ref_g=0;
const char* meal_preference="NONE";
uint32_t meal_plateau_since=0,meal_closed_at=0,meal_stable_since=0;
uint32_t phase_at=0,started_at=0,servo_move_for_ms=0,last_scale_ms=0,last_hc_ms=0;
unsigned cat_hits=0;
char current_food='A';
enum class TimedGateStop : uint8_t { UNKNOWN, OPEN, CLOSED };
TimedGateStop timed_gate_stop=TimedGateStop::UNKNOWN;
bool busy() {
  return feed_stage == FeedStage::WAIT_HX
    || feed_stage == FeedStage::WAIT_CAT
    || feed_stage == FeedStage::OPENING
    || feed_stage == FeedStage::WAIT_WEIGHT
    || feed_stage == FeedStage::CLOSING
    || feed_stage == FeedStage::DIAG_OPEN
    || feed_stage == FeedStage::DIAG_CLOSE;
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
  protocolSerial().printf("CAT 3x <=30cm CONFIRMED. SERVO OPEN %u ms, PWM %u us.\n",
     (unsigned)open_ms, (unsigned)SERVO_OPEN_US);
  return true;
}
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
  protocolSerial().print("CAT REQUEST: healthy ZERO baseline, waiting REAL HC1 distance 2..30cm x3.\n");
  return true;
}
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
void diagServo(bool opening, uint32_t now) {
  if (!servo_armed || cat_inspect_required) {
    protocolSerial().print("SERVO TEST BLOCKED: servo_arm / inspect_ok required.\n");
    return;
  }
  manualServoMove(opening, opening ? open_ms : close_ms, now);
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
void diagTick(uint32_t now) { Sample s; s.now_ms=now;
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
}
void openingTick(uint32_t now) { Sample s; s.now_ms=now;
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
}
void closingTick(uint32_t now) { Sample s; s.now_ms=now;
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
void weightTick(uint32_t now) { Sample s; s.now_ms=now;
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
}
void catTick(uint32_t now) { Sample s; s.now_ms=now;
  if (feed_stage == FeedStage::WAIT_CAT) {
    if (uint32_t(now - phase_at) >= CAT_WAIT_TIMEOUT_MS) {
      cancel("HC1 NO 3 CONSECUTIVE VALID READS", true);
      return;
    }
    // Read new HC1 RAW samples, not stale or smoothed old values.
    if (!hc.raw.valid) {
      cat_hits = 0;
      return;
    }
    if (hc.raw.fresh && hc.raw.sampled_at_ms != last_hc_ms) {
      if (last_hc_ms && uint32_t(hc.raw.sampled_at_ms - last_hc_ms) > 800u)
        cat_hits = 0;
      last_hc_ms = hc.raw.sampled_at_ms;
      if (!hc.raw.valid) {
        cat_hits = 0;
        return;
      }
      float distance = hc.raw.value;
      if (std::isfinite(distance) && distance >= CAT_MIN_CM && distance <= CAT_MAX_CM) {
        if (cat_hits < 3) ++cat_hits;
        protocolSerial().printf("HC1=%.1fcm CAT distance OK %u/3\n",
          double(distance), (unsigned)cat_hits);
        if (cat_hits == 3) startOpen(now);
      } else {
        cat_hits = 0;
      }
    }
    return;
  }
}
void hxTick(uint32_t now) { Sample s; s.now_ms=now;
  if (feed_stage == FeedStage::WAIT_HX) {
    if (uint32_t(now - started_at) > HX_WAIT_TIMEOUT_MS) {
      cancel("HX711 NO HEALTHY GRAM WITHIN 25S; CHECK WEIGHT/SENSOR", true);
      return;
    }
    if (acceptableScaleSample(s)) beginCatWithScale(s);
    return;
  }
}
void globalTick(uint32_t now) { Sample s; s.now_ms=now;
  if (feed_stage != FeedStage::CLOSING && uint32_t(now - started_at) > 45000u) {
    if (feed_stage == FeedStage::WAIT_WEIGHT || feed_stage == FeedStage::OPENING) {
      startClose(now, false);
    } else cancel("GLOBAL TIMEOUT", true);
    return;
  }
}
void confirmClosed() {
    if (busy() || pwm.moving()) {
      protocolSerial().print("INSPECT LOCK: stop motor, physically verify gate position.\n");
      return;
    }
    cat_inspect_required = false;
    timed_gate_stop = TimedGateStop::CLOSED;
    feed_stage = FeedStage::IDLE;
    protocolSerial().print("BENCH INSPECT ACK: operator confirms gate aligned CLOSED; this is not sensor feedback. CAT may resume.\n");
    return;
  }
#define GPIO_IS_VALID_GPIO(p) ((p)>=0&&(p)<=48)
#define GPIO_IS_VALID_OUTPUT_GPIO(p) GPIO_IS_VALID_GPIO(p)
namespace current_hardware {constexpr int SERVO_SIGNAL=6,PUMP_CONTROL=7,D2_WATER_ECHO=19;}
struct TestPins {
  bool inputAllowed(int pin) const {
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
  bool outputAllowed(int pin) const {
    return inputAllowed(pin)
      && pin != 10
      && pin != current_hardware::D2_WATER_ECHO // GPIO19 is D2 input on this USB-UART PCB.
      && GPIO_IS_VALID_OUTPUT_GPIO(pin);
  }
};

uint32_t expectedDuty(unsigned us){return (us*16384u+10000u)/20000u;}
void assertStopped(){assert(hw_attached&&!pwm.moving()&&duty==expectedDuty(1500));}

namespace std {using ::strlen;using ::strcmp;using ::strncmp;using ::strncpy;using ::memchr;}
unsigned char nv[4096];size_t nv_size=0;bool fail_nv=false;
class Preferences {public:bool begin(const char*,bool){return true;}size_t getBytesLength(const char*){return nv_size;}
size_t getBytes(const char*,void* out,size_t n){memcpy(out,nv,n);return n;}
size_t putBytes(const char*,const void* in,size_t n){if(fail_nv)return 0;memcpy(nv,in,n);nv_size=n;return n;}};
namespace bench_v8 {using ::busy;using ::dog_running;using ::demo_exited;using ::cat_inspect_required;using ::timed_gate_stop;using ::TimedGateStop;
using ::benchScaleSample;using ::beginManualFeed;using ::feed_stage;using ::FeedStage;using ::manual_feed_active;using ::last_delta_g;}
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

char ai_species='N';uint32_t ai_species_ms=0;constexpr uint32_t AI_DISPLAY_HOLD_MS=4000;
const char* oledAiLineText(uint32_t now) {
  if (ai_species_ms != 0 && uint32_t(now-ai_species_ms) <= AI_DISPLAY_HOLD_MS) {
    if(ai_species=='C') return "CAT";
    if(ai_species=='D') return "DOG";
  }
  return "FAIL";
}
void clearLog(){uart_n=0;uart_log[0]=0;}
int main(){
 scale_ready=true;scale_value=0;timed_gate_stop=TimedGateStop::CLOSED;
 clearLog();assert(scheduled_feed_v1::command("feed_once schedule_one",10000));
 assert(feed_stage==FeedStage::OPENING&&!manual_feed_active&&strstr(uart_log,"ACCEPTED")&&nv_size>0);
 unsigned previous=writes;clearLog();scheduled_feed_v1::command("feed_once schedule_one",10001);
 assert(writes==previous&&strstr(uart_log,"DUPLICATE"));
 clearLog();scheduled_feed_v1::command("feed_once schedule_two",10002);assert(writes==previous&&strstr(uart_log,"BUSY"));
 openingTick(10900);scale_stamp=15400;weightTick(15400);assert(feed_stage==FeedStage::WAIT_WEIGHT);
 scale_value=35;scale_stamp=15401;weightTick(15401);assert(feed_stage==FeedStage::CLOSING);
 closingTick(15401+1450);assert(feed_stage==FeedStage::DONE);clearLog();scheduled_feed_v1::tick();assert(strstr(uart_log,"WEIGHT_REACHED"));
 scheduled_feed_v1::loaded=false;scheduled_feed_v1::storage_ok=false;scheduled_feed_v1::history={};feed_stage=FeedStage::IDLE;
 previous=writes;clearLog();scheduled_feed_v1::command("feed_once schedule_one",20000);assert(writes==previous&&strstr(uart_log,"DUPLICATE"));
 scale_ready=false;clearLog();scheduled_feed_v1::command("feed_once schedule_two",20001);assert(writes==previous&&strstr(uart_log,"HX_NOT_READY"));
 scale_ready=true;fail_nv=true;clearLog();scheduled_feed_v1::command("feed_once schedule_two",20002);assert(writes==previous&&strstr(uart_log,"STORAGE_WRITE_FAILED"));fail_nv=false;
 cat_inspect_required=true;clearLog();scheduled_feed_v1::command("feed_once schedule_two",20003);assert(writes==previous&&strstr(uart_log,"INSPECTION_REQUIRED"));cat_inspect_required=false;
 clearLog();scheduled_feed_v1::command("feed_once bad/id",20004);assert(writes==previous&&strstr(uart_log,"INVALID_ID"));
 ai_species='N';feed_stage=FeedStage::OPENING;dog_running=true;assert(!strcmp(oledAiLineText(30000),"FAIL"));
 ai_species='C';ai_species_ms=30000;assert(!strcmp(oledAiLineText(30001),"CAT"));assert(!strcmp(oledAiLineText(34001),"FAIL"));
 ai_species='D';assert(!strcmp(oledAiLineText(30001),"DOG"));ai_species_ms=0xfffffff0u;assert(!strcmp(oledAiLineText(20),"DOG"));
 puts("PASS:scheduled ACK,durable duplicate across reboot,busy,HX,storage,inspection gates,25s weight path;OLED real CAT/DOG/FAIL/expiry/rollover");
}
