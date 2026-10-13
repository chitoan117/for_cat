"""Canonical v1 CSV is also read by the native C++ firmware-encoder harness."""

import csv
from pathlib import Path

import pytest

from app.serial_link.protocol import Command, Frame, decode, encode

VECTORS = Path(__file__).resolve().parents[2] / "docs" / "UART_V1_GOLDEN_VECTORS.csv"
with VECTORS.open(encoding="utf-8", newline="") as stream:
    ROWS = list(csv.DictReader(stream))


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["name"])
def test_python_codec_matches_shared_uart_v1_vector(row):
    command = Command(int(row["command"]))
    assert command.name == row["name"]
    frame = Frame(int(row["request_id"], 16), command, bytes.fromhex(row["payload_hex"]))
    encoded = encode(frame)
    assert encoded.hex() == row["frame_hex"]
    assert encoded[-2:].hex() == row["crc_le_hex"]
    assert decode(encoded) == frame


def test_shared_vectors_cover_every_v1_command_exactly_once():
    assert {row["name"] for row in ROWS} == {command.name for command in Command}
    assert len(ROWS) == len(Command) == 7
