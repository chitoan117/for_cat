"""Low-rate physical PING/GET_STATUS and optional bad-CRC host probe."""

import argparse
import sys
import time
import json
from math import isfinite

from app.serial_link.protocol import Command, Frame, decode, encode
from app.serial_link.real_transport import RealEsp32SerialTransport


def run_safe_probe(transport, count=3, interval=1.0, clock=time.monotonic, sleep=time.sleep):
    """Safe protocol measurements only; caller/physical evidence determines the M3 gate."""
    if not 1 <= count <= 10 or not isfinite(interval) or interval < 0.25:
        raise ValueError("count must be 1..10; interval finite and >=0.25 seconds")
    records = []
    for index in range(count):
        for command in (Command.PING, Command.GET_STATUS):
            request_id = 100 + index * 2 + int(command == Command.GET_STATUS)
            began = clock()
            record = {"command": command.name, "request_id": request_id, "response": None,
                      "response_id": None, "payload_hex": None, "crc_valid": None,
                      "request_correlated": None, "timeout": False, "result": "FAIL",
                      "includes_first_open_reset_delay": index == 0 and command == Command.PING}
            try:
                response = decode(transport.exchange(encode(Frame(request_id, command))))
                expected = Command.ACK if command == Command.PING else Command.SYSTEM_STATUS
                payload = bytes([Command.PING]) if command == Command.PING else b"\x01"
                record.update(response=response.command.name, response_id=response.request_id,
                              payload_hex=response.payload.hex(), crc_valid=True,
                              request_correlated=response.request_id == request_id)
                if response.request_id == request_id and response.command == expected and response.payload == payload:
                    record["result"] = "PASS"
            except TimeoutError as exc:
                record.update(timeout=True, error=str(exc)[:256])
            except (ConnectionError, ValueError) as exc:
                record["error"] = str(exc)[:256]
                if "CRC" in str(exc):
                    record["crc_valid"] = False
            record["round_trip_ms"] = round(max(0, clock() - began) * 1000, 3)
            records.append(record)
        if index + 1 < count:
            sleep(interval)
    return {"label": "SAFE SERIAL PROBE — not an automatic milestone/hardware declaration",
            "commands_sent": [record["command"] for record in records], "records": records,
            "protocol_probe_passed": all(record["result"] == "PASS" for record in records),
            "timeouts": sum(record["timeout"] for record in records), "feed_requests_sent": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description="Test detected ESP32 USB serial device without feeding")
    parser.add_argument("--device", required=True, help="detected /dev/ttyUSB* or /dev/ttyACM*")
    parser.add_argument("--count", type=int, default=3, help="1..10 pairs of requests")
    parser.add_argument("--interval", type=float, default=1, help="seconds between pairs, >= 0.25")
    parser.add_argument("--malformed", action="store_true", help="send one PING frame with invalid CRC")
    parser.add_argument("--m3", action="store_true", help="physical bring-up measurements; only PING/GET_STATUS")
    parser.add_argument("--json", action="store_true", help="structured probe output for explicitly saved evidence")
    args = parser.parse_args()
    if not 1 <= args.count <= 10 or not isfinite(args.interval) or args.interval < 0.25:
        parser.error("count must be 1..10 and interval >= 0.25 seconds")
    if args.m3 and args.malformed:
        parser.error("M3 mode sends only valid PING/GET_STATUS; do not combine --m3 and --malformed")
    transport = RealEsp32SerialTransport(args.device)
    errors = 0
    try:
        probe = run_safe_probe(transport, args.count, args.interval)
        errors += sum(record["result"] != "PASS" for record in probe["records"])
        if args.json:
            print(json.dumps(probe, indent=2))
        else:
            print(probe["label"])
            for record in probe["records"]:
                print(f"{record['command']} id={record['request_id']} reply={record['response']} "
                      f"reply_id={record['response_id']} payload={record['payload_hex']} "
                      f"CRC={record['crc_valid']} RTT_ms={record['round_trip_ms']} "
                      f"timeout={record['timeout']} result={record['result']} {record.get('error', '')}")
        if args.malformed:
            request = bytearray(encode(Frame(500, Command.PING)))
            request[-1] ^= 1
            try:
                # Deliberately bypass the validated transport for this one host probe.
                import serial
                transport.close()
                with serial.Serial(port=args.device, baudrate=115200, timeout=2, write_timeout=2) as port:
                    time.sleep(2)  # USB serial open may reset the ESP32
                    port.reset_input_buffer()
                    port.write(request)
                    response = decode(port.read(13))  # one-byte NACK reason payload
                print(f"bad-CRC PING response={response.command.name} id={response.request_id} "
                      f"reason={response.payload.hex()}")
                if response.command != Command.NACK or response.payload != b"\x01":
                    errors += 1
            except (ConnectionError, TimeoutError, ValueError) as exc:
                errors += 1
                print(f"bad-CRC PING unavailable: {exc}")
    finally:
        transport.close()
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
