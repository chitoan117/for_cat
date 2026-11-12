# UART / USB serial protocol v1

Canonical byte-for-byte vectors shared by Python and the C++ firmware encoder: `UART_V1_GOLDEN_VECTORS.csv`. The Python test and executed native C++ harness load the **same CSV**; do not maintain separate hand-written expected frames. The common `0x12345678` request ID is a test correlation value; live GET_STATUS uses ID 0, and feed IDs are allocated separately.

Baud rate 115200, 8N1. Frames: `A5 5A | VERSION:u8=01 | REQUEST_ID:u32 LE | COMMAND:u8 | PAYLOAD_LENGTH:u16 LE | PAYLOAD:0..256 bytes | CRC16:u16 LE`. Minimum 12 bytes. CRC-16/CCITT-FALSE (`poly=0x1021`, `init=0xFFFF`, no reflection, xorout=0) covers VERSION through end of PAYLOAD, excluding START and CRC. The Python codec requires an exact complete frame; ESP32 parses incrementally, resets incomplete frames after 250 ms, rejects oversized/invalid CRC frames and never drives actuators from malformed data.

| Code | Command | Request/response payload |
| --- | --- | --- |
| 1 | PING | request empty; reply ACK payload `01` |
| 2 | GET_STATUS | request empty; reply SYSTEM_STATUS payload `01` (protocol responsive only) |
| 3 | FEED_REQUEST | request empty; reply ACK payload `03` if received, NACK otherwise |
| 4 | FEED_STATUS | request empty using original feed request ID; reply FEED_STATUS one-byte result |
| 5 | SYSTEM_STATUS | response, `01` = protocol responsive; not actuator-ready evidence |
| 6 | ACK | response payload is echoed request command byte |
| 7 | NACK | response payload one-byte reason |

FEED_STATUS codes: `00=PENDING`, `01=SUCCESS`, `02=REJECTED`, `03=ERROR`. NACK reasons: `01=bad frame`, `02=version`, `03=unsupported`, `04=busy`, `05=unknown ID`, `06=bad payload`. Requests and replies share REQUEST_ID; Jetson rejects mismatched replies. ID 0 is used for health/status queries; feed IDs begin at 1. ACK is only a valid received command; it **never** means dispensing succeeded. RC2 HW_SAFE ACKs then reports REJECTED (local reason SAFE_BUILD_ACTUATORS_DISABLED); SIM uses explicitly synthetic 10 g local target/sensors and returns PENDING then final status. The bounded 16-ID dispatch ledger fails closed on capacity, does not evict/re-execute IDs, and is volatile across reboot. No grams/reason/water fields are added to v1. Before enabling real feeding, implement MCU durable command replay and validate physical safety/recovery.

Python provides mock and optional pyserial transports, a bounded incremental `FrameStreamDecoder` for offline stream/fuzz validation, and a link manager for correlation/stats. No real link is validated. `serial_port.h` selects UART0 for bridge profiles or native S3 HW CDC for the inspected compile surrogate; no application UART GPIO remapping. Water telemetry is **not** present in protocol v1; it would require a documented compatible extension/version, not a silent change to SYSTEM_STATUS. Both profiles prohibit physical outputs.

Quality correction: the Python stream parser does not speculate that a CRC-valid START sequence inside an incomplete payload is a separate frame. It waits for the outer length/CRC, or candidate timeout before resynchronizing. Recovery from an in-range corrupted length may therefore require timeout; this ambiguity cannot be resolved early from bytes alone. **Frame format, encoder/CRC and seven golden vectors remain unchanged.** Host feed IDs never wrap/reuse; exhaustion fails closed. V1 has no boot/session nonce, so a physical peer reset cannot establish a new final outcome from a stale same-ID reply alone; physical feeds remain blocked and unknown outcomes are not blindly resent.
