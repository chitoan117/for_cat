import pytest

from app.serial_link.protocol import Command, Frame, decode, encode
from app.serial_link.real_transport import RealEsp32SerialTransport


class FakePort:
    def __init__(self, *, mode="normal", **kwargs):
        self.options = kwargs
        self.mode = mode
        self.responses = bytearray()
        self.closed = False

    def reset_input_buffer(self):
        self.responses.clear()

    def write(self, request):
        if self.mode == "unplugged":
            raise OSError("device disconnected")
        frame = decode(request)
        if self.mode != "silent":
            reply_id = frame.request_id + 1 if self.mode == "wrong_id" else frame.request_id
            reply_command = Command.ACK if frame.command == Command.PING else Command.SYSTEM_STATUS
            reply_payload = bytes([frame.command]) if frame.command == Command.PING else b"\x01"
            reply = bytearray(encode(Frame(reply_id, reply_command, reply_payload)))
            if self.mode == "bad_crc":
                reply[-1] ^= 1
            self.responses.extend(reply)
        return len(request)

    def read(self, count):
        if not self.responses:
            return b""
        # A serial port may return fewer bytes than requested.
        part = bytes(self.responses[:1])
        del self.responses[:1]
        return part

    def close(self):
        self.closed = True


def test_real_transport_framing_partial_reads_and_request_ids():
    ports = []

    def factory(**kwargs):
        port = FakePort(**kwargs)
        ports.append(port)
        return port

    link = RealEsp32SerialTransport("/dev/tty-test", serial_factory=factory, startup_delay=0, timeout=0.1)
    for command in (Command.PING, Command.GET_STATUS, Command.PING):
        request = Frame(234, command)
        response = decode(link.exchange(encode(request)))
        assert response.request_id == 234
        assert response.command == (Command.ACK if command == Command.PING else Command.SYSTEM_STATUS)
    assert len(ports) == 1
    assert ports[0].options["baudrate"] == 115200
    assert ports[0].options["port"] == "/dev/tty-test"
    link.close()
    assert ports[0].closed


@pytest.mark.parametrize("mode, error", [
    ("unplugged", ConnectionError), ("silent", TimeoutError),
    ("wrong_id", TimeoutError), ("bad_crc", ValueError),
])
def test_serial_failures_close_port_and_allow_reconnect(mode, error):
    modes = [mode, "normal"]
    ports = []

    def factory(**kwargs):
        port = FakePort(mode=modes.pop(0), **kwargs)
        ports.append(port)
        return port

    link = RealEsp32SerialTransport("/dev/tty-test", serial_factory=factory, startup_delay=0, timeout=0.01)
    request = encode(Frame(1, Command.PING))
    with pytest.raises(error):
        link.exchange(request)
    assert ports[0].closed
    assert decode(link.exchange(request)) == Frame(1, Command.ACK, b"\x01")
    link.close()
