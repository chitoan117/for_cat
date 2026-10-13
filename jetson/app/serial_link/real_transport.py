"""Synchronous pyserial framing with bounded reads and reconnect on failure."""

import time
from math import isfinite
from threading import RLock
from typing import Callable

from app.config import MAX_PAYLOAD
from app.serial_link.protocol import START, Frame, ProtocolError, decode


class ReconnectDeferred(ConnectionError):
    pass


class RealEsp32SerialTransport:
    def __init__(
        self, device: str, timeout: float = 1.0, startup_delay: float = 2.0,
        serial_factory: Callable | None = None,
        reconnect_backoff_seconds: float = 0,
    ):
        if not device:
            raise ValueError("serial device path is required")
        if not isfinite(timeout) or not 0 < timeout <= 30 or not isfinite(startup_delay) or not 0 <= startup_delay <= 30 or not 0 <= reconnect_backoff_seconds <= 30:
            raise ValueError("invalid serial timeout or startup delay")
        self.device = device
        self.timeout = timeout
        self.startup_delay = startup_delay
        self._factory = serial_factory
        self._port = None
        self._lock = RLock()
        self.reconnect_backoff_seconds = reconnect_backoff_seconds
        self._retry_at = 0.0

    def _connect(self) -> None:
        if self._port is not None:
            return
        if time.monotonic() < self._retry_at:
            raise ReconnectDeferred("serial reconnect backoff active")
        if self._factory is None:
            import serial  # optional when MOCK is selected
            self._factory = serial.Serial
        self._port = self._factory(
            port=self.device, baudrate=115200, timeout=min(self.timeout, 0.1),
            write_timeout=self.timeout,
        )
        # Many USB ESP32 boards reset when the serial port is first opened.
        if self.startup_delay:
            time.sleep(self.startup_delay)
        self._port.reset_input_buffer()

    def close(self) -> None:
        with self._lock:
            if self._port is not None:
                try:
                    self._port.close()
                except Exception:
                    pass  # a vanished serial device may also fail on close
                finally:
                    self._port = None

    def _read_exact(self, count: int, deadline: float) -> bytes:
        output = bytearray()
        while len(output) < count:
            if time.monotonic() >= deadline:
                raise TimeoutError("ESP32 response timed out")
            part = self._port.read(count - len(output))
            if part:
                output.extend(part)
        return bytes(output)

    def _read_frame(self, deadline: float) -> Frame:
        # Skip startup diagnostics or leftover bytes until the start marker.
        prefix = b""
        while True:
            byte = self._read_exact(1, deadline)
            prefix = (prefix + byte)[-2:]
            if prefix == START:
                break
        header = self._read_exact(8, deadline)
        length = int.from_bytes(header[6:8], "little")
        if length > MAX_PAYLOAD:
            raise ProtocolError("ESP32 response payload too long")
        raw = START + header + self._read_exact(length + 2, deadline)
        return decode(raw)

    def exchange(self, request: bytes) -> bytes:
        expected_id = decode(request).request_id
        with self._lock:
            try:
                self._connect()
                written = self._port.write(request)
                if written != len(request):
                    raise TimeoutError("incomplete ESP32 serial write")
                deadline = time.monotonic() + self.timeout
                while True:
                    reply = self._read_frame(deadline)
                    if reply.request_id == expected_id:
                        # Return the original bytes only after validating the frame.
                        from app.serial_link.protocol import encode
                        return encode(reply)
                    # Stale reply: never pass it to the caller as this request's result.
            except ReconnectDeferred:
                raise  # frequent status polling must not keep extending the retry deadline
            except (TimeoutError, ProtocolError):
                self.close()
                self._retry_at = time.monotonic() + self.reconnect_backoff_seconds
                raise
            except Exception as exc:
                self.close()
                self._retry_at = max(self._retry_at, time.monotonic() + self.reconnect_backoff_seconds)
                raise ConnectionError(f"ESP32 serial device unavailable: {self.device}") from exc
