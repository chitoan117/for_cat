"""Conservative cat detector→crop→identity boundary, no detector/runtime bundled."""

from dataclasses import dataclass
from typing import Protocol

from app.ai.models import Identity, Recognition
from app.camera.base import CameraFrame
from app.camera.frame_ops import crop_frame
from app.vision.geometry import NormalizedBox


@dataclass(frozen=True)
class CatDetection:
    box: NormalizedBox
    confidence: float


class CatDetector(Protocol):
    def load(self) -> bool: ...
    def predict(self, frame: CameraFrame) -> list[CatDetection]: ...
    def health(self) -> str: ...
    def close(self) -> None: ...


class DetectorIdentityModel:
    def __init__(self, detector: CatDetector, classifier, detector_threshold: float | None,
                 identity_threshold: float | None):
        self.detector, self.classifier = detector, classifier
        self.detector_threshold, self.identity_threshold = detector_threshold, identity_threshold
        self.state = "NOT_CONFIGURED"

    def load(self) -> bool:
        if self.detector_threshold is None or self.identity_threshold is None:
            return False
        if not 0 <= self.detector_threshold <= 1 or not 0 <= self.identity_threshold <= 1:
            raise ValueError("validated thresholds must be bounded")
        if not self.detector.load():
            return False
        load = getattr(self.classifier, "load", None)
        if load is not None and not load():
            self.detector.close()
            return False
        self.state = "NOT_VALIDATED"
        return True

    def predict(self, frame: CameraFrame) -> Recognition:
        if self.state != "NOT_VALIDATED":
            raise RuntimeError("detector/classifier not configured")
        detections = self.detector.predict(frame)
        if not detections:
            return Recognition(timestamp=frame.captured_at, identity=Identity.NO_SUBJECT)
        # Even a low-confidence second cat makes the scene non-authoritative.
        if len(detections) != 1:
            return Recognition(timestamp=frame.captured_at, identity=Identity.UNKNOWN, ambiguous=True)
        detection = detections[0]
        if not 0 <= detection.confidence <= 1 or detection.confidence < self.detector_threshold:
            return Recognition(timestamp=frame.captured_at, identity=Identity.UNKNOWN)
        try:
            crop = crop_frame(frame, detection.box)
        except ValueError:
            return Recognition(timestamp=frame.captured_at, identity=Identity.UNKNOWN, ambiguous=True)
        recognition = self.classifier.predict(crop)
        if recognition.confidence is None or recognition.confidence < self.identity_threshold:
            return Recognition(timestamp=frame.captured_at, identity=Identity.UNKNOWN,
                               bounding_box=detection.box)
        return recognition.model_copy(update={"bounding_box": detection.box, "timestamp": frame.captured_at})

    def health(self) -> str:
        return self.state

    def close(self) -> None:
        try:
            self.detector.close()
        finally:
            close = getattr(self.classifier, "close", None)
            if close is not None:
                close()
            self.state = "NOT_CONFIGURED"
