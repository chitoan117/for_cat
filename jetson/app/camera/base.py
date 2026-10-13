from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CameraFrame:
    captured_at: datetime
    pixels: bytes
    width: int
    height: int
    synthetic: bool
    pixel_format: str = "RGB"
    monotonic_seconds: float | None = None
    media_seconds: float | None = None


class CameraProvider(ABC):
    @abstractmethod
    def open(self) -> bool:
        """Open the device, or report that it cannot be opened."""

    @abstractmethod
    def read(self) -> CameraFrame | None:
        """Read one frame or report failure."""

    @abstractmethod
    def health(self) -> str:
        """Return MOCK, ONLINE or OFFLINE."""

    @abstractmethod
    def close(self) -> None:
        """Release resources."""

    @abstractmethod
    def capture(self) -> CameraFrame:
        """Return one frame."""
