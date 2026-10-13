"""Canonical capture metadata; requested targets are never ground-truth labels."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

IDENTITY = ("OWNER_CAT", "OTHER_CAT", "OTHER_OBJECT", "UNKNOWN", "SKIP")
BEHAVIOR = ("EATING", "DRINKING", "NEAR_FOOD", "NEAR_WATER", "LEAVING", "OTHER", "UNSURE", "SKIP")


class SessionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal[1] = 1
    session_id: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    recorded_at: datetime
    camera_source: Literal["CAMERA", "VIDEO"]
    camera_device: str = Field(min_length=1, max_length=512)
    resolution: tuple[int, int] | None = None
    fps: float | None = Field(default=None, gt=0, le=1000)
    identity_target: Literal["OWNER_CAT", "OTHER_CAT", "OTHER_OBJECT", "UNKNOWN", "SKIP"]
    behavior_target: Literal["EATING", "DRINKING", "NEAR_FOOD", "NEAR_WATER", "LEAVING", "OTHER", "UNSURE", "SKIP"]
    food_type: str | None = Field(default=None, max_length=64)
    lighting: str | None = Field(default=None, max_length=64)
    distance: str | None = Field(default=None, max_length=64)
    view_angle: str | None = Field(default=None, max_length=64)
    occlusion: str | None = Field(default=None, max_length=64)
    environment: str | None = Field(default=None, max_length=256)
    notes: str | None = Field(default=None, max_length=512)
    usable: bool = False
    source_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_hash_kind: Literal["VIDEO_FILE_SHA256", "SAMPLED_FRAME_STREAM_SHA256"]
    duration_seconds: float = Field(gt=0, le=3600)
    sampling_interval_seconds: float = Field(gt=0, le=3600)
    minimum_spacing_seconds: float = Field(ge=0, le=3600)
    max_frames: int = Field(ge=1, le=1000)
    sample_count: int = Field(default=0, ge=0, le=1000)
    stop_reason: str = Field(default="DRY_RUN", max_length=64)

    @field_validator("recorded_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must have a timezone")
        return value.astimezone(timezone.utc)

    @field_validator("resolution")
    @classmethod
    def dimensions(cls, value):
        if value is not None and (not all(0 < n <= 4096 for n in value) or value[0]*value[1] > 8_500_000):
            raise ValueError("resolution exceeds capture budget")
        return value
