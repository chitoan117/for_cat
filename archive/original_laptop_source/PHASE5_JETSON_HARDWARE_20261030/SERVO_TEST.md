# Servo — BLOCKED / NOT_RUN / LOCKED

Date: 2026-10-30. Evidence reviewed: existing `ACTUATOR_PROCEDURES.md`, pin/profile map, Phase4 safety source/tests. No current PWM, movement, Serial session or actuator request executed.

## Proposed isolated bench, requires explicit approval

- Purpose: verify a **small unloaded** bounded move and real stop/return behavior; not food dispensing or proof of gate closure.
- Intended GPIO6, separate **diag_servo_bench** image, external5V supply/common GND. Actual wiring, exact image identity/default DISARMED/PWM-off and rated supply/current headroom remain NEEDS_PHYSICAL_VALIDATION.
- Pump and buzzer load-power isolated; remove food/load or horn only where safe, mechanical clearance, hands clear, accessible external power cutoff.
- Exact safe min/max/close/open pulse values are **not yet confirmed**. No PWM/góc/hành trình is guessed. No runnable configure/ARM sequence is approved until USER supplies/reviews those values and supervision.

## Exact preparation command — PLAN ONLY

After verifying these existing remote paths, USER can inspect this plan without opening Serial:

```bash
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
T=/home/toan/for_cat/hardware_diag_candidate_20261029/tools
PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00
"$PY" "$T/serial_evidence.py" --port "$PORT" --service-scope user --profile servo --output /home/toan/servo_OWNER_NEW --seconds 120 --interactive --actuator-supervised
```

No `--execute` here. The actual tool's execute branch stops Bridge, opens one Serial and can send human-typed commands; that is a separate maintenance approval with production interruption, not permitted now. Path existence/runtime is not verified this session.

## Proposed human sequence after all gates and separate authorization

1. Confirm exact bench firmware/default OFF/status and approved configuration in a human TTY. No AI/Web/button/scheduled activation.
2. USER types only reviewed configure values, then separately approves `SEND servo arm YES`. **ARM may move immediately toward candidate CLOSE**, not merely set a harmless flag.
3. One bounded `SEND servo open` after approval; source contract is one move/arm,250ms move hold,350ms close hold/PWMoff,2s arm expiry/3s deadline/max3arms per boot. These are firmware bounds, not physical timing certification. No automatic repeat/reboot to evade budget.
4. Log status before/after, exact pulses, source/image SHA, source clock, supply/current/reset observations and video. Verify real motion/return/OFF; ACK/PWM-off does not prove physical closure or zero motor current.

**Stop/recovery:** `STOP` / `SEND servo stop` is the documented immediate PWM-off fault latch. If jam/unexpected motion/brownout or console loss, USER cuts external servo power safely; keep FAULT, no auto-rearm/retry. Close tools and restore only the originally active Bridge under the approved window; check fresh PID/sole owner and AI/API unchanged. Do not restart services from this session.

Expected evidence is a reviewed small-move result and fail-safe behavior. Current outcome stays **BLOCKED**, physical movement **NOT_RUN**. Closed-loop aim35g/final30–40g requires its own approval after servo/HX/recovery gates pass.
