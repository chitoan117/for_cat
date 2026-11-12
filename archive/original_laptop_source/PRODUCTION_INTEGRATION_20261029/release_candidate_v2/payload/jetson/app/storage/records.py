"""Typed UTC session records; no observations are generated automatically."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.ai.models import Identity
from app.behavior.models import Behavior


class TimedRecord(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    @field_validator("*", mode="after")
    @classmethod
    def aware_timestamps(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("timestamps must be timezone-aware")
            return value.astimezone(timezone.utc)
        return value


class FeedingSession(TimedRecord):
    session_id: str = Field(min_length=1, max_length=64)
    cat_identity: Identity = Identity.UNKNOWN
    food_type: str | None = Field(default=None, max_length=64)
    requested_grams: float | None = Field(default=None, ge=0, le=1000)
    dispensed_grams: float | None = Field(default=None, ge=0, le=1000)
    weight_before_eating: float | None = Field(default=None, ge=0)
    weight_after_eating: float | None = Field(default=None, ge=0)
    estimated_consumed_grams: float | None = Field(default=None, ge=0)
    requested_at: datetime
    dispense_started_at: datetime | None = None
    dispense_finished_at: datetime | None = None
    eating_started_at: datetime | None = None
    eating_finished_at: datetime | None = None
    result: str = Field(default="UNKNOWN", max_length=32)
    reject_reason: str | None = Field(default=None, max_length=128)
    source: str = Field(default="UNVALIDATED", max_length=32)
    approach_delay_seconds: float | None = Field(default=None, ge=0)
    repeat_visits: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_interval(self):
        for start, end in ((self.dispense_started_at, self.dispense_finished_at),
                           (self.eating_started_at, self.eating_finished_at)):
            if start is not None and end is not None and end < start:
                raise ValueError("session end precedes start")
        return self


class DrinkingSession(TimedRecord):
    session_id: str = Field(min_length=1, max_length=64)
    cat_identity: Identity = Identity.UNKNOWN
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: str | None = Field(default=None, max_length=256)
    source: str = Field(default="UNVALIDATED", max_length=32)

    @model_validator(mode="after")
    def check_interval(self):
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("drinking end precedes start")
        return self


class BehaviorRecord(TimedRecord):
    session_id: str = Field(min_length=1, max_length=64)
    cat_identity: Identity = Identity.UNKNOWN
    behavior: Behavior
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    feeding_session_id: str | None = Field(default=None, max_length=64)
    food_type: str | None = Field(default=None, max_length=64)
    source: str = Field(default="UNVALIDATED", max_length=32)
    completion_reason: str = Field(default="BEHAVIOR_STOPPED", max_length=32)
    estimated_consumed_grams: float | None = Field(default=None, ge=0)
    weight_evidence_validated: bool = False


class FoodType(BaseModel):
    food_type: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    description: str | None = Field(default=None, max_length=256)


class PreferenceSummary(TimedRecord):
    food_type: str = Field(min_length=1, max_length=64)
    calculated_at: datetime
    status: Literal["SUFFICIENT_DATA", "INSUFFICIENT_DATA"]
    sessions: int = Field(ge=0)
    trend: Literal["HIGH", "MODERATE", "LOW"] | None = None
    evidence: dict[str, float | int | None] = Field(default_factory=dict)
    method: str = Field(default="EXPERIMENTAL", max_length=64)
