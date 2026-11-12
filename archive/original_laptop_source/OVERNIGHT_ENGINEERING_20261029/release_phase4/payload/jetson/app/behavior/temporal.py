"""Monotonic, frame-confirmed eating/drinking sessions. No classifier included."""

from datetime import datetime, timezone, timedelta
from enum import Enum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ai.models import Identity
from app.behavior.models import Behavior


class SignalType(str, Enum):
    START = "START"
    END = "END"


class Prediction(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    timestamp: datetime
    monotonic_seconds: float = Field(ge=0)
    identity: Identity
    behavior: Behavior
    confidence: float | None = Field(default=None, ge=0, le=1)
    food_roi: bool = False
    water_roi: bool = False

    @field_validator("timestamp")
    @classmethod
    def require_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must have a timezone")
        return value.astimezone(timezone.utc)


class SessionSignal(BaseModel):
    signal: SignalType
    session_id: str
    identity: Identity
    behavior: Behavior
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    approach_delay_seconds: float | None = None
    repeat_visits: int = 0


class TemporalEngine:
    def __init__(self, min_frames: int = 2, confirm_seconds: float = 0.5,
                 dropout_seconds: float = 1.5, cooldown_seconds: float = 0.5,
                 min_confidence: float = 0.5):
        if min_frames < 2 or min_frames > 30 or not 0 <= confirm_seconds <= 30 or \
                not 0 < dropout_seconds <= 30 or not 0 <= cooldown_seconds <= 30 or \
                not isfinite(min_confidence) or not 0 <= min_confidence <= 1:
            raise ValueError("invalid temporal thresholds")
        self.min_frames, self.confirm_seconds = min_frames, confirm_seconds
        self.dropout_seconds, self.cooldown_seconds = dropout_seconds, cooldown_seconds
        self.min_confidence = min_confidence
        self.candidate: tuple[Identity, Behavior, float, datetime, int] | None = None
        self._candidate_last_mono = 0.0
        self.active: SessionSignal | None = None
        self.last_good_mono = 0.0
        self.last_good_time: datetime | None = None
        self.last_mono = -1.0
        self.cooldown_until = 0.0
        self.approach: dict[tuple[Identity, Behavior], float] = {}
        self.last_end: dict[tuple[Identity, Behavior], float] = {}
        self.serial = 0

    @staticmethod
    def _kind(p: Prediction) -> Behavior | None:
        if p.identity not in (Identity.OWNER_CAT, Identity.OTHER_CAT):
            return None
        if p.behavior == Behavior.EATING and p.food_roi:
            return Behavior.EATING
        if p.behavior == Behavior.DRINKING and p.water_roi:
            return Behavior.DRINKING
        return None

    def _finish(self) -> SessionSignal:
        finished = self.active.model_copy(update={
            "signal": SignalType.END,
            "ended_at": self.active.started_at + timedelta(seconds=max(0.0, self.last_good_mono - self._started_mono)),
            "duration_seconds": round(max(0.0, self.last_good_mono - self._started_mono), 3),
        })
        self.last_end[(finished.identity, finished.behavior)] = self.last_good_mono
        self.cooldown_until = self.last_good_mono + self.cooldown_seconds
        self.active = None
        self.candidate = None
        return finished

    def update(self, p: Prediction) -> list[SessionSignal]:
        if p.monotonic_seconds < self.last_mono:
            raise ValueError("prediction monotonic time moved backwards")
        self.last_mono = p.monotonic_seconds
        events = []
        kind = self._kind(p)
        valid = kind is not None and p.confidence is not None and p.confidence >= self.min_confidence
        if p.identity in (Identity.OWNER_CAT, Identity.OTHER_CAT):
            if p.behavior == Behavior.NEAR_FOOD and p.food_roi:
                self.approach.setdefault((p.identity, Behavior.EATING), p.monotonic_seconds)
            if p.behavior == Behavior.NEAR_WATER and p.water_roi:
                self.approach.setdefault((p.identity, Behavior.DRINKING), p.monotonic_seconds)
        if self.active is not None:
            if p.monotonic_seconds - self.last_good_mono >= self.dropout_seconds:
                events.append(self._finish())
            elif valid and self.active.identity == p.identity and self.active.behavior == kind:
                self.last_good_mono = p.monotonic_seconds
                self.last_good_time = p.timestamp
                return events
            else:
                return events
        if not valid or p.monotonic_seconds < self.cooldown_until:
            self.candidate = None
            return events
        key = (p.identity, kind)
        if self.candidate is None or self.candidate[:2] != key or \
                p.monotonic_seconds-self._candidate_last_mono >= self.dropout_seconds:
            self.candidate = (p.identity, kind, p.monotonic_seconds, p.timestamp, 1)
            self._candidate_last_mono = p.monotonic_seconds
            return events
        identity, behavior, first_mono, first_time, count = self.candidate
        count = min(count + 1, self.min_frames)
        self.candidate = (identity, behavior, first_mono, first_time, count)
        self._candidate_last_mono = p.monotonic_seconds
        if count >= self.min_frames and p.monotonic_seconds - first_mono >= self.confirm_seconds:
            self.serial += 1
            last = self.last_end.get(key)
            approach = self.approach.pop(key, None)
            self.active = SessionSignal(
                signal=SignalType.START, session_id=f"visit-{self.serial:06d}",
                identity=identity, behavior=behavior, started_at=first_time,
                approach_delay_seconds=round(max(0, first_mono - approach), 3) if approach is not None else None,
                repeat_visits=1 if last is not None and first_mono - last <= 300 else 0,
            )
            self._started_mono = first_mono
            self.last_good_mono = p.monotonic_seconds
            self.last_good_time = p.timestamp
            self.candidate = None
            events.append(self.active)
        return events

    def flush(self, monotonic_seconds: float) -> list[SessionSignal]:
        if not isfinite(monotonic_seconds) or monotonic_seconds < self.last_mono:
            raise ValueError("invalid flush monotonic time")
        if self.active and monotonic_seconds - self.last_good_mono >= self.dropout_seconds:
            return [self._finish()]
        return []

    def close_session(self) -> list[SessionSignal]:
        """EOF/explicit stop: end at last observed positive frame, never invent elapsed eating."""
        self.candidate = None
        return [self._finish()] if self.active is not None else []
