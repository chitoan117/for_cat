"""Machine-readable frozen command semantics and physical/telemetry distinction."""
import argparse
import json
from pathlib import Path

COMMANDS = [
    (1, "PING", "JETSON_TO_ESP", 0, 0, "ACK payload=01", "none", "none", "repeat ACK; no state mutation"),
    (2, "GET_STATUS", "JETSON_TO_ESP", 0, 0, "SYSTEM_STATUS payload=01 (safe firmware alive, NOT sensor health)", "none", "none", "repeat same status"),
    (3, "FEED_REQUEST", "JETSON_TO_ESP", 0, 0, "ACK payload=03 only receipt; poll FEED_STATUS => REJECTED=02 in HW_SAFE", "volatile ID/result cache, max16", "none in HW_SAFE", "same ID ACK, never re-execute; cache full NACK04; ID0 NACK06"),
    (4, "FEED_STATUS", "JETSON_TO_ESP", 0, 0, "FEED_STATUS byte 0 pending/1 success/2 rejected/3 error; unknown ID NACK05", "none", "none", "read cached result; reboot forgets IDs"),
    (5, "SYSTEM_STATUS", "ESP_TO_JETSON", 1, 1, "byte01 only, correlated to GET_STATUS", "link ONLINE after semantic validation", "none", "foreign IDs discarded; no boot nonce in v1"),
    (6, "ACK", "ESP_TO_JETSON", 1, 1, "original request command01 or03, correlated ID", "receipt only, not dispensing SUCCESS", "none", "unexpected ACK rejected; foreign ID discarded"),
    (7, "NACK", "ESP_TO_JETSON", 1, 1, "reason01 bad frame/02 version/03 unsupported/04 busy/05 unknown ID/06 payload", "link DEGRADED for protocol reasons; business NACK04/05 link ONLINE", "none", "known reason accepted; wrong shape/code rejected")
]


def matrix():
    return {"schema_version": 1, "protocol": "FROZEN_UART_V1", "start_hex": "a55a", "crc": "CRC16_CCITT_FALSE_LE",
            "wire_max_payload": 256, "minimum_frame_bytes": 12, "maximum_frame_bytes": 268,
            "request_partial_timeout_ms": 250, "max_bytes_per_firmware_loop": 64,
            "safe_mode": "ACTUATOR_OUTPUTS_ENABLED=0; no pump/servo command exists",
            "commands": [{"command_id": ident, "name": name, "direction": direction,
                          "payload_min_bytes": low, "payload_max_bytes": high,
                          "payload_schema": "empty" if direction == "JETSON_TO_ESP" else response,
                          "valid_response": response, "invalid_response": "ProtocolError => DEGRADED; timeout/disconnect => OFFLINE",
                          "ack_semantics": "ACK is receipt only; no actuator authority",
                          "timeout": "Jetson configured deadline; reconnect/backoff after failure; partial firmware input needs >250ms silence",
                          "duplicate_replay": duplicate, "state_mutation": state, "persistence_mutation": persistence,
                          "safety_effect": "NONE: outputs hard disabled"}
                         for ident, name, direction, low, high, response, state, persistence, duplicate in COMMANDS],
            "negative_rules": {"bad_crc": "NACK01; no dispatch", "bad_version": "NACK02; no dispatch",
                               "bad_start": "discard until START", "oversized_header": "NACK01 at header; reset candidate",
                               "legal_nonempty_request": "framing accepts <=256 but current request semantics NACK06",
                               "truncation_drop_duplicate": "NACK or silence; expire candidate then accept next valid frame",
                               "incoming_response_commands": "empty payload NACK03; nonempty payload NACK06"},
            "not_present": ["binary sensor telemetry", "binary EVENT command", "grams payload", "boot nonce/authentication", "pump command", "servo command"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(matrix(), stream, indent=2)


if __name__ == "__main__":
    main()
