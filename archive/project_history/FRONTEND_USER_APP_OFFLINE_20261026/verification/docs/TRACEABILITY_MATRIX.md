# Requirements traceability

Statuses: HOST VERIFIED means a bounded software scope is exercised; PARTIAL means final operational outcome remains unverified. No hardware-required requirement is marked complete. Test filenames are project-relative; AI/data/report fixtures are synthetic.

| ID | Requirement | Implementation | Host test | Simulation | Hardware/real-data required | Current status |
| --- | --- | --- | --- | --- | --- | --- |
| FR-001 | Identity | `jetson/app/vision/detector.py`, `ai/evaluation.py` | `test_jetson_hardening.py`, `test_productization_ai.py` | Injected labels | Actual cat dataset/runtime | PARTIAL / AI UNTRAINED |
| FR-002 | Eating | `app/behavior/temporal.py`, `fusion.py` | `test_observation_pipeline.py`, `test_rc2_evidence.py` | Synthetic events | Annotated real events | PARTIAL |
| FR-003 | Drinking | temporal/fusion, `analytics/reports.py` | `test_records_preference.py`, `test_product_reports.py` | Synthetic events | Annotated real events | PARTIAL |
| FR-004 | Manual intent/result | `app/api/routes.py`, `storage/repositories.py` | `test_api.py`, `test_rc2_evidence.py` | Simulator transport | Physical link/rig | PARTIAL / physical blocked |
| FR-005 | Dispense | `esp32/include/safety_logic.h` | `native_safety.cpp`, `native_drivers.cpp` | Feed twin | Load cell + closure/jam/rig | PARTIAL |
| FR-006 | Water maintenance | `safety_logic.h`, `m4/snapshot.h` | Native harnesses, `test_simulator.py` | Water twin/shadow | Calibrated level + pump rig | PARTIAL |
| FR-007 | History | `app/storage/` | `test_models_store.py`, `test_db_maintenance.py` | Synthetic history | Deployed power/reset/storage | PARTIAL |
| FR-008 | REST | `app/main.py`, `api/routes.py` | `test_api.py`, `test_api_fuzz.py` | Mock API | Old frontend/deployment | PARTIAL |
| FR-009 | Readiness | `app/status.py`, config/readiness tools | `test_jetson_hardening.py` | Unknown/mock states | Actual components | PARTIAL |
| FR-010 | Capture | `ai/capture.py`, `session.py`, `tools/capture_session.py` | `ai/tests/test_productization_data.py` | Generated video | Physical webcam/session quality | HOST VERIFIED / physical pending |
| FR-011 | Data version/leakage | `ai/releases.py`, `dataset.py` | `test_productization_data.py` | Synthetic files/splits | Real corpus/near-review | HOST VERIFIED / real-data pending |
| FR-012 | Interchange | `ai/interchange.py` | `test_productization_data.py` | Local classification round-trip | Real platform export; future box converter | PARTIAL |
| FR-013 | Experiments/models/eval | `ai/experiments.py`, `evaluation.py` | `test_productization_ai.py` | Hash/metric fixtures | Actual training/predictions/Jetson | HOST VERIFIED foundation / AI pending |
| FR-014 | Reports | `app/analytics/reports.py`, `vision/tracking.py` | `test_product_reports.py` | Supplied record fixtures | Clean real subject/weight trials | PARTIAL |
| NFR-001 | Bounds | budget/storage/serial, capture/artifacts | hardening/fuzz/data tests | Failure budgets | Long real soak | HOST VERIFIED / deployed pending |
| NFR-002 | Serial recovery | `app/serial_link/` | `test_real_transport.py`, `test_protocol_fuzz.py` | Fake ports/twin | USB drop/replug | PARTIAL |
| NFR-003 | Local autonomy | `esp32/include/safety_logic.h` | Native harnesses | Offline twin | Power/network-loss rig | PARTIAL |
| NFR-004 | Reproducibility | `scripts/check_release.py`, experiment bundle | `test_release_check.py`, AI tests | N/A | Jetson env reproducibility | HOST VERIFIED / target pending |
| NFR-005 | Latency | processing budgets, benchmark tools | `test_jetson_hardening.py` | Host-overhead only | Actual Nano/model benchmark | NOT TARGET VERIFIED |
| NFR-006 | Compatibility | `uart_v1.h`, protocol/golden CSV | `test_uart_golden.py`, native vectors | Seven vectors | Physical peer/frontend | HOST VERIFIED wire / integration pending |
| NFR-007 | Local security | config/runtime/artifacts | fuzz/hardening/data/registry tests | Malformed input | Deployment auth/network | PARTIAL |
| SAFE-001 | MCU authority | board gates/dispatch, FeedService | native/API tests | Rejected safe commands | Final actuator rig | PARTIAL, gate enforced |
| SAFE-002 | Pump OFF/fault | water controller/disabled pump | native harnesses | Water fault scenarios | Physical stop/leak/dry run | PARTIAL |
| SAFE-003 | Servo/reboot | feed controller/persistence/disabled servo | native safety/replay tests | Interrupted dispense | Physical closure/NVS reset | PARTIAL |
| SAFE-004 | RTC invalid | `m4/rtc.h`, snapshot/feed policy | native driver integration | Fake RTC | Actual RTC/rollback/retention | PARTIAL |
| SAFE-005 | Weight fault | HX711/snapshot/feed policy | native driver integration | Fake ready/rails | Actual disconnect/drift/rig | PARTIAL |
| SAFE-006 | Shadow | config/pipeline/inactive registry | hardening/registry tests | No actuation | Real passive model run | HOST VERIFIED / real AI pending |
| SAFE-007 | Pin/output gates | `board_config.h`, `m4/actuator_interfaces.h` | compile guards/native tests | Disabled interfaces | Exact board/electrical/mechanics | HOST gate VERIFIED / physical pending |
| SAFE-008 | Conservative claims | analytics/reports/docs | report tests | Missing/ambiguous data | Real evidence if ever estimating | HOST VERIFIED constraints |

Test paths beginning `test_` are under `jetson/tests/` unless explicitly `ai/tests/`; native files are under `esp32/test/`. Traceability does not substitute for the test output in `PRE_HARDWARE_FINAL_BASELINE.md`.
