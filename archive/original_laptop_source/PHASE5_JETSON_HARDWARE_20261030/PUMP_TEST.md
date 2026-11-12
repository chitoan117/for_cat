# Pump — BLOCKED / NOT_RUN / LOCKED

Date: 2026-10-30. Evidence reviewed: kit `ACTUATOR_PROCEDURES.md`, maintenance matrix and tooling command gates. No pump output or wet test performed.

## Exact blockers

- Intended GPIO7/F5305S/external5V is a documented map, not current wiring verification.
- Shipped **diag_pump_bench is INERT_UNKNOWN_POLARITY**: PHYSICAL_ENABLE0, OFF_LEVEL-1, no GPIO7 output. No active-pump image is qualified from this session.
- Actual driver input voltage/polarity, measured OFF level0/1, boot/reset/high-Z bias, current/protection/flyback arrangement and supply ratings are missing. High-Z does not prove motor OFF.
- Primed water/pipe/outlet conditions, physical cutoff and direct USER supervision/approval remain missing. Servo must be OFF and load-isolated; no scheduling/AI control.

## Preparation — PLAN ONLY

After path verification, existing CLI supports this inert status-capture proposal:

```bash
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
T=/home/toan/for_cat/hardware_diag_candidate_20261029/tools
PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00
"$PY" "$T/serial_evidence.py" --port "$PORT" --service-scope user --profile pump_inert --output /home/toan/pump_inert_OWNER_NEW --seconds 30
```

No `--execute`. Real capture would interrupt Bridge/open Serial and requires separate approval. Inert firmware must reject ARM/ON; inert status is not a motor-OFF electrical measurement.

## Proposed later wet pulse, not authorized

1. USER measures logic with motor isolated and safe dummy load; records OFF level and boot/reset bias plus voltage/current/protection evidence. Do not choose polarity from module name.
2. Copy existing `OWNER_OBSERVATIONS_TEMPLATE.json` to a NEW filled observation file. Only after physical review, prepare a **separate conditional active image** matching measured polarity; do not alter locked baseline images. Flash remains independently NO-GO until full gates and explicit flash approval.
3. After qualified image/correct OFF status, verify real motor OFF at cold boot/reset/USB transitions; maintain emergency power cut. Prime water path, safe outlet/container, no dry-running beyond rated limits, no water near wiring.
4. Under specific authorization, use human TTY `pump_active` profile with matching `--pump-observation` file and `--interactive --actuator-supervised`. Actual tool refuses ARM/ON until observed OFF level matches the file; no automatic activation. Pulse duration must be selected from actual pump rating/review, within firmware20–500ms/max3pulses per boot/cooldown≥1s/arm expiry2s. No duration is approved in this report.
5. Observe start/flow/current and actual automatic OFF; measure water volume only with a real instrument. Save status/raw timestamps, pulse duration, image SHA, driver/supply evidence and video.

**Stop/recovery:** documented `STOP` / `SEND pump off` / `SEND pump disarm`; if not OFF or console fails, USER cuts external pump power. Keep failure evidence; no auto-retry or switch polarity in software. After an approved session, close Serial, hand back only original Bridge and verify sole ownership/AI/API state. GPIO OFF/ACK alone is not zero-flow/current proof.

Current result: **BLOCKED**, wet pulse **NOT_RUN**. No water-level automation/WATER_ROI or drinking/flow qualification inferred.
