# Faster opening and small closing extension — 2026-11-06

CURRENT ACCEPTED PROFILE: see balanced/. Owner confirmed1350us/900ms OPEN and1600us/1450ms CLOSE return to the closed reference after3 physical cycles. Neutral1500us. This supersedes the initial750/1050 trial and the900/1050 trial described below. Final app SHA256a23efe87f2d502f0f4aad27a0aab5cf2b140b04a06ba2f5e8f4bdf878da2aa47. Deployment must be checked against balanced/flash_result.json and balanced/resume_verified.json.

Owner reports food jam and drift toward OPEN, requests faster/stronger opening command and a small additional closing stroke. Owner confirmed the jam was cleared and the mechanism aligned CLOSED with separate servo power disconnected before trial readiness was acknowledged.

Trial profile: GPIO6 OPEN1350us/750ms (previous1400us/1100ms), CLOSE1600us/1050ms (previous1600us/1000ms), neutral1500us. The opening duration is shortened alongside the increased command offset to avoid simply increasing opening travel. Speed/travel are not linear in pulse offset under load; these values require owner-observed mechanical trial. PWM does not raise the servo's rated torque or provide position feedback. Closing extends the existing stroke by50ms; no separate fine-adjust or compensation stroke is added.

Only servo constants/default durations, help text and read-only pulse reporting change. Source comparisons confirm unchanged HX driver/filter/adapter, distance initialization and feed state-machine logic. Native extracted-branch tests PASS for timing boundaries, alternating cycles, duplicate rejection, STOP inspection lock, retry after completed close, E1≤30cm three-reading gate, 34.99g wait /35g close, and GPIO19 input policy.

Guarded app-only deployment uses actual previous app70e5d5aacf62810e2ae721f2b079854427f12c16103d3ab704b011980a6293d8, flash/partition/OTA backup and preserved NVS. Expected new app1d5b96fd8e87d219afef7e44c17e0dc2db5a3bac46114a158ddb5b4d480c0c50. Flash and trial readiness must be confirmed by flash_result.json and trial_ready.json; this README alone is not evidence of successful programming.

After programming, the CAT/DOG demo is held exited for a supervised first trial. Owner may use one press of the physical feed button, then release and wait for the bounded full cycle. That manual button path deliberately starts a manual feed even while the AI demo is exited. Final travel/drift acceptance is pending a physical observation. No automatic dose accuracy claim is made and no new tare is performed.

The previously deployed DOG confidence/temporal filter on Jetson remains unchanged. Frontend, water/pump behavior, sensor pin map and load-cell calibration remain unchanged.

Owner physical feedback after750ms trial: opening insufficient; closing returns correctly. Only OPEN duration was changed to900ms in RAM via existing open_ms command. Actual UART confirmed1350us/900ms OPEN,1600us/1050ms CLOSE,moving0. Flash defaults remain750/1050 until physical900ms acceptance. NVS/scale calibration unchanged by RAM timing command.
