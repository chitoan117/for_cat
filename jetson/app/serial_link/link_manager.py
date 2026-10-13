"""Bounded request correlation and link observability above a transport."""

from collections import deque
from threading import RLock

from app.serial_link.protocol import Command, Frame, ProtocolError, decode, encode
from app.serial_link.transport import SerialTransport
from app.status import LinkState
from app.observability import WarningLimiter, get_logger


class LinkManager:
    def __init__(self, transport: SerialTransport, max_pending: int = 256):
        if not 1 <= max_pending <= 10000:
            raise ValueError("max_pending out of range")
        self.transport = transport
        self.state = LinkState.UNCONFIGURED
        self.sent = self.received = self.failures = 0
        self._pending: deque[int] = deque(maxlen=max_pending)
        self._lock = RLock()
        self.warnings = WarningLimiter()

    @property
    def pending(self) -> tuple[int, ...]:
        with self._lock:
            return tuple(self._pending)

    def mark_pending(self, request_id: int) -> None:
        with self._lock:
            if request_id not in self._pending:
                if len(self._pending) == self._pending.maxlen:
                    raise OverflowError("pending request capacity reached")
                self._pending.append(request_id)

    def mark_done(self, request_id: int) -> None:
        with self._lock:
            try:
                self._pending.remove(request_id)
            except ValueError:
                pass

    def exchange(self, request_id: int, command: Command) -> Frame:
        with self._lock:
            self.state = LinkState.CONNECTING if self.state in (LinkState.UNCONFIGURED, LinkState.OFFLINE) else self.state
            self.sent += 1
            try:
                reply = decode(self.transport.exchange(encode(Frame(request_id, command))))
                if reply.request_id != request_id:
                    raise ProtocolError("mismatched request ID")
            except (ConnectionError, TimeoutError):
                self.failures += 1
                self.state = LinkState.OFFLINE
                self.warnings.warn(get_logger(), "serial_offline", "serial link unavailable",
                                   {"component": "serial", "request_id": request_id, "event_type": "OFFLINE"})
                raise
            except (ProtocolError, ValueError):
                self.failures += 1
                self.state = LinkState.DEGRADED
                raise
            self.received += 1
            self.state = LinkState.ONLINE
            return reply

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"sent": self.sent, "received": self.received,
                    "failures": self.failures, "pending": len(self._pending)}
