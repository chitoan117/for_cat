
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
constexpr uint16_t SERVO_OPEN_US = 1400; // UNO-tested: open RIGHT.
constexpr uint16_t SERVO_CLOSE_US = 1600; // UNO-tested: close LEFT.
constexpr uint16_t SERVO_NEUTRAL_US = 1500;
constexpr uint16_t SERVO_FINE_MS = 170; // Actual UNO FINE_MS.
constexpr uint32_t MAX_SERVO_ACTIVE_MS = 5000;
constexpr float CLOSE_AT_G = 30.0f;  // 30..40g acceptable; close on crossing 30g
constexpr float MAX_NORMAL_G = 40.0f;
constexpr float CAT_MIN_CM = 5.0f;
constexpr float CAT_MAX_CM = 30.0f;
constexpr uint32_t CAT_WAIT_TIMEOUT_MS = 30000;
constexpr uint32_t HX_WAIT_TIMEOUT_MS = 25000;
constexpr uint32_t WEIGHT_WAIT_TIMEOUT_MS = 25000;
uint16_t open_ms = 1100; // Actual UNO OPEN_MS, not its outdated menu text.
uint16_t close_ms = 900; // Actual UNO CLOSE_MS, owner-tested mechanism.

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
  if (may_have_moved) cat_inspect_required = true;
  feed_stage = error ? FeedStage::FAULT : FeedStage::IDLE;
  servo_armed = false;
  cat_hits = 0;
}
bool startOpen(uint32_t now) {
  if ((!pwm.attached() && !pwm.start(SERVO_NEUTRAL_US)) || !pwm.write(SERVO_OPEN_US)) {
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
  manual_feed_active = false;
  close_on_weight = by_weight;
  // If V-153-1C25 limit switch on GPIO47 is already pressed, stop immediately without driving close
  if (USE_CLOSE_LIMIT_SWITCH && (limit_closed || digitalRead(PIN_CLOSE_LIMIT) == LOW)) {
    neutralMotor();
    physical_closed_verified = true;
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
  buzzerStop();
  demo_exited = false;
  cat_inspect_required = false;
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
  protocolSerial().print("CAT REQUEST: healthy ZERO baseline, waiting REAL HC1 distance 5..30cm x3.\n");
  return true;
}
bool manualServoMove(bool opening, uint32_t duration, uint32_t now) {
  if (busy() || pwm.moving() || dog_running || bench_cal != BenchCal::Idle) {
    protocolSerial().print("SERVO BUSY: use 0 / stop to stop first.\n");
    return false;
  }
  if (!duration || duration > MAX_SERVO_ACTIVE_MS) return false;
  if ((!pwm.attached() && !pwm.start(SERVO_NEUTRAL_US))
      || !pwm.write(opening ? SERVO_OPEN_US : SERVO_CLOSE_US)) {
    neutralMotor();
    protocolSerial().print("SERVO MANUAL OUTPUT FAILED; no timed move started.\n");
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
      physical_closed_verified = hit_limit;
      cat_inspect_required = !close_on_weight && !hit_limit;
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

uint32_t expectedDuty(unsigned us){return (us*16384u+10000u)/20000u;}
void assertStopped(){assert(hw_attached&&!pwm.moving()&&duty==expectedDuty(1500));}
int main(){
  assert(SERVO_OPEN_US==1400&&SERVO_CLOSE_US==1600&&SERVO_NEUTRAL_US==1500);
  assert(open_ms==1100&&close_ms==900&&SERVO_FINE_MS==170);
  assert(!pwm.attached()); // Boot output remains detached until a movement command.
  assert(manualServoMove(true,open_ms,100));
  assert(duty==expectedDuty(1400)&&attaches==1&&pwm.moving());
  assert(!manualServoMove(false,close_ms,200)); // No restart or queue while moving.
  beginManualFeed(200,"WEB"); // A web/button feed must not preempt servo adjustment.
  assert(phase_at==100&&servo_move_for_ms==1100);
  diagTick(1199); assert(pwm.moving()); diagTick(1200); assertStopped();
  assert(manualServoMove(false,close_ms,1300));
  assert(attaches==1&&duty==expectedDuty(1600)); // Reuse neutral PWM.
  diagTick(2199); assert(pwm.moving()); diagTick(2200); assertStopped();
  assert(manualServoMove(false,SERVO_FINE_MS,2300));
  diagTick(2469); assert(pwm.moving()); diagTick(2470); assertStopped();
  assert(manualServoMove(true,SERVO_FINE_MS,2500));
  assert(duty==expectedDuty(1400)); diagTick(2670); assertStopped();
  assert(manualServoMove(true,open_ms,2800)); cancel("STOP",false); assertStopped();
  assert(cat_inspect_required);
  assert(manualServoMove(false,SERVO_FINE_MS,3000));
  diagTick(3170); assertStopped(); // Explicit correction allowed after stop.
  assert(cat_inspect_required); // Correction does not unlock automatic feeding.
  cat_inspect_required=false;
  assert(startOpen(4000)); openingTick(5099); assert(pwm.moving());
  openingTick(5100); assertStopped(); assert(feed_stage==FeedStage::WAIT_WEIGHT);
  startClose(5200,true); assert(duty==expectedDuty(1600));
  closingTick(6099); assert(pwm.moving()); closingTick(6100); assertStopped();
  assert(feed_stage==FeedStage::DONE&&!physical_closed_verified);
  startClose(6200,false); closingTick(7100); assertStopped();
  assert(feed_stage==FeedStage::FAULT&&cat_inspect_required);
  feed_stage=FeedStage::IDLE;
  assert(manualServoMove(true,170,UINT32_MAX-100));
  diagTick(68); assert(pwm.moving()); diagTick(69); assertStopped();
  assert(setMotionTime("1100",true)); assert(setMotionTime("900",false));
  assert(!setMotionTime("99",true)&&!setMotionTime("5001",false));
  assert(!setMotionTime("900x",false));
  dog_running=true; assert(!manualServoMove(true,170,8000)); dog_running=false;
  bench_cal=BenchCal::Tare; assert(!manualServoMove(true,170,8000)); bench_cal=BenchCal::Idle;
  assert(!manualServoMove(true,0,8000)&&!manualServoMove(true,5001,8000));
  assert(manualServoMove(true,170,8000)); fail_write=true; neutralMotor();
  assert(!pwm.attached()&&detaches==1); // Output failure falls back to detach.
  assert(gpio_reads==0);
  fail_write=false; feed_stage=FeedStage::IDLE; cat_inspect_required=false;
  unsigned before_writes=writes;
  scale_ready=false; hx.signed_grams.valid=true; hx.signed_grams.value=0;
  beginManualFeed(9000,"WEB");
  assert(!pwm.moving()&&writes==before_writes); // No stale or synthetic 0g fallback.
  scale_ready=true; scale_value=0; scale_stamp=10000;
  beginManualFeed(10000,"BUTTON"); assert(pwm.moving()&&manual_feed_active);
  openingTick(11100); assert(feed_stage==FeedStage::WAIT_WEIGHT); assertStopped();
  scale_value=29; scale_stamp=15099; weightTick(15099);
  assert(feed_stage==FeedStage::WAIT_WEIGHT);
  scale_stamp=15100; weightTick(15100);
  assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
  closingTick(16000); assert(feed_stage==FeedStage::FAULT); assertStopped();
  // A valid measured threshold produces a normal close; >40g is not MASS OK.
  beginManualFeed(17000,"WEB"); openingTick(18100);
  scale_value=baseline_g+30; scale_stamp=18200; weightTick(18200);
  assert(close_on_weight); closingTick(19100); assert(feed_stage==FeedStage::DONE);
  scale_value=0; beginManualFeed(20000,"WEB"); openingTick(21100);
  scale_value=41; scale_stamp=21200; weightTick(21200);
  assert(!close_on_weight); closingTick(22100); assert(feed_stage==FeedStage::FAULT);
  // Loss of the scale during an open cycle triggers a bounded failure close.
  scale_value=0; scale_ready=true; beginManualFeed(23000,"WEB"); openingTick(24100);
  scale_ready=false; weightTick(25900); assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
  closingTick(26800); assert(feed_stage==FeedStage::FAULT); assertStopped();
  // Missing HX never energizes while waiting; valid nonzero CAT baseline blocks.
  feed_stage=FeedStage::WAIT_HX; started_at=30000; before_writes=writes;
  hxTick(55000); assert(writes==before_writes&&!pwm.moving());
  hxTick(55001); assert(feed_stage==FeedStage::FAULT);
  scale_ready=true; scale_value=3; Sample sample; sample.now_ms=60000;
  assert(!beginCatWithScale(sample)&&!pwm.moving());
  scale_value=0; assert(beginCatWithScale(sample));
  hc.raw={true,true,60100,10}; catTick(60100); assert(cat_hits==1);
  catTick(60101); assert(cat_hits==1); // Duplicate sample does not count.
  hc.raw.valid=false; hc.raw.fresh=false; catTick(60200); assert(cat_hits==0);
  hc.raw={true,true,60300,10}; catTick(60300);
  hc.raw.sampled_at_ms=60500; catTick(60500); assert(cat_hits==2&&!pwm.moving());
  hc.raw.sampled_at_ms=60700; catTick(60700); assert(feed_stage==FeedStage::OPENING&&pwm.moving());
  cancel("STOP",false);
  // Global deadline still grants the recovery close its 900ms, then stops.
  feed_stage=FeedStage::WAIT_WEIGHT; started_at=0; globalTick(45001);
  assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
  globalTick(45002); closingTick(45002); assert(pwm.moving());
  closingTick(45901); assertStopped(); assert(feed_stage==FeedStage::FAULT);
  puts("PASS: UNO PWM/durations, neutral hold, repeat/fine moves, busy rejection, automatic cycle, STOP, rollover, fault and bounds");
  puts("PASS: missing/stale scale manual block, mass threshold/overshoot/timeout, HX loss, consecutive HC1, no premature recovery-stop");
}
