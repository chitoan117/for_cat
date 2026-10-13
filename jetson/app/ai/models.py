from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from app.vision.geometry import NormalizedBox


class Identity(str, Enum):
    OWNER_CAT = "OWNER_CAT"
    OTHER_CAT = "OTHER_CAT"
    OTHER_OBJECT = "OTHER_OBJECT"
    NO_SUBJECT = "NO_SUBJECT"
    UNKNOWN = "UNKNOWN"


class Recognition(BaseModel):
    timestamp: datetime
    identity: Identity = Identity.UNKNOWN
    confidence: float | None = Field(default=None, ge=0, le=1)
    model_version: str | None = None
    bounding_box: NormalizedBox | None = None
    ambiguous: bool = False
