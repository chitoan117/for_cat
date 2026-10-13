from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.ai.models import Identity


class Behavior(str, Enum):
    EATING = "EATING"
    DRINKING = "DRINKING"
    NEAR_FOOD = "NEAR_FOOD"
    NEAR_WATER = "NEAR_WATER"
    LEAVING = "LEAVING"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class BehaviorObservation(BaseModel):
    timestamp: datetime
    identity: Identity = Identity.UNKNOWN
    behavior: Behavior = Behavior.UNKNOWN
    feeding_session_id: str | None = None
    food_type: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    food_roi: bool = False
    water_roi: bool = False


class VisitRecord(BehaviorObservation):
    eating_start: datetime | None = None
    eating_end: datetime | None = None
    eating_duration_seconds: float | None = Field(default=None, ge=0)
    drinking_start: datetime | None = None
    drinking_end: datetime | None = None
    drinking_duration_seconds: float | None = Field(default=None, ge=0)
    food_dispensed_grams: float | None = Field(default=None, ge=0)
    food_remaining_grams: float | None = Field(default=None, ge=0)
    estimated_food_consumed_grams: float | None = Field(default=None, ge=0)
    approach_delay_seconds: float | None = Field(default=None, ge=0)
    visit_duration_seconds: float | None = Field(default=None, ge=0)
    repeat_visits: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_intervals(self):
        for prefix in ("eating", "drinking"):
            start = getattr(self, f"{prefix}_start")
            end = getattr(self, f"{prefix}_end")
            if start is not None and end is not None and end < start:
                raise ValueError(f"{prefix}_end precedes {prefix}_start")
        return self


class FoodPreferenceEvidence(BaseModel):
    """Evidence across sessions only; no preference score or conclusion."""

    food_type: str
    feeding_session_ids: list[str]
    percentage_consumed: list[float | None] = Field(default_factory=list)
    approach_delay_seconds: list[float | None] = Field(default_factory=list)
    eating_duration_seconds: list[float | None] = Field(default_factory=list)
    leftover_grams: list[float | None] = Field(default_factory=list)
    repeat_visits: list[int | None] = Field(default_factory=list)
