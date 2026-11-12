from app.camera.usb_webcam import UsbWebcamCameraProvider


class Image:
    shape = (2, 3, 3)

    def tobytes(self):
        return bytes(18)


class FakeCapture:
    def __init__(self, device, *, opened=True):
        self.device = device
        self.opened = opened
        self.readable = True

    def isOpened(self):
        return self.opened

    def read(self):
        return (True, Image()) if self.readable else (False, None)

    def release(self):
        self.opened = False


def test_camera_provider_open_read_health_close_without_hardware():
    captures = []

    def factory(device):
        cap = FakeCapture(device)
        captures.append(cap)
        return cap

    camera = UsbWebcamCameraProvider("/dev/video-test", capture_factory=factory)
    assert camera.open()
    assert captures[0].device == "/dev/video-test"
    frame = camera.capture()
    assert (frame.width, frame.height, frame.synthetic, frame.pixel_format) == (3, 2, False, "BGR")
    assert camera.health() == "ONLINE"
    captures[-1].readable = False
    assert camera.read() is None
    camera.close()
    assert not captures[-1].opened


def test_unavailable_camera_reports_offline_without_raising():
    camera = UsbWebcamCameraProvider("/dev/video-test",
                                      capture_factory=lambda device: FakeCapture(device, opened=False))
    assert camera.health() == "NOT_CONNECTED"
    assert camera.open() is False
    assert camera.health() == "OFFLINE"


def test_windows_index_zero_is_not_rejected_as_false():
    captured = []

    def factory(index):
        captured.append(index)
        return FakeCapture(index)

    camera = UsbWebcamCameraProvider(0, capture_factory=factory)
    assert camera.open()
    assert captured == [0]
    camera.close()
