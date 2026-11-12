# HX711 independent VERIFY5 — BLOCKED, 2026-10-27

- Session: `hxcal_e721ec976ad44342b4522a051ba6c9f1`; FIT0/5/10/20/30/35 previously completed on current mounting, candidate remains CANDIDATE_PENDING_VALIDATION (not active).
- Operator explicitly confirmed a single nominal 5 g weight in the tray. Existing `observe_ultrasonic.py --hx-capture 5 --hx-phase verify --operator-confirmed` returned RUNTIME_PASS for **raw capture only**: point `fb0d234c424c4eea9f7dba6775252ba0`, 31 samples over 30 s, no rejected samples, stable candidate window.
- Candidate calculated **7.371194838734029 g** for declared **5 g**: error **+2.371194838734029 g (+47.4239%)**, tolerance **±0.1 g**, `independent_point_passed=false`. Do not interpret raw-capture RUNTIME_PASS as gram calibration PASS.
- Existing raw evidence reported at `/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/fast_track_ultrasonic/hxcal_e721ec976ad44342b4522a051ba6c9f1/verify_5.0g_1793090005861820846.raw.json`, SHA256 `e72c624971d45904dd6e374e9fb35eb62a3625d30ad9ce72c3a5d8e7986ac309` (reported by remote tool; reread/verify when network recovers).
- Earlier independent VERIFY0 candidate was +0.013494902879522992 g, within ±0.1 g; FIT5 model prediction was 5.004801336965092 g. These are distinct captures; the new VERIFY5 cannot be silently replaced by FIT5.
- Jetson was reachable at 15:32 +07 by authenticated link-local IPv6 after laptop IPv4/mDNS network changed. `timedatectl` indicated clock not synchronized; worker WAITING_TIME_VALID, AI `DISCONNECTED`. Serial raw reported live and all safety flags false/output0. Jetson reboot/power/clock/load placement causality is **UNKNOWN**, not established.
- The attempted **read-only** audit `audit_verify5_failure.py` did not run: SSH to both IPv4 addresses and later IPv6 timed out. No model activation, retare, refit, verify10, NVS command or actuator command was issued after the failed point.
- Next physical action: operator removes *only* 5 g reference from the normally mounted tray, leaving tray/gauging unchanged; wait for explicit empty-tray confirmation. Then, when SSH is available, inspect boot IDs/current clocks/receipt, perform bounded independent unloaded diagnostic to distinguish zero shift from wrong-load/placement or sensitivity change. Preserve candidate and failed VERIFY5 point; no PHYSICAL_PASS before full independent verify/persistence gates.

## Follow-up after explicit empty-tray confirmation

- Operator has now confirmed the tray is empty again (`khay trống verify`). **No post-failure VERIFY0g capture has run.** The previous VERIFY0 point remains the earlier point before the failed VERIFY5.
- Attempts to reach Jetson over authenticated SSH at `192.168.123.8`, `192.168.137.59` and `fe80::2f03:e65b:a064:b574%13` all timed out. Windows `Ethernet 5` has link `Up`/1 Gbps and IPv4 `192.168.137.1`, but neighbor resolution for `192.168.137.59` is incomplete and the known IPv6 neighbor is unreachable; `server-jetson.local` did not resolve. The cause is not yet known.
- Keep tray unloaded and servo/pump isolated. Obtain the Jetson's currently assigned IP from its *local console* before trying another calibration capture. Do not create a synthetic point, infer zero response or claim live safety flags while the network is unavailable.

## Post-failure empty-tray verification (network restored via SSH IPv6)

- User confirmed empty tray after removing5g. Existing tool recorded new independent VERIFY0 point `3340e334213d4d59950296108b43525f` (30 real samples/29s, 0 outliers): mean raw `-669439.1` counts. Raw file SHA256 `07b25fc342c381db0f441dfba192c525c55e2b3c9cceafc3a38f0d0d58d80048` at session evidence path `verify_0.0g_1793090441964959534.raw.json`.
- Candidate estimates **+2.258386021611615g at unloaded0g**, strict tolerance ±0.1g: independent point FAIL despite `stable=true` (spread0.14025g, sigma0.03051g, drift0.01465g).
- Failed VERIFY5 was +7.371194838734029g; difference between this5g point and new unloaded point ~5.11281g. This does **not** rescue the original calibration because zero alone is >2g off and the difference is also outside nominal5±0.1g. Do not subtract the new zero to report an activated model.
- Original VERIFY0 and FIT points used host boot ID `4df3d847-d13e-48a5-85b3-2e8eb826c1e2`; failed VERIFY5 used `23964cf7-c101-43a4-8995-4b12ea805416`. Reboot temporally coincides with zero shift but its cause (mounting, cable/load contact, reference placement, ADC/power, etc.) is **unproven**.
- Safety remained false/output0, other ultrasonic acquisition disabled, actual=null, no re-tare/refit/activation/NVS/servo/pump command. Calibration state remains `CANDIDATE_PENDING_VALIDATION`; this verify round has a failed point and should not be marked PHYSICAL_PASS.
- **Next single user action:** inspect with tray still empty for contact/pressure from wires, brackets, objects or misalignment on the load-cell platform; report what is seen without adding mass or changing the mount yet.

## Owner follow-up: unexpected object found

- Owner reports **one additional object estimated at about 2.371 g** on/touching the load-cell tray. The mass is owner-provided approximate information, **not a validated reading** from the currently inactive calibration model.
- This is a plausible source of the post-reboot candidate offsets (+2.371g on declared VERIFY5 and +2.258g on declared unloaded VERIFY0), but cannot be confirmed until the object is removed and an independent unloaded capture returns within tolerance.
- Preserve both failed points and the six fit points. No automatic subtraction, retare, refit, reset-phase, model activation, or revised PASS. Next action: remove only that unexpected object, leave the tray/mount/wires unchanged, then explicitly confirm removal before another diagnostic0g capture.
