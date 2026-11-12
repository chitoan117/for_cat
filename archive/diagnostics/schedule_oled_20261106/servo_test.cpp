
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
struct Serial { template<class... T> void printf(const char*,T...){} void print(const char*){} } serial;
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
int main(){ TestPins pins; assert(pins.inputAllowed(19)&&!pins.outputAllowed(19)&&!pins.inputAllowed(20)&&!pins.inputAllowed(6)&&!pins.inputAllowed(7));
 assert(open_ms==900&&close_ms==1450);
 assert(SERVO_OPEN_US==1350&&SERVO_CLOSE_US==1600&&SERVO_NEUTRAL_US==1500);
 uint32_t t=10000;
 for(unsigned i=0;i<5;++i){
   assert(manualServoMove(true,open_ms,t));
   diagTick(t+open_ms-1);assert(pwm.moving());diagTick(t+open_ms);assertStopped();
   unsigned old=writes;assert(!manualServoMove(true,open_ms,t+open_ms+1)&&old==writes);
   uint32_t close_at=t+open_ms+100;
   assert(manualServoMove(false,close_ms,close_at));
   diagTick(close_at+close_ms-1);assert(pwm.moving());diagTick(close_at+close_ms);assertStopped();
   assert(timed_gate_stop==TimedGateStop::CLOSED);
   old=writes;assert(!manualServoMove(false,close_ms,close_at+close_ms+1)&&old==writes);
   t=close_at+close_ms+100;
 }
 scale_ready=true;scale_value=0;beginManualFeed(t,"BUTTON");openingTick(t+open_ms);
 last_delta_g=0.1f;beginManualFeed(t+open_ms+100,"BUTTON");
 closingTick(t+open_ms+100+close_ms-1);assert(pwm.moving());
 closingTick(t+open_ms+100+close_ms);assertStopped();
 assert(feed_stage==FeedStage::FAULT&&!cat_inspect_required);
 t+=open_ms+close_ms+200;beginManualFeed(t,"BUTTON");assert(pwm.moving());
 cancel("STOP",false);assertStopped();assert(cat_inspect_required);
 auto old=writes;beginManualFeed(t+100,"BUTTON");assert(writes==old);
 // Run the actual production weight branch at the new target boundary.
 cat_inspect_required=false;feed_stage=FeedStage::IDLE;timed_gate_stop=TimedGateStop::CLOSED;
 t=100000;scale_value=0;scale_ready=true;beginManualFeed(t,"BUTTON");openingTick(t+open_ms);
 scale_value=34.99f;++scale_stamp;weightTick(t+open_ms+1);assert(feed_stage==FeedStage::WAIT_WEIGHT);
 scale_value=35.0f;++scale_stamp;weightTick(t+open_ms+2);assert(feed_stage==FeedStage::CLOSING&&close_on_weight);
 closingTick(t+open_ms+2+close_ms);assertStopped();
 // Three distinct E1 readings are required; 30cm is accepted, >30cm rejected.
 cat_inspect_required=false;feed_stage=FeedStage::WAIT_CAT;timed_gate_stop=TimedGateStop::CLOSED;
 phase_at=200000;cat_hits=0;last_hc_ms=0;hc.raw.valid=hc.raw.fresh=true;
 hc.raw.value=30.01f;hc.raw.sampled_at_ms=200001;catTick(200001);assert(cat_hits==0);
 hc.raw.value=30.0f;
 for(unsigned i=1;i<=3;i++){hc.raw.sampled_at_ms=200001+180*i;catTick(hc.raw.sampled_at_ms);}
 assert(feed_stage==FeedStage::OPENING);cancel("STOP",false);
 puts("PASS: 34.99g waits,35g closes;E1 30cm accepted after3 distinct readings,30.01cm rejected");
 puts("PASS:new closing duration boundary;5 alternating cycles;no extra duplicate strokes;manual early-close retry;STOP lock;neutral and loadcell mass result preserved");
}
