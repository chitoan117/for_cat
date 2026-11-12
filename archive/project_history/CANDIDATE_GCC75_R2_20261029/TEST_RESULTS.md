# GCC75_R2 Windows qualification — fresh run

Run thực: `validation_windows_20261030_005707/result.json`. Không lấy overnight
counts làm R2PASS; các suite dưới chạy bằng freshR2executables và R2adapter/UI.

| Program/suite | Executed result |
|---|---|
| FOOD_ROI |10groups /115checks PASS|
| DiagnosticSession |17checks PASS|
| Inherited behavior/preference/35g |11groups /158checks PASS|
| R2dispense safety |**16cases /126checks PASS**|
| Parser/framer |26cases PASS|
| Timelineduplicate/frozen/reconnect/latch |6cases PASS|
| Backend/API fullR2suite |**47passed**|
| Flutter fullR2suite |**28passed**|
| Flutteranalyze |Noissues|
| Transfer/runnerguard newtests |11passed, Windows/tempfiles/defaultPLAN|
| WholePOSIXBridge Windows |NOT_RUN; compiled/PLANtested only by futureARM64runner|
| R2ARM64 |**NOT_RUN**|

Counts báo riêng từngprogram/layer, không cộngtrùng semantic scenarios thành một
tổngmới. Rawlogs là sourceoftruth; native snapshotcounts và fixtures được tạo từ
stdoutthật, không chỉnh PASS thủ công. Newtoolingcommand/stdoutrecord ở
WINDOWS_TOOLING_RESULT.json; packageverifier được chạy thêm trên actualdelta khi pack.

## Newfocused scenarios
R2dispense: nominal/lower34.8/upper35.2; over35.21/36; under34.79; directlaunch36;
maskedwindow36;timeout;stale/invalid/nonfiniteHX;disconnect;duplicateID/duplicated
samples;journalclearfailure. Mọi outputfake được kiểmoff, no terminalCOMPLETE cho
failure. C++reports cósourceSIMULATED/physical_passfalse, integerreason không là
wirestatus. Lower/upper là floatrepresentation, không đo accuracyhardware.

16case controllerresults đi qua actualMockEsp32Transport→FEED_STATUS→FastAPItempDB
và fixtureFlutter. Thêm ACK-only, unknowncode20, wrongID, malformedlength,
PENDINGcode không tạoSUCCESS/terminalhistory. Duplicatefinal/idempotency chỉ1session.
All8telemetrycasewidgets và28fullFluttertests kiểm mockbanner/null/state/history.

## Probes (reproduction không phải baselinePASS)
`overnight_audit_probes.log`: DIRECT_LAUNCH_36=SERVO_PULSE_OPEN/opens1;
MASKED_WINDOW_36=COMPLETE. `r2_audit_probes.log`: FAULT/opens0 và
FAULT/TARGET_OVERSHOOT. Cả2process exit0 để ghi expectedobservations; không gọi
baselinefeedinglogicPASS. Originalovernightprobe36stable và qualifiedresults giữ nguyên.

## Repeat commands (chỉ khi có thay đổi liên quan)
```powershell
& 'D:\for_cat\.venv\Scripts\python.exe' -B 'D:\for_cat\CANDIDATE_GCC75_R2_20261029\verify_windows.py'
& 'D:\for_cat\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider -o 'pythonpath=D:/for_cat/CANDIDATE_GCC75_R2_20261029' 'D:\for_cat\CANDIDATE_GCC75_R2_20261029\tests\test_r2_tooling.py'
```
Đầu tiên tạoNEWvalidationdir, không overwrite sourcefixtures hoặc R1run. Không
startserver/Serial/camera. ARM64commands/expectedcounts trong README; outcome của
USER cần result/compilelogs/version/hash trước khi R2ARM64 được chấp nhận.
