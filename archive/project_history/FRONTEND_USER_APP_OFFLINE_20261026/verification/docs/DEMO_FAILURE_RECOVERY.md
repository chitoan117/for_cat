# University demo failure/recovery plan

Current demo is **SOFTWARE / SYNTHETIC / MOCK**, not physical feeding/recognition. A future physical demonstration may occur only after actual gates. Stop on unexpected movement, heat, power sag, leak or sensor fault; preserve logs. Never remove output guards, guess pins/labels, infer SUCCESS from ACK or switch silently to mocks to hide a failed experiment.

| Failure | Safe response | Honest fallback | Actual evidence to retain |
| --- | --- | --- | --- |
| Camera unavailable | Stop/close observation run; report OFFLINE, no fabricated continuation | Existing `tools.demo_replay` or supplied-file replay clearly labelled SYNTHETIC/OFFLINE; show capture dry-run/architecture | Actual device/backend/read errors and stop reason |
| AI unavailable | Keep UNKNOWN/NOT_CONFIGURED, shadow/no automatic intent; no invented confidence | Explain task/registry/evaluation contracts; show synthetic replay only under an explicit label | Artifact/runtime/config/hash/load error or simply NOT TRAINED |
| ESP32-S3 disconnects | Show OFFLINE/PENDING/unknown outcome; no blind resend or actuator enable | Local mock API/twin in a separate explicitly selected software demo, not proof of reconnect | IDs, CRC/timeout, node/routing, unplug/replug trace |
| Sensor fails | Weight/RTC/water prerequisite invalid; no feeding/pump; unknown readings | Existing native/twin fault case labelled HOST/SIMULATION; blank calibration table | Actual health/raw/fault/voltage/firmware/timestamp |
| Servo unavailable | Keep disabled; no direct GPIO or forced motion | Explain desired-state policy and simulated request rejection; do not claim material dispensed | Missing hardware/driver/gate/mechanics or real safe fault log |
| Network/frontend unavailable | Keep API local; no emergency public binding/port forwarding | Local loopback health/history contract or prepared design diagrams; no fake Web/App screenshot | Actual endpoint/client/network error, no credentials |

Software fallback from `jetson/`, using the project venv:

```text
python -m tools.demo_replay
python -m tools.run_simulator NORMAL
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Do not change live configuration mid-request. Stop the affected process, explain the failure, then deliberately run a distinct mock/offline process if needed. Keep original failure outcome in the report. If even software dependencies are unavailable, present static requirements/sequence diagrams and saved **actual host** check logs, with date/version; no PASS claim for today's unrun test. A failed demo is evidence of a limitation, not permission to fabricate a successful result.
