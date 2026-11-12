# Web / AI / SQLite integration — live GET evidence

Date: 2026-10-30. **HTTP observations VERIFIED_PASS; sensor-to-Web integration FAIL/BLOCKED; target GPU/browser qualification NOT_RUN.**

## Actual requests and evidence

`http_readonly_audit.py --base http://192.168.123.8:8000 --execute GET_EXISTING_STATUS --out ...\http_lan_20261030` executed via `run_evidence.py`, exit0, `02:29:12.431515Z–02:29:17.571134Z`. 14 GET responses, two cached-state observations separated by4s, bounded1MiB/body, no redirects/proxy/identity spoofing. Bodies/status/timestamps/hashes in `http_lan_20261030/result.json`; derived hash-verified analysis in `HTTP_ANALYSIS.json`.

| Endpoint | Actual result |
|---|---|
| `/api/v1/health` | 200, status ok |
| `/api/v1/readiness` | 200; API/database READY; ready=false; observation_service STOPPED; API pipeline camera NOT_CONFIGURED, ai MOCK |
| `/api/status` | 200; provider label REAL, invalid/missing sensor data; external AI classification NONE/health ONLINE/source EXISTING_CPP_TENSORRT_STDOUT |
| `/api/v1/esp32/status` | 200; fresh Bridge heartbeat, BAD_TELEMETRY, telemetry null, valid_reports0 |
| `/api/hx711/status` | 200; grams/raw/calibration_id null, raw_available=false, NOT_CALIBRATED; actual_dispensed_grams null |
| `/api/v1/feeding-history`, `/drinking-history` | 200; captured responses [] |
| `/api/v1/sessions/feeding`, `/sessions/drinking` | 200; captured responses [] |
| `/api/v1/hardware-diagnostics/status` | **404**; extension not available on this origin |
| `/kiosk` | 200 HTML, title Bữa ăn của MÈO, base `/flutter/`, loads flutter_bootstrap.js |

Additional single GET `/api/v1/esp32/events?limit=20` at `02:32:53.714077Z`, exit0/HTTP200, saved `BRIDGE_EVENTS.json` and `evidence/bridge_events/`: repeated **unsupported firmware mode** including latest server timestamp09:32:42Z.

## Interpretation and discrepancies

- Fresh Bridge heartbeat is not fresh sensor data: updated_monotonic199715→204119ms but last_rx_monotonic0, no accepted telemetry. `stale=false` here does not make absent data usable. Units distance_cm/grams remain null, not0.
- REAL is provider/provenance labeling; it is not a sensor/physical qualification flag. No SIMULATED fixture was uploaded or displayed as LIVE.
- API pipeline MOCK and external AI ONLINE/NONE are different reported components. No current PID, actual TensorRT engine/GPU/frame epoch/camera ownership verified; no new camera/watch/MJPEG request. Generic CAT/NONE is not OWNER_CAT identity.
- `owner_verification.hx711` still says gram_calibration DEFERRED, while the later scoped file `HX711_ACCEPTANCE.json` accepts static35g34.981g. The API metadata is older/incomplete for this acceptance. Retain the newer accepted static result; do not retare/retest or claim current calibration valid from the historical badge.
- Current firmware grams/calibration context unknown; API NOT_CALIBRATED does not erase historical static accuracy acceptance.
- Kiosk HTML availability is verified, not Flutter execution/render/null-handling/38g display on this browser. No browser automation/device control or frontend deployment occurred.
- History [] proves only the captured query responses, not absence of all historical physical activity. No consumption/preference/emotion/drinking inference produced.
- Server clock labeling is about+7h relative to client receipts; preserve both and inspect read-only host time before trusting wall-clock chronology.

The legacy `/api/v1/status` path was intentionally not requested: reviewed older implementations can poll the binary transport or call provider health. Read-only cached `/api/status`, `/esp32/status` and `/readiness` supplied the needed state without that ambiguity. No camera endpoint, feed polling or POST was used.

## Next integration work

Obtain host preflight and ARM64 file-only result first. Then review current firmware identity, security/electrical/maintenance gates and a separate integration rollout. Quad-sensor firmware,8192 framer, qualified PIR/HX forwarding and paired API/Flutter profile must be compatible; no production change is authorized merely by an ARM64 compile PASS. Keep actual grams, UNKNOWN/null/error and ACK-vs-final semantics intact.
