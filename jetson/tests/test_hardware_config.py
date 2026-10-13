import pytest
from fastapi.testclient import TestClient

from app.config import HardwareConfig
from app.main import create_app
from app.serial_link.mock_transport import MockEsp32Transport
from app.storage.event_store import InMemoryEventStore


@pytest.mark.parametrize("values, expected", [
    ({}, ("MOCK", None, "MOCK", None)),
    ({"CAMERA_PROVIDER": "usb", "CAMERA_DEVICE": "/dev/video8",
      "ESP32_TRANSPORT": "serial", "ESP32_SERIAL_DEVICE": "/dev/ttyACM3"},
     ("USB", "/dev/video8", "SERIAL", "/dev/ttyACM3")),
])
def test_configuration_parsing(values, expected):
    config = HardwareConfig.from_env(values)
    assert (config.camera_provider, config.camera_device,
            config.esp32_transport, config.esp32_serial_device) == expected


@pytest.mark.parametrize("values", [
    {"CAMERA_PROVIDER": "USB"}, {"ESP32_TRANSPORT": "SERIAL"},
    {"CAMERA_PROVIDER": "UNKNOWN"}, {"ESP32_TRANSPORT": "UNKNOWN"},
])
def test_invalid_or_missing_devices(values):
    with pytest.raises(ValueError):
        HardwareConfig.from_env(values)


def test_video_path_cors_and_bounds():
    config = HardwareConfig.from_env({"CAMERA_PROVIDER": "video", "VIDEO_REPLAY_PATH": "sample.mp4",
                                      "CORS_ORIGINS": "https://example.test"})
    assert config.camera_provider == "VIDEO" and config.video_file == "sample.mp4"
    assert config.cors_origins == ("https://example.test",)
    assert HardwareConfig.from_env({"CAMERA_PROVIDER": "USB", "CAMERA_DEVICE": "0"}).camera_device == 0
    for bad in ({"CAMERA_PROVIDER": "VIDEO"}, {"CORS_ORIGINS": "*"},
                {"ESP32_SERIAL_BAUD": "9600"}, {"EVENT_RETENTION": "0"},
                {"PREFERENCE_MIN_SESSIONS": "1"}):
        with pytest.raises(ValueError):
            HardwareConfig.from_env(bad)


def test_mock_status_is_labeled_and_sensors_unconnected():
    with TestClient(create_app(store=InMemoryEventStore(), hardware=HardwareConfig())) as client:
        body = client.get("/api/v1/status").json()
        assert body["camera"] == "MOCK"
        assert body["esp32"] == "MOCK"
        assert body["sensors"] == "NOT_CONNECTED"
        assert client.get("/api/v1/health").json() == {"status": "ok"}


@pytest.mark.parametrize("camera_result", ["ONLINE", "OFFLINE"])
def test_status_mapping_disconnect_and_reconnect_without_claiming_hardware(camera_result):
    class StubCamera:
        def health(self):
            return camera_result

        def close(self):
            pass

    serial_stub = MockEsp32Transport()
    config = HardwareConfig(esp32_transport="SERIAL", esp32_serial_device="test-only")
    with TestClient(create_app(store=InMemoryEventStore(), transport=serial_stub,
                               camera=StubCamera(), hardware=config)) as client:
        assert client.get("/api/v1/status").json()["esp32"] == "ONLINE"
        serial_stub.online = False
        offline = client.get("/api/v1/status").json()
        assert offline["esp32"] == "OFFLINE" and not offline["esp32_online"]
        assert offline["camera"] == camera_result
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        serial_stub.online = True
        assert client.get("/api/v1/status").json()["esp32"] == "ONLINE"
        # Even a working serial link must not receive a Phase 2 feed request.
        assert client.post("/api/v1/feed/manual").json()["state"] == "REJECTED"
        assert serial_stub.feeds == {}
