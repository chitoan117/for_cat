# Changes / rollback review

Source snapshot và hash trước sửa ở `offline_continuation/SOURCE_BASELINE.json`.
Runtime changes **chỉ candidate**, không apply vào qualifiedkit/production:

| File trong `offline_continuation/` | Thay đổi |
|---|---|
| `candidate/diagnostics.py` | SIMULATED provenance cho replay; explicitOK/STALE/DISCONNECTED/INVALID/TIMEOUT; age/reason và separateclockdomains |
| `candidate/flutter/hardware_diagnostics_panel.dart` | Clear staleexport; telemetryage display |
| `candidate/firmware/include/m4/dispense_bench.h` | Target-specific overshootfault trướcCOMPLETE |
| `candidate/bridge/owner_behavior.h` | Newsynthetic identity/ROI/distance/temporalpolicy + configurableconsumptionpreference |
| `candidate/flutter/offline_history_panel.dart` | Explicit mock-onlyACK/final/history harness |

Newtests: `tests/logic_tests.cpp`, `timeline_probe.cpp`, `test_integration.py`,
`candidate/flutter/test/continuation_test.dart`. Newfixture/evidence generation:
`make_fixtures.py`, `verify.py`; one-shot snapshots `stage.py`, `stage_dispense.py`.
`fixtures/` chứa labeledwire, C++dispenseoutcomes/sessiontimeline, actualASGI
contractcases và mockfeedhistorycontract. Không có privatecatimages/publicdata
được gánOWNER_CAT.

Maintenance package riêng: 5requiredmd, `readiness.py`, `serial_window.py`,
`boot_capture.py`, `security_flags.py`, `app_plan.py`, twoapproval/reviewexamples,
newtoolingtests/runner, private-evidence handling và ownintegrity. Agent chỉ chạy
Windows fake-service tests/defaults, không dùng execution flags.

`candidate_changes.patch` do continuationfinalizer tạo ghi before/afterdiff cho
changedsources và additions. **Patch là review artifact, chưa apply/deploy**.
Newmachine inventory/integrity ở `ARTIFACT_MANIFEST.json`; sourcehashes được so
với qualifiedinputs sau mỗi test run. No Gitcommit, cleanup hoặc migration.

Rollback software work: giữ production/qualifiedinputs nguyên trạng, bỏ qua
candidate mới nếu không accept; không cần undo deployedcode vì chưa deploy.
Không xóa oldrelease_camera/phase4/nativeevidence hoặc backup để làm gọn folder.
