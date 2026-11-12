
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#undef isfinite
namespace std { using ::strtol; inline bool isfinite(float v){return __builtin_isfinite(v);} }
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
bool benchScaleSample(uint32_t,float&,uint32_t&){return false;}
void buzzerStop(){dog_running=false;}
float meal_plateau_ref_g=0,meal_stable_ref_g=0;
const char* meal_preference="NONE";
uint32_t meal_plateau_since=0,meal_closed_at=0,meal_stable_since=0;
uint32_t phase_at=0,started_at=0,servo_move_for_ms=0,last_scale_ms=0;
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
  protocolSerial().printf("CAT 3x <=20cm CONFIRMED. SERVO OPEN %u ms, PWM %u us.\n",
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
    startClose(now, true);
    return;
  }
  if (feed_stage == FeedStage::OPENING || feed_stage == FeedStage::CLOSING) {
    return;
  }
  float g = NAN;
  uint32_t sample_ms = 0;
  if (benchScaleSample(now, g, sample_ms)) {
    baseline_g = g;
  } else if (hx.signed_grams.valid && std::isfinite(hx.signed_grams.value)) {
    baseline_g = hx.signed_grams.value;
  } else {
    baseline_g = 0.0f;
  }
  last_delta_g = 0.0f;
  cat_hits = 3;
  last_scale_ms = 0;
  manual_feed_active = true;
  started_at = phase_at = now;
  protocolSerial().printf("MANUAL FEED (%s): baseline=%.2fg -> SERVO OPEN NOW!\n",
    source, double(baseline_g));
  startOpen(now);
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
void diagTick(uint32_t now) {
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
void openingTick(uint32_t now) {
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
void closingTick(uint32_t now) {
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
  puts("PASS: UNO PWM/durations, neutral hold, repeat/fine moves, busy rejection, automatic cycle, STOP, rollover, fault and bounds");
}
