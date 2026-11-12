"""Deterministic policy simulation with persisted counters, no GPIO or device claims."""

from dataclasses import dataclass
from math import isfinite
from enum import Enum


class FeedState(str, Enum):
    SAFE_BOOT = "SAFE_BOOT"
    IDLE = "IDLE"
    PRECHECK = "PRECHECK"
    DISPENSING = "DISPENSING"
    CLOSING = "CLOSING"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    FAULT = "FAULT"


@dataclass
class DailyState:
    date_key: int = 0
    portions: int = 0
    grams: float = 0
    last_feed_epoch: int = 0
    revision: int = 1
    needs_inspection: bool = False


@dataclass
class FeedSensors:
    monotonic_seconds: float = 0
    epoch_seconds: int = 0
    date_key: int = 0
    rtc_valid: bool = False
    food_available: bool = False
    scale_valid: bool = False
    servo_valid: bool = False
    weight_grams: float = 0
    servo_closed: bool = False


class SimulatedFeedController:
    def __init__(self, daily: DailyState | None = None):
        self.record = daily if daily is not None else DailyState()
        self.locked = self._invalid_record(self.record)
        self.state = FeedState.SAFE_BOOT
        self.reason: str | None = None
        self.servo_open = False  # simulation flag, never physical output
        self.id: int | None = None
        self.target = self.baseline = self.began = self.progress_at = self.progress = 0.0

    @staticmethod
    def _invalid_record(value: DailyState) -> bool:
        return (value.revision != 1 or value.needs_inspection or not isfinite(value.grams) or
                value.grams < 0 or value.date_key == 0 and (value.portions != 0 or value.grams != 0))

    def boot(self, daily: DailyState | None = None):
        if daily is None:
            # Invalid safety record: NEVER reset counters to zero and proceed.
            self.record = DailyState(revision=0)
        else:
            self.record = daily
        self.locked = self._invalid_record(self.record)
        self.state = FeedState.SAFE_BOOT
        self.id = None
        self.servo_open = False
        self.reason = None

    def _reject(self, reason: str):
        self.state = FeedState.REJECTED
        self.reason = reason
        self.servo_open = False

    def _fault(self, reason: str):
        self.state = FeedState.FAULT
        self.reason = reason
        self.servo_open = False

    def tick(self, s: FeedSensors):
        if self.state == FeedState.SAFE_BOOT:
            if s.rtc_valid and s.date_key and not self.locked and \
                    s.date_key >= self.record.date_key:
                if s.date_key != self.record.date_key:
                    self.record.date_key = s.date_key
                    self.record.portions = 0
                    self.record.grams = 0
                self.state = FeedState.IDLE
            return
        if self.state == FeedState.PRECHECK:
            if (not all((s.rtc_valid, s.scale_valid, s.servo_valid, s.food_available)) or
                    s.date_key != self.record.date_key or not isfinite(s.weight_grams) or s.weight_grams < 0):
                self._fault("SENSOR_FAULT")
                return
            self.record.needs_inspection = True  # caller persists before real output in future
            self.state = FeedState.DISPENSING
            self.servo_open = True
            self.began = self.progress_at = s.monotonic_seconds
            self.progress = s.weight_grams
        elif self.state == FeedState.DISPENSING:
            if not all((s.rtc_valid, s.scale_valid, s.servo_valid, s.food_available)) or \
                    s.date_key != self.record.date_key or not isfinite(s.weight_grams) or s.weight_grams < 0:
                self._fault("SENSOR_FAULT")
            elif s.monotonic_seconds - self.began >= 20:
                self._fault("FEED_TIMEOUT")
            elif s.weight_grams - self.baseline >= self.target:
                self.servo_open = False
                self.state = FeedState.CLOSING
            else:
                if s.weight_grams - self.progress >= 0.2:
                    self.progress = s.weight_grams
                    self.progress_at = s.monotonic_seconds
                if s.monotonic_seconds - self.progress_at >= 5:
                    self._fault("NO_WEIGHT_PROGRESS")
        elif self.state == FeedState.CLOSING:
            if not s.rtc_valid or s.date_key != self.record.date_key or not s.servo_valid or \
                    s.monotonic_seconds - self.began >= 20:
                self._fault("SERVO_FAILURE")
            elif s.servo_closed and (not s.scale_valid or not isfinite(s.weight_grams) or
                                     s.weight_grams < self.baseline or
                                     self.record.grams + s.weight_grams - self.baseline > 150):
                self._fault("INVALID_WEIGHT")
            elif s.servo_closed:
                self.state = FeedState.COMPLETE
                self.record.portions += 1
                self.record.grams += s.weight_grams - self.baseline
                self.record.last_feed_epoch = s.epoch_seconds
                self.record.needs_inspection = False

    def request(self, request_id: int, target: float, s: FeedSensors) -> bool:
        if self.state in (FeedState.PRECHECK, FeedState.DISPENSING, FeedState.CLOSING, FeedState.FAULT):
            return False
        self.id = request_id
        self.reason = None
        self.servo_open = False
        if self.state == FeedState.SAFE_BOOT or self.locked or self.record.needs_inspection:
            self._reject("SAFE_BOOT")
        elif not s.rtc_valid or not s.date_key or s.epoch_seconds <= 0 or \
                s.date_key < self.record.date_key:
            self._reject("RTC_INVALID")
        else:
            if s.date_key != self.record.date_key:
                self.record.date_key, self.record.portions, self.record.grams = s.date_key, 0, 0
            if not 1 <= target <= 50:
                self._reject("TARGET_OUT_OF_RANGE")
            elif not s.food_available:
                self._reject("FOOD_EMPTY")
            elif not s.scale_valid or not isfinite(s.weight_grams) or s.weight_grams < 0:
                self._reject("HX711_FAILURE")
            elif not s.servo_valid:
                self._reject("SERVO_FAILURE")
            elif self.record.portions >= 4:
                self._reject("DAILY_LIMIT_REJECTED")
            elif self.record.grams + target > 150:
                self._reject("DAILY_GRAMS_LIMIT")
            elif self.record.last_feed_epoch and \
                    s.epoch_seconds - self.record.last_feed_epoch < 3600:
                self._reject("COOLDOWN_REJECTED")
            else:
                self.target = target
                self.baseline = s.weight_grams
                self.state = FeedState.PRECHECK
        return True


class WaterState(str, Enum):
    SAFE_BOOT = "SAFE_BOOT"
    NORMAL = "NORMAL"
    FILLING = "FILLING"
    FAULT = "FAULT"


class SimulatedWaterController:
    def __init__(self):
        self.state = WaterState.SAFE_BOOT
        self.pump_on = False
        self.reason: str | None = None
        self.good_samples = self.low_samples = 0
        self.began = self.progress_at = self.progress = 0.0

    def boot(self):
        self.__init__()  # pump always OFF, no automatic resume

    def tick(self, seconds: float, valid: bool, level: float, *, pump_valid: bool = True):
        if not valid or not 0 <= level <= 100:
            self.state, self.pump_on, self.reason = WaterState.FAULT, False, "WATER_SENSOR_FAILURE"
            self.good_samples = self.low_samples = 0
            return
        if self.state == WaterState.FAULT and self.reason != "WATER_SENSOR_FAILURE":
            return  # timeout/no-progress fault requires reset/inspection
        if self.state in (WaterState.SAFE_BOOT, WaterState.FAULT):
            self.good_samples += 1
            if self.good_samples < 3:
                return
            self.state, self.reason = WaterState.NORMAL, None
            self.low_samples = 0
        if self.state == WaterState.NORMAL:
            self.low_samples = self.low_samples + 1 if level < 25 else 0
            if self.low_samples >= 3:
                if not pump_valid:
                    self.state, self.pump_on, self.reason = WaterState.FAULT, False, "PUMP_FAULT"
                else:
                    self.state, self.pump_on = WaterState.FILLING, True
                    self.began = self.progress_at = seconds
                    self.progress = level
        elif self.state == WaterState.FILLING:
            if not pump_valid:
                self.state, self.pump_on, self.reason = WaterState.FAULT, False, "PUMP_FAULT"
            elif level >= 75:
                self.state, self.pump_on = WaterState.NORMAL, False
                self.low_samples = 0
            elif seconds - self.began >= 30:
                self.state, self.pump_on, self.reason = WaterState.FAULT, False, "PUMP_TIMEOUT"
            else:
                if level - self.progress >= 2:
                    self.progress, self.progress_at = level, seconds
                if seconds - self.progress_at >= 5:
                    self.state, self.pump_on, self.reason = WaterState.FAULT, False, "PUMP_NO_PROGRESS"
