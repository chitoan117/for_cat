from typing import Protocol


class SerialTransport(Protocol):
    def exchange(self, request: bytes) -> bytes:
        """Send one frame and return one correlated reply; raise TimeoutError/ConnectionError."""
