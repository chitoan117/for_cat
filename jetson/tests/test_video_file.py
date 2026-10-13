from app.camera.video_file import VideoFileCameraProvider
from app.camera.base import CameraFrame
from tools.replay_video import replay
from datetime import datetime, timedelta, timezone


class Image:
    shape = (2, 3, 3)

    def tobytes(self):
        return b"\x00" * 18


class FakeVideo:
    def __init__(self, path):
        self.index = 0
        self.closed = False

    def isOpened(self):
        return True

    def get(self, prop):
        return self.index * 500 if prop == 0 else 2

    def read(self):
        if self.index >= 2:
            return False, None
        self.index += 1
        return True, Image()

    def release(self):
        self.closed = True


def test_video_replay_timestamps_eof_and_explicit_reset(tmp_path):
    path = tmp_path / "synthetic-file.mp4"
    path.write_bytes(b"synthetic test stub")  # no video decoder needed
    videos = []

    def factory(path):
        capture = FakeVideo(path)
        videos.append(capture)
        return capture

    provider = VideoFileCameraProvider(str(path), capture_factory=factory)
    assert provider.health() == "MOCK"
    first, second = provider.read(), provider.read()
    assert first.synthetic is False  # recorded pixels are not fabricated
    assert (first.width, first.height, first.pixel_format) == (3, 2, "BGR")
    assert (second.captured_at - first.captured_at).total_seconds() == 0.5
    assert provider.read() is None and provider.health() == "OFFLINE"
    assert len(videos) == 1 and videos[0].closed
    provider.reset()
    assert provider.read() is not None
    provider.close()


def test_replay_tool_uses_mock_predictions_without_fabrication():
    class Frames:
        def __init__(self):
            self.count = 0

        def open(self):
            return True

        def read(self):
            if self.count >= 3:
                return None
            timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=self.count)
            self.count += 1
            return CameraFrame(timestamp, b"\x00" * 12, 2, 2, False)

        def close(self):
            pass

    result = replay("synthetic-replay", provider=Frames(), max_frames=3)
    assert result["status"] == "REPLAY_ONLY_NO_AI_VALIDATION"
    assert result["frames"] == 3 and result["signals"] == []
