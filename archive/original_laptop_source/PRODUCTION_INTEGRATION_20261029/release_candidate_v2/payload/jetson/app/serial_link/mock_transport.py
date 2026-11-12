from app.serial_link.protocol import Command, FeedCode, Frame, decode, encode


class MockEsp32Transport:
    """Explicitly controlled outcomes; receiving ACK never dispenses food."""

    def __init__(self):
        self.online = True
        self.timeout = False
        self.reject_requests = False
        self.feeds: dict[int, FeedCode] = {}

    def complete_feed(self, request_id: int, outcome: FeedCode) -> None:
        if outcome == FeedCode.PENDING:
            raise ValueError("completion must be terminal")
        if request_id not in self.feeds:
            raise KeyError(request_id)
        self.feeds[request_id] = outcome

    def exchange(self, request: bytes) -> bytes:
        if not self.online:
            raise ConnectionError("mock ESP32 offline")
        if self.timeout:
            raise TimeoutError("mock ESP32 timed out")
        frame = decode(request)
        if frame.command == Command.PING:
            reply = Frame(frame.request_id, Command.ACK, bytes([Command.PING]))
        elif frame.command == Command.GET_STATUS:
            reply = Frame(frame.request_id, Command.SYSTEM_STATUS, b"\x01")  # mock ready
        elif frame.command == Command.FEED_REQUEST:
            if self.reject_requests:
                reply = Frame(frame.request_id, Command.NACK, b"\x04")  # busy/rejected
            else:
                if frame.request_id not in self.feeds and len(self.feeds) >= 10000:
                    return encode(Frame(frame.request_id, Command.NACK, b"\x04"))
                self.feeds.setdefault(frame.request_id, FeedCode.PENDING)  # duplicate cannot erase terminal result
                reply = Frame(frame.request_id, Command.ACK, bytes([Command.FEED_REQUEST]))
        elif frame.command == Command.FEED_STATUS:
            if frame.request_id in self.feeds:
                reply = Frame(frame.request_id, Command.FEED_STATUS, bytes([self.feeds[frame.request_id]]))
            else:
                reply = Frame(frame.request_id, Command.NACK, b"\x05")  # unknown ID
        else:
            reply = Frame(frame.request_id, Command.NACK, b"\x03")  # unsupported command
        return encode(reply)
