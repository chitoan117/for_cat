"""Bring-up-tool logic tests only; no physical serial/camera/sensor access."""

from pathlib import Path

import pytest

from app.serial_link.mock_transport import MockEsp32Transport
from app.serial_link.protocol import Command, Frame, decode, encode
from tools.test_serial import run_safe_probe


def test_m3_probe_sends_only_safe_commands_and_reports_measurements():
    sent = []
    class Probe(MockEsp32Transport):
        def exchange(self, request):
            sent.append(decode(request).command)
            return super().exchange(request)
    report = run_safe_probe(Probe(), count=2, interval=0.25, sleep=lambda _: None)
    assert sent == [Command.PING, Command.GET_STATUS] * 2
    assert report["protocol_probe_passed"] and report["feed_requests_sent"] == 0
    assert all(record["crc_valid"] and record["request_correlated"] for record in report["records"])
    assert all(record["round_trip_ms"] >= 0 for record in report["records"])


@pytest.mark.parametrize("failure", ["timeout", "disconnect", "stale", "crc"])
def test_m3_probe_never_reports_pass_for_failure(failure):
    class BadLink:
        def exchange(self, request):
            frame = decode(request)
            if failure == "timeout": raise TimeoutError("synthetic timeout")
            if failure == "disconnect": raise ConnectionError("synthetic unplug")
            if failure == "stale": return encode(Frame(frame.request_id + 1, Command.ACK, b"\x01"))
            raw = bytearray(encode(Frame(frame.request_id, Command.ACK, b"\x01")))
            raw[-1] ^= 1
            return bytes(raw)
    report = run_safe_probe(BadLink(), count=1)
    assert report["protocol_probe_passed"] is False
    assert all(record["result"] == "FAIL" for record in report["records"])
    assert report["timeouts"] == (2 if failure == "timeout" else 0)
    assert report["feed_requests_sent"] == 0


def test_first_flash_bridge_profile_is_hard_disabled_and_distinct_from_native():
    import configparser
    root = Path(__file__).resolve().parents[2]
    ini = configparser.ConfigParser(interpolation=None)
    ini.read(root / "esp32" / "platformio.ini")
    flags = ini["env:esp32s3_n16r8_hw_safe_uart"]["build_flags"]
    assert "-DFORR_NATIVE_USB=0" in flags and "-DARDUINO_USB_CDC_ON_BOOT=0" in flags
    assert "-DFORR_HW_SAFE=1" in flags and "SIMULATED_SENSORS" not in flags
    assert "-DACTUATOR_OUTPUTS_ENABLED=0" in ini["env"]["build_flags"]


def test_ascii_monitor_banner_does_not_change_binary_uart_frame_decode():
    from app.serial_link.real_transport import RealEsp32SerialTransport
    from jetson.tests.test_real_transport import FakePort
    class BannerPort(FakePort):
        def write(self, request):
            count = super().write(request)
            self.responses = bytearray(b"FORR_CAT actuator_enabled=0 simulation=0 safety=SAFE_BUILD_ACTUATORS_DISABLED\r\n") + self.responses
            return count
    link = RealEsp32SerialTransport("synthetic", serial_factory=BannerPort, startup_delay=0)
    report = run_safe_probe(link, count=1)
    assert report["protocol_probe_passed"] and report["feed_requests_sent"] == 0
    link.close()
