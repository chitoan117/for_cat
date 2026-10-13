#pragma once

// Portable deterministic policy/state logic. NEVER connects to GPIO.
#include <cmath>
#include <cstdint>

namespace safety {
enum class Health : uint8_t { NOT_VALIDATED, OK, FAULT };
enum class FeedState : uint8_t {
  SAFE_BOOT, IDLE, PRECHECK, DISPENSING, CLOSING, COMPLETE, REJECTED, FAULT
};
enum class FeedReason : uint8_t {
  NONE, BUSY, RTC_INVALID, FOOD_EMPTY, HX711_FAULT, SERVO_FAULT,
  TARGET_OUT_OF_RANGE, DAILY_PORTIONS, DAILY_GRAMS, COOLDOWN,
  TIMEOUT, NO_PROGRESS, INVALID_WEIGHT, CLOSE_FAILURE, SAFE_MODE, PERSISTENCE_FAULT
};

struct DailyRecord {
  uint32_t revision = 2;
  uint32_t day = 0;            // YYYYMMDD from validated RTC, 0 = unknown
  uint16_t portions = 0;
  float grams = 0;
  uint64_t last_feed_epoch = 0;
  bool needs_inspection = false;  // uncertain interrupted dispense: fail closed
};

class DailyStore {
 public:
  virtual ~DailyStore() = default;
  virtual bool save(const DailyRecord&) = 0;
};

struct FeedPolicy {
  float min_grams = 1;
  float max_grams = 50;
  float max_daily_grams = 150;
  uint16_t max_daily_portions = 4;
  uint32_t cooldown_seconds = 3600;
  uint32_t feed_timeout_ms = 20000;
  uint32_t progress_timeout_ms = 5000;
  float min_progress_grams = 0.2f;
};

struct FeedInputs {
  uint32_t now_ms = 0;          // monotonic, unsigned subtraction handles wrap
  uint64_t epoch_seconds = 0;   // only used when RTC valid
  uint32_t day = 0;
  bool rtc_valid = false;
  bool food_available = false;
  Health scale = Health::NOT_VALIDATED;
  Health servo = Health::NOT_VALIDATED;
  float measured_grams = 0;
  bool servo_closed = false;
};

class FeedController {
 public:
  explicit FeedController(FeedPolicy policy = {}) : policy_(policy) {}
  void attachStore(DailyStore& store) { store_ = &store; }

  void boot(DailyRecord persisted) {
    locked_ = persisted.revision != 2 || persisted.needs_inspection ||
              !std::isfinite(persisted.grams) ||
              persisted.grams < 0 || (persisted.day == 0 &&
              (persisted.portions != 0 || persisted.grams != 0));
    record_ = persisted.revision == 2 ? persisted : DailyRecord{};
    state_ = FeedState::SAFE_BOOT;
    reason_ = FeedReason::NONE;
    open_requested_ = false;
    request_id_ = 0;  // never resume an interrupted feeding operation
  }

  void tick(const FeedInputs& input) {
    if (state_ == FeedState::SAFE_BOOT) {
      if (!locked_ && input.rtc_valid && input.day != 0 &&
          (record_.day == 0 || input.day >= record_.day)) {
        if (syncDay(input)) state_ = FeedState::IDLE;
        else fault(FeedReason::PERSISTENCE_FAULT);
      }
      return;
    }
    if (state_ == FeedState::PRECHECK) {
      // Inputs may have changed since command receipt; recheck before desired-open.
      if (!input.rtc_valid || input.day != record_.day || !input.food_available ||
          input.scale != Health::OK || input.servo != Health::OK ||
          !std::isfinite(input.measured_grams) || input.measured_grams < 0) {
        fault(FeedReason::INVALID_WEIGHT); return;
      }
      // Write-ahead barrier: a failed NVS write cannot open a real servo.
      DailyRecord pending = record_;
      pending.needs_inspection = true;
      if (!store_ || !store_->save(pending)) {
        fault(FeedReason::PERSISTENCE_FAULT); return;
      }
      record_ = pending;
      state_ = FeedState::DISPENSING;
      open_requested_ = true;  // simulation-only desired state
      began_at_ = progressed_at_ = input.now_ms;
      progress_grams_ = input.measured_grams;
      return;
    }
    if (state_ == FeedState::DISPENSING) {
      if (!input.rtc_valid || input.day != record_.day || input.scale != Health::OK ||
          input.servo != Health::OK || !input.food_available ||
          !std::isfinite(input.measured_grams)) {
        fault(FeedReason::INVALID_WEIGHT); return;
      }
      if (static_cast<uint32_t>(input.now_ms - began_at_) >= policy_.feed_timeout_ms) {
        fault(FeedReason::TIMEOUT); return;
      }
      float delta = input.measured_grams - baseline_;
      if (delta >= target_) {
        open_requested_ = false;
        state_ = FeedState::CLOSING;
        return;
      }
      if (input.measured_grams - progress_grams_ >= policy_.min_progress_grams) {
        progress_grams_ = input.measured_grams;
        progressed_at_ = input.now_ms;
      }
      if (static_cast<uint32_t>(input.now_ms - progressed_at_) >= policy_.progress_timeout_ms)
        fault(FeedReason::NO_PROGRESS);
      return;
    }
    if (state_ == FeedState::CLOSING) {
      if (!input.rtc_valid || input.day != record_.day || input.servo != Health::OK ||
          static_cast<uint32_t>(input.now_ms - began_at_) >= policy_.feed_timeout_ms) {
        fault(FeedReason::CLOSE_FAILURE); return;
      }
      if (input.scale != Health::OK) { fault(FeedReason::INVALID_WEIGHT); return; }
      if (!input.servo_closed) return;
      float actual = input.measured_grams - baseline_;
      if (!std::isfinite(actual) || actual < 0 ||
          record_.grams + actual > policy_.max_daily_grams) {
        fault(FeedReason::INVALID_WEIGHT); return;
      }
      DailyRecord complete = record_;
      complete.grams += actual;
      ++complete.portions;
      complete.last_feed_epoch = input.epoch_seconds;
      complete.needs_inspection = false;
      // Persist counters and clear inspection flag before reporting SUCCESS.
      if (!store_ || !store_->save(complete)) {
        fault(FeedReason::PERSISTENCE_FAULT); return;
      }
      record_ = complete;
      state_ = FeedState::COMPLETE;
    }
  }

  // Returns false on controller-busy; duplicates must be handled at caller ID cache.
  bool request(uint32_t id, float target, const FeedInputs& input) {
    if (state_ == FeedState::PRECHECK || state_ == FeedState::DISPENSING ||
        state_ == FeedState::CLOSING || state_ == FeedState::FAULT) return false;
    request_id_ = id;
    target_ = target;
    reason_ = FeedReason::NONE;
    open_requested_ = false;
    if (state_ == FeedState::SAFE_BOOT || locked_ || record_.needs_inspection) {
      reject(FeedReason::SAFE_MODE); return true;
    }
    if (!input.rtc_valid || input.day == 0 || input.epoch_seconds == 0) {
      reject(FeedReason::RTC_INVALID); return true;
    }
    if (record_.day != 0 && input.day < record_.day) {
      reject(FeedReason::RTC_INVALID); return true;
    }
    if (!syncDay(input)) { fault(FeedReason::PERSISTENCE_FAULT); return true; }
    if (!std::isfinite(target) || target < policy_.min_grams || target > policy_.max_grams)
      reject(FeedReason::TARGET_OUT_OF_RANGE);
    else if (!input.food_available) reject(FeedReason::FOOD_EMPTY);
    else if (input.scale != Health::OK || !std::isfinite(input.measured_grams) ||
             input.measured_grams < 0)
      reject(FeedReason::HX711_FAULT);
    else if (input.servo != Health::OK) reject(FeedReason::SERVO_FAULT);
    else if (record_.portions >= policy_.max_daily_portions)
      reject(FeedReason::DAILY_PORTIONS);
    else if (record_.grams + target > policy_.max_daily_grams)
      reject(FeedReason::DAILY_GRAMS);
    else if (record_.last_feed_epoch != 0 &&
             (input.epoch_seconds < record_.last_feed_epoch ||
              input.epoch_seconds - record_.last_feed_epoch < policy_.cooldown_seconds))
      reject(FeedReason::COOLDOWN);
    else {
      baseline_ = input.measured_grams;
      state_ = FeedState::PRECHECK;
    }
    return true;
  }

  FeedState state() const { return state_; }
  FeedReason reason() const { return reason_; }
  bool openRequested() const { return open_requested_; }
  uint32_t requestId() const { return request_id_; }
  DailyRecord record() const { return record_; }

 private:
  bool syncDay(const FeedInputs& input) {
    if (input.rtc_valid && input.day != 0 && record_.day != input.day) {
      DailyRecord next = record_;
      next.day = input.day;
      next.portions = 0;
      next.grams = 0;
      // Preserve last-feed epoch for cooldown across midnight.
      if (!store_ || !store_->save(next)) return false;
      record_ = next;
    }
    return true;
  }
  void reject(FeedReason reason) {
    reason_ = reason; open_requested_ = false; state_ = FeedState::REJECTED;
  }
  void fault(FeedReason reason) {
    reason_ = reason; open_requested_ = false; state_ = FeedState::FAULT;
  }

  FeedPolicy policy_;
  DailyRecord record_{};
  FeedState state_ = FeedState::SAFE_BOOT;
  FeedReason reason_ = FeedReason::NONE;
  uint32_t request_id_ = 0, began_at_ = 0, progressed_at_ = 0;
  float baseline_ = 0, progress_grams_ = 0, target_ = 0;
  bool open_requested_ = false;
  bool locked_ = false;
  DailyStore* store_ = nullptr;
};

enum class WaterState : uint8_t { SAFE_BOOT, NORMAL, FILLING, FAULT };
enum class WaterReason : uint8_t { NONE, SENSOR_FAULT, PUMP_FAULT, NO_PROGRESS, TIMEOUT };
struct WaterInputs {
  uint32_t now_ms = 0;
  Health sensor = Health::NOT_VALIDATED;
  Health pump = Health::NOT_VALIDATED;
  float level_percent = 0;
};
struct WaterPolicy {
  float low_percent = 25, high_percent = 75, min_progress_percent = 2;
  uint8_t stable_samples = 3;
  uint32_t max_run_ms = 30000, progress_timeout_ms = 5000;
};

class WaterController {
 public:
  explicit WaterController(WaterPolicy policy = {}) : policy_(policy) {}
  void boot() { state_ = WaterState::SAFE_BOOT; reason_ = WaterReason::NONE;
                pump_requested_ = false; low_count_ = good_count_ = 0; }
  void tick(const WaterInputs& input) {
    if (input.sensor != Health::OK || !std::isfinite(input.level_percent) ||
        input.level_percent < 0 || input.level_percent > 100) {
      state_ = WaterState::FAULT; reason_ = WaterReason::SENSOR_FAULT;
      pump_requested_ = false; good_count_ = low_count_ = 0; return;
    }
    if (state_ == WaterState::FAULT && reason_ != WaterReason::SENSOR_FAULT) return;
    if (state_ == WaterState::FAULT || state_ == WaterState::SAFE_BOOT) {
      if (++good_count_ < policy_.stable_samples) return;
      state_ = WaterState::NORMAL; reason_ = WaterReason::NONE; low_count_ = 0;
    }
    if (state_ == WaterState::NORMAL) {
      low_count_ = input.level_percent < policy_.low_percent ? low_count_ + 1 : 0;
      if (low_count_ >= policy_.stable_samples) {
        if (input.pump != Health::OK) { fail(WaterReason::PUMP_FAULT); return; }
        state_ = WaterState::FILLING; pump_requested_ = true;
        began_at_ = progressed_at_ = input.now_ms;
        progress_level_ = input.level_percent;
      }
    } else if (state_ == WaterState::FILLING) {
      if (input.pump != Health::OK) { fail(WaterReason::PUMP_FAULT); return; }
      if (input.level_percent >= policy_.high_percent) {
        state_ = WaterState::NORMAL; pump_requested_ = false; low_count_ = 0; return;
      }
      if (static_cast<uint32_t>(input.now_ms - began_at_) >= policy_.max_run_ms) {
        fail(WaterReason::TIMEOUT); return;
      }
      if (input.level_percent - progress_level_ >= policy_.min_progress_percent) {
        progress_level_ = input.level_percent; progressed_at_ = input.now_ms;
      }
      if (static_cast<uint32_t>(input.now_ms - progressed_at_) >= policy_.progress_timeout_ms)
        fail(WaterReason::NO_PROGRESS);
    }
  }
  WaterState state() const { return state_; }
  WaterReason reason() const { return reason_; }
  bool pumpRequested() const { return pump_requested_; }

 private:
  void fail(WaterReason reason) {
    state_ = WaterState::FAULT; reason_ = reason; pump_requested_ = false;
  }
  WaterPolicy policy_;
  WaterState state_ = WaterState::SAFE_BOOT;
  WaterReason reason_ = WaterReason::NONE;
  uint8_t low_count_ = 0, good_count_ = 0;
  uint32_t began_at_ = 0, progressed_at_ = 0;
  float progress_level_ = 0;
  bool pump_requested_ = false;
};
}  // namespace safety
