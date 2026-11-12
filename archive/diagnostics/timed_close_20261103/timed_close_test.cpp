
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
namespace std { using ::strtol; }
enum class FeedStage { IDLE, FAULT, OPENING, WAIT_WEIGHT, CLOSING, DIAG_OPEN, DIAG_CLOSE, DONE };
constexpr bool USE_CLOSE_LIMIT_SWITCH=false;
constexpr int LOW=0, PIN_CLOSE_LIMIT=47;
constexpr uint16_t SERVO_NEUTRAL_US=1500, SERVO_CLOSE_US=1700;
constexpr uint32_t MAX_SERVO_ACTIVE_MS=5000;
unsigned reads=0;
int digitalRead(int) { ++reads; return LOW; }
struct Serial { template<class... T> void printf(const char*,T...){} void print(const char*){} } serial;
Serial& protocolSerial(){return serial;}
struct Pwm {
  bool on=false; unsigned writes=0,stops=0; uint16_t pulse=0;
  bool attached(){return on;}
  bool start(uint16_t us){on=true; pulse=us; return true;}
  bool write(uint16_t us){++writes; pulse=us; return true;}
  bool off(){++stops;on=false;return true;}
} pwm;
FeedStage feed_stage=FeedStage::IDLE;
bool manual_feed_active=false, close_on_weight=false, limit_closed=true;
bool physical_closed_verified=false,cat_inspect_required=false,servo_armed=false;
bool meal_logged=false,meal_start_locked=false;
float last_delta_g=35,meal_starting_g=0,meal_remaining_g=0,meal_consumed_g=0;
float meal_plateau_ref_g=0,meal_stable_ref_g=0;
const char* meal_preference="NONE";
uint32_t meal_plateau_since=0,meal_closed_at=0,meal_stable_since=0,phase_at=0;
uint16_t open_ms=550,close_ms=4000;
unsigned cat_hits=0;
char current_food='A';
bool busy(){ return feed_stage!=FeedStage::IDLE && feed_stage!=FeedStage::FAULT && feed_stage!=FeedStage::DONE; }
void neutralMotor() {
  if (pwm.attached()) {
    pwm.write(SERVO_NEUTRAL_US);
    pwm.off();
  }
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
void diagTick(uint32_t now) {
  if (feed_stage == FeedStage::DIAG_OPEN || feed_stage == FeedStage::DIAG_CLOSE) {
    const bool hit_close_limit = USE_CLOSE_LIMIT_SWITCH && (feed_stage == FeedStage::DIAG_CLOSE) && (limit_closed || digitalRead(PIN_CLOSE_LIMIT) == LOW);
    const uint32_t duration = feed_stage == FeedStage::DIAG_OPEN ? open_ms : close_ms;
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
bool setMotionTime(const char* text, bool opening) {
  char* end = nullptr;
  const long value = std::strtol(text, &end, 10);
  if (*text == 0 || *end != 0 || value < 100 || value > MAX_SERVO_ACTIVE_MS
      || busy() || pwm.attached()) return false;
  if (opening) open_ms = (uint16_t)value;
  else close_ms = (uint16_t)value;
  return true;
}

int main(){
  // LOW/disconnected GPIO47 must have no influence on timed motion.
  startClose(100,true);
  assert(pwm.on && pwm.pulse==1700 && feed_stage==FeedStage::CLOSING);
  closingTick(4099); assert(pwm.on && feed_stage==FeedStage::CLOSING);
  closingTick(4100); assert(!pwm.on && feed_stage==FeedStage::DONE);
  assert(!physical_closed_verified && !cat_inspect_required && reads==0);
  // A close requested after HX failure remains a fault requiring inspection.
  startClose(5000,false); closingTick(9000);
  assert(!pwm.on && feed_stage==FeedStage::FAULT && cat_inspect_required);
  // millis rollover cannot stop early or run past the configured interval.
  startClose(UINT32_MAX-100,true);
  closingTick(3898); assert(pwm.on);
  closingTick(3899); assert(!pwm.on);
  // Stop interrupts motion immediately rather than waiting for its timer.
  startClose(12000,true); cancel("STOP",false);
  assert(!pwm.on && feed_stage==FeedStage::IDLE && cat_inspect_required);
  // Diagnostic motion uses the selected duration in each direction.
  pwm.start(1700); feed_stage=FeedStage::DIAG_CLOSE; phase_at=0;
  diagTick(3999); assert(pwm.on); diagTick(4000); assert(!pwm.on);
  pwm.start(1300); feed_stage=FeedStage::DIAG_OPEN; phase_at=0;
  diagTick(549); assert(pwm.on); diagTick(550); assert(!pwm.on);
  // Timing edits require idle state, valid integer syntax, and bounded values.
  assert(!setMotionTime("99",false)); assert(!setMotionTime("5001",false));
  assert(!setMotionTime("550junk",false)); assert(!setMotionTime("",false));
  assert(setMotionTime("550",false) && close_ms==550);
  startClose(20000,true); assert(!setMotionTime("1000",false));
  cancel("STOP",false); assert(setMotionTime("5000",false));
  assert(reads==0);
  puts("PASS: timed close, GPIO47 isolation, HX failure, rollover, stop, diagnostics, timing bounds");
}
