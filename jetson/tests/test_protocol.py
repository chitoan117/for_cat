import pytest

from app.serial_link.mock_transport import MockEsp32Transport
from app.serial_link.protocol import Command, FeedCode, Frame, ProtocolError, crc16, decode, encode


def test_crc_standard_vector_and_roundtrip():
    assert crc16(b"123456789") == 0x29B1
    # Fixed v1 wire vector (request ID little-endian; CRC bytes little-endian).
    assert encode(Frame(0x12345678, Command.FEED_REQUEST)).hex() == "a55a017856341203000023b6"
    for command in Command:
        frame = Frame(0x12345678, command, b"\x00\xA5\xFF")
        assert decode(encode(frame)) == frame


def test_invalid_crc_and_malformed_frames():
    valid = encode(Frame(12, Command.PING))
    corrupted = bytearray(valid)
    corrupted[-1] ^= 0x01
    for invalid in (bytes(corrupted), valid[:-1], b"garbage" + valid, valid + b"extra",
                    valid[:8] + b"\xFF\x7F" + valid[10:],
                    valid[:8] + b"\x01\x00" + valid[10:],
                    valid[:2] + b"\x02" + valid[3:]):
        with pytest.raises(ProtocolError):
            decode(invalid)
    with pytest.raises(ProtocolError):
        encode(Frame(1, Command.PING, bytes(257)))


def test_unknown_command_with_valid_crc_is_rejected():
    # Encoder can build a raw unknown code for this malformed-input test.
    unknown = encode(Frame(42, 0xFE))
    with pytest.raises(ProtocolError, match="unknown command"):
        decode(unknown)


def test_mock_transport_separates_ack_and_final_status():
    mock = MockEsp32Transport()
    ack = decode(mock.exchange(encode(Frame(5, Command.FEED_REQUEST))))
    assert ack == Frame(5, Command.ACK, bytes([Command.FEED_REQUEST]))
    assert decode(mock.exchange(encode(Frame(5, Command.FEED_STATUS)))).payload == bytes([FeedCode.PENDING])
    mock.complete_feed(5, FeedCode.REJECTED)
    result = decode(mock.exchange(encode(Frame(5, Command.FEED_STATUS))))
    assert result.command == Command.FEED_STATUS
    assert result.payload == bytes([FeedCode.REJECTED])
