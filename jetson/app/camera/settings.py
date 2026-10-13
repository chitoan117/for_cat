from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class CaptureSettings:
    width: int = 640
    height: int = 480
    fps: float = 10
    backend: str = "AUTO"
    pipeline: str | None = None
    read_timeout_ms: int = 1000
    failure_threshold: int = 3

    def __post_init__(self):
        if not 1 <= self.width <= 3840 or not 1 <= self.height <= 2160 or \
                not isfinite(self.fps) or not 0 < self.fps <= 60:
            raise ValueError("invalid bounded camera resolution/FPS")
        if self.backend not in ("AUTO", "V4L2", "GSTREAMER"):
            raise ValueError("camera backend must be AUTO, V4L2 or GSTREAMER")
        if not 50 <= self.read_timeout_ms <= 10000 or not 1 <= self.failure_threshold <= 30:
            raise ValueError("invalid camera failure/timeout bounds")
        if self.backend == "GSTREAMER" and (not self.pipeline or len(self.pipeline) > 2048):
            raise ValueError("GSTREAMER requires a trusted local bounded pipeline ending in appsink")
        if self.pipeline and ("appsink" not in self.pipeline or "\n" in self.pipeline):
            raise ValueError("GStreamer pipeline must be single-line and use appsink")
        if self.pipeline and any(sink in self.pipeline.lower() for sink in ("filesink", "multifilesink", "splitmuxsink")):
            raise ValueError("capture backend cannot include automatic recording sinks")
