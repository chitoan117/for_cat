# Sensor status wire extension — design only

**Frozen UART v1 remains unchanged** in `esp32/include/uart_v1.h`, `jetson/app/serial_link/protocol.py` and the seven golden vectors. Existing PING/GET_STATUS and feed commands keep their exact frame/payload semantics. No sensor telemetry command, new command ID or incompatible decoder is implemented in this preparation.

The new local `m4::SensorSnapshot` cannot be represented by the existing one-byte GET_STATUS without losing optional data, units, health, freshness and water-policy meaning. Diagnostic ASCII JSON is a separate component-test image, never injected into the normal binary stream or treated as Jetson production telemetry.

## Proposed future contract

After physical acquisition and sampling requirements are known, agree on a **versioned capability negotiation and sensor-status response** implemented together on Jetson and MCU. Command IDs and binary packing remain undecided. Legacy peers must retain legacy behavior; unsupported telemetry returns an explicit unsupported outcome, not reinterpreted v1 bytes.

Required fields:

- schema version, MCU boot/session identifier, monotonic snapshot time;
- per-component health/reason plus validity bits and sample age; a missing value must remain absent, not zero;
- HX711 raw counts and optional calibrated grams with explicit units/scale;
- optional valid RTC UTC epoch; RTC invalidity and monotonic time are distinct;
- food and water distance/level independently, including calibration state and range validity;
- actual local water state/reason and separately labelled policy request versus verified physical actuator state;
- calibration-record version and relevant configuration/validation flags;
- servo/pump readiness/output-disabled state, without claiming a measurement from a commanded output;
- explicit stale/out-of-order/reboot handling; invalid sensor snapshots must not trigger feeding or pumping.

Do not expose hypothetical diagnostic pump readiness as production pump health. Do not infer liters/mass/consumption from a percentage alone. Preserve raw diagnostic detail without manufacturing a calibrated measurement.

## Acceptance work before implementation

Choose payload size/rate based on real sampling and link measurements, keep the bounded frame parser, and define unknown-field/version handling. Add separate golden vectors for new commands; keep all seven v1 vectors. Test missing/uncalibrated/fault/stale readings, CRC/length/noise, reconnection/reboot, legacy/new peer compatibility and optional values in the Jetson API/storage path. Only then wire real verified component inputs into normal MCU status/policies and agree any API/frontend changes. No frontend is modified by this design note.
