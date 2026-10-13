from datetime import datetime, timezone

from app.camera.base import CameraFrame, CameraProvider


class MockCameraProvider(CameraProvider):
    def open(self) -> bool:
        return True

    def read(self) -> CameraFrame:
        return self.capture()

    def health(self) -> str:
        return "MOCK"

    def close(self) -> None:
        pass

    def capture(self) -> CameraFrame:
        return CameraFrame(
            captured_at=datetime.now(timezone.utc),
            pixels=bytes([0] * 12),  # 2 x 2 RGB synthetic black image
            width=2,
            height=2,
            synthetic=True,
        )
