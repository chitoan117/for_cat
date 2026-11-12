"""Wire format: A5 5A | version:u8 | id:u32 LE | command:u8 | length:u16 LE | payload | CRC16 LE."""

from dataclasses import dataclass
from enum import IntEnum
from struct import pack, unpack_from
from math import isfinite

from app.config import MAX_PAYLOAD

START = b"\xA5\x5A"
VERSION = 1
MIN_FRAME = 12


class ProtocolError(ValueError):
    pass


class Command(IntEnum):
    PING = 1
    GET_STATUS = 2
    FEED_REQUEST = 3
    FEED_STATUS = 4
    SYSTEM_STATUS = 5
    ACK = 6
    NACK = 7


class FeedCode(IntEnum):
    PENDING = 0
    SUCCESS = 1
    REJECTED = 2
    ERROR = 3


@dataclass(frozen=True)
class Frame:
    request_id: int
    command: Command
    payload: bytes = b""


def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE, init FFFF, polynomial 1021, no reflection/xorout."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode(frame: Frame) -> bytes:
    if not 0 <= frame.request_id <= 0xFFFFFFFF:
        raise ProtocolError("request ID out of range")
    if len(frame.payload) > MAX_PAYLOAD:
        raise ProtocolError("payload too long")
    body = pack("<BIBH", VERSION, frame.request_id, int(frame.command), len(frame.payload)) + frame.payload
    return START + body + pack("<H", crc16(body))


def decode(data: bytes) -> Frame:
    if len(data) < MIN_FRAME or data[:2] != START:
        raise ProtocolError("invalid start or truncated frame")
    version, request_id, command, length = unpack_from("<BIBH", data, 2)
    if version != VERSION:
        raise ProtocolError("unsupported version")
    if length > MAX_PAYLOAD or len(data) != MIN_FRAME + length:
        raise ProtocolError("invalid frame length")
    if unpack_from("<H", data, len(data) - 2)[0] != crc16(data[2:-2]):
        raise ProtocolError("invalid CRC")
    try:
        kind = Command(command)
    except ValueError as exc:
        raise ProtocolError("unknown command") from exc
    return Frame(request_id, kind, data[10:-2])


class FrameStreamDecoder:
    """Incremental, bounded v1 parser for noisy serial/replay streams."""

    def __init__(self, max_buffer: int = 512, partial_timeout: float = 0.25):
        if not MIN_FRAME + MAX_PAYLOAD <= max_buffer <= 8192 or not isfinite(partial_timeout) or partial_timeout <= 0:
            raise ValueError("invalid parser bounds")
        self.max_buffer = max_buffer
        self.partial_timeout = partial_timeout
        self.buffer = bytearray()
        self.last_byte_at: float | None = None
        self.discarded = 0

    def expire(self, monotonic_seconds: float) -> None:
        if self.buffer and self.last_byte_at is not None and \
                monotonic_seconds - self.last_byte_at >= self.partial_timeout:
            # A timed-out outer candidate is no longer authoritative. Only now may
            # later START bytes be resynchronized; they can legally occur in payload.
            self.discarded += 1
            del self.buffer[:1]
            self.last_byte_at = None

    def feed(self, chunk: bytes, monotonic_seconds: float) -> list[Frame]:
        self.expire(monotonic_seconds)
        output = self._drain()
        for byte in chunk:
            self.last_byte_at = monotonic_seconds
            self.buffer.append(byte)
            if len(self.buffer) > self.max_buffer:
                self.buffer.pop(0)
                self.discarded += 1
            output.extend(self._drain())
        return output

    def _drain(self) -> list[Frame]:
        output = []
        while self.buffer:
            marker = self.buffer.find(START)
            if marker < 0:
                keep = 1 if self.buffer[-1] == START[0] else 0
                self.discarded += len(self.buffer) - keep
                self.buffer = self.buffer[-keep:] if keep else bytearray()
                break
            if marker:
                self.discarded += marker
                del self.buffer[:marker]
            if len(self.buffer) < 10:
                break
            size = int.from_bytes(self.buffer[8:10], "little")
            if self.buffer[2] != VERSION or self.buffer[7] not in Command._value2member_map_ or size > MAX_PAYLOAD:
                self.discarded += 1
                del self.buffer[0]
                continue
            total = MIN_FRAME + size
            if len(self.buffer) < total:
                break  # never interpret a legal payload as a new frame before timeout
            try:
                frame = decode(bytes(self.buffer[:total]))
            except ProtocolError:
                self.discarded += 1
                del self.buffer[0]
                continue
            output.append(frame)
            del self.buffer[:total]
        return output
