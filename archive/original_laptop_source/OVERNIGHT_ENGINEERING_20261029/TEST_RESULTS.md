# Executed tests — offline continuation only

| Phạm vi mới | Kết quả | Evidence |
|---|---|---|
| Maintenance logic | 21 tests PASS, fake services only | kit `maintenance_readiness/validation/` |
| C++14 behavior + preference +35g | 11 groups /158checks PASS | `offline_continuation/evidence/logic_tests.log` |
| Real parser/session timeline | 6 cases PASS | `timeline_probe.log`, `fixtures/session_timeline.json` |
| Expanded parser/API integration | 26 unique cases PASS across focused runs | logs listed below |
| Flutter | 12 unique cases PASS across focused runs | original8 + targeted/currentcases |
| Flutter analyze | PASS, no issues | `flutter_analyze.log` |
| NewcandidateARM64 | NOT_RUN | originalGCC75_R1 PASS theoUSER không áp sang newpatch |

## Backend count, không cộng trùng / không che initial failures

Initial `backend_tests.log` có **17passed/1failed**:16unchangedwire/framing cases
và1ASGIexportPASS; mockmanual fixture thiếuFEED_MANUALscope. Sửa fixture dùng
explicit fake tailnet engineer, không nới auth production. Chạy lại đúngcase.
Sau khi thêm timeline/error/timefields, chỉ chạy các test liên quan:

| Latest targeted log | Passed |
|---|---:|
| `backend_test_cpp_to_sqlite_api_exports_actual_contract_cases.log` |1|
| `backend_test_mock_manual_feed_ack_final_duplicate_disconnect_and_histories.log` |1|
| `backend_test_actual_cpp_session_timeline_through_cached_api.log` |1|
| `backend_test_cpp_closed_loop_failure_never_becomes_api_success.log` |6|
| `backend_test_exported_contract_time_domains_and_error_reasons.log` |1|

**16 untouched wire cases +10 latest targeted =26 unique PASS**. Không tuyên bố
đã chạy một full26-case suite lần cuối. Toàn suite có thể chạy lại bằng command dưới.

## Flutter count

Initial8casePASS. Sau khi bổ sung states/time và đổi displayage, latest
`flutter_selected_0.log` có8ASGIfixturewidgetsPASS, `_1.log` có1timestampmappingPASS.
3casekhôngbịảnhhưởng (exportregression, mockhistorywidget, ACKstatelabels) giữPASS;
extendedACKerrorlabels cũng được targeted `_3.log` kiểm. **12uniquePASS**, không
cộng8+9=17. Initial regexselector dùng`|` bị Windows.bat xử lý thành shellpipeline;
runner được sửa tách selectors và whitelist, thất bại ban đầu còn ở
`flutter_selected.log`. Không coi lỗi harness là lỗi ứng dụng Flutter.

## Bug reproductions
1. `baseline_overshoot_probe.log`:stateCOMPLETE cho36g.
   `candidate_overshoot_probe.log`:stateFAULT/reasonTARGET_OVERSHOOT cho cùng input.
   “probePASS” chỉ nghĩa process chạy thành công và tái hiện expectedbug;
   **không phải baseline feedinglogicPASS**.
2. Qualified diagnostics source có thể xuất `source=REAL` cho executioncontext
   OFFLINE_TEST_ONLY. Candidate buộc SIMULATED; actualASGI/Dartfixtures test điều này.
3. Exporterror có thể giữ lastsuccessfulJSON trongcontroller. Regression chứng minh
   candidate clear exportedLog trên request/error mới.
4. Invalid/disconnected telemetry được phân loại riêng, không hiển thị cm/g cũ.

## Commands tái chạy khi có thay đổi liên quan
```powershell
$p = 'D:\for_cat\.venv\Scripts\python.exe'
$c = 'D:\for_cat\OVERNIGHT_ENGINEERING_20261029\offline_continuation'
& $p -B "$c\verify.py" --part native
& $p -B "$c\verify.py" --part timeline
& $p -B "$c\verify.py" --part backend
& $p -B "$c\verify.py" --part flutter
```
Focused backend: `--part backend --case TEST_FUNCTION_NAME`.
FocusedFlutter: `--part flutter --case 'ASGI|timestamp'` (runner tách selector an toàn).
Maintenance new-only: `python -B ...\maintenance_readiness\verify_new_tooling.py`.
Các lệnh này không run oldqualifiedsuites, không flash/device/service/camera.
Testfixtures là SIMULATION; mock finalstatus không là nghiệm thu35g thực.
