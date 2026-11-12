import random

import pytest

from app.serial_link.protocol import Command, Frame, FrameStreamDecoder, ProtocolError, decode, encode


def test_stream_recovers_after_random_bytes_corrupt_crc_and_timeout():
    rng = random.Random(0xC47)
    parser = FrameStreamDecoder()
    for i in range(500):
        noise = rng.randbytes(rng.randrange(0, 100))
        parser.feed(noise, i * 1.0)
        parser.expire(i + 0.9)
        assert len(parser.buffer) <= 512
        valid = Frame(i, Command.PING)
        assert valid in parser.feed(encode(valid), i + 0.91)
    broken = bytearray(encode(Frame(600, Command.GET_STATUS)))
    broken[-1] ^= 1
    assert parser.feed(bytes(broken) + encode(Frame(601, Command.GET_STATUS)), 501) == [Frame(601, Command.GET_STATUS)]


def test_stream_recovers_from_bogus_in_range_length_after_candidate_timeout():
    parser = FrameStreamDecoder()
    fake = b"\xA5\x5A\x01\x01\x00\x00\x00\x01\x00\x01"  # claims 256 payload bytes
    valid = Frame(900, Command.GET_STATUS)
    assert parser.feed(fake + encode(valid), 0) == []
    assert parser.feed(b"", 0.3) == [valid]
    assert len(parser.buffer) == 0 and parser.discarded >= len(fake)


def test_decoder_bounded_fuzz_malformed_inputs():
    rng = random.Random(12345)
    for _ in range(1000):
        data = rng.randbytes(rng.randrange(0, 512))
        try:
            decode(data)
        except ProtocolError:
            pass
        parser = FrameStreamDecoder()
        parser.feed(data, 0)
        parser.expire(1)
        assert len(parser.buffer) <= 512
