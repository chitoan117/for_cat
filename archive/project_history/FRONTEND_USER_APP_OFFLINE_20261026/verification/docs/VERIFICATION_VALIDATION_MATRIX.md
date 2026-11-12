# Verification versus validation

| Function | UNIT TEST | HOST INTEGRATION | SIMULATION | COMPILE | PHYSICAL BENCH | REAL DATA | FULL SYSTEM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| REST/history/feed lifecycle | PASS | Mock API/SQLite PASS | Synthetic PASS | Python imports PASS | Pending Jetson/link | Pending | Pending |
| UART/reconnect | PASS | Fake ports PASS | Twin PASS | Safe firmware PASS | Pending USB | N/A | Pending |
| Feed/water safety | Native PASS | Driver→policy fake I/O PASS | Twin PASS | All safe profiles PASS | Pending real rigs | Pending sensor evidence | Pending |
| Sensor/UI drivers | Native math/state PASS | Fake GPIO/I²C PASS | Synthetic inputs | Diagnostic profiles PASS | Pending all components | No measured calibration | Pending |
| Capture/manifest | PASS | Spawned generated video PASS | Synthetic video | Python imports PASS | Webcam pending | Real sessions absent | Pending |
| Extraction/leakage/releases | PASS | Local fixture pipeline PASS | Synthetic corpus | Python imports PASS | N/A | Corpus/review absent | Pending data lifecycle |
| Candidate/experiment/model registry | Schema/hash PASS | Inactive metadata PASS | Placeholder bytes ONLY | Python imports PASS | Actual runtime pending | Training absent | Pending |
| Frame/event evaluation/sweep | Arithmetic PASS | Supplied fixtures PASS | Synthetic predictions | Python imports PASS | Jetson runtime pending | No real predictions | Pending |
| Temporal/fusion/tracking boundary | PASS | Injected replay PASS | Synthetic events | Python imports PASS | Camera/tracker pending | Real annotations absent | Pending |
| Preference/activity reports | Filters/unknowns PASS | Supplied records PASS | Synthetic only | Python imports PASS | Weight attribution pending | Clean trials absent | Pending |
| Existing Web/App | Contract documented | Not integrated here | API fixtures only | Frontend unchanged | Pending network | Pending user scenarios | Pending |

PASS is limited to the named layer. A compiler does not validate wiring, a codec does not validate sensor calibration, and fixture metrics do not validate AI. Final counts/toolchain are in `PRE_HARDWARE_FINAL_BASELINE.md`; milestone is M2.
