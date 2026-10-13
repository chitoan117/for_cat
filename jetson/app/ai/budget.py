from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ProcessingBudget:
    inference_fps: float = 0  # direct legacy/tests: 0 disables pacing; app config uses explicit bounded FPS
    max_width: int = 640
    max_height: int = 480
    frame_skip: int = 1
    queue_depth: int = 1
    max_age_seconds: float = 1

    def __post_init__(self):
        if not isfinite(self.inference_fps) or not 0 <= self.inference_fps <= 30 or \
                not 1 <= self.max_width <= 1920 or not 1 <= self.max_height <= 1080 or \
                not 1 <= self.frame_skip <= 60 or self.queue_depth != 1 or \
                not isfinite(self.max_age_seconds) or not 0 < self.max_age_seconds <= 30:
            raise ValueError("invalid bounded processing budget")
