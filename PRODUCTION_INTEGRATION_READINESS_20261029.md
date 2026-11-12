# FOR_CAT — Production integration readiness

Thời điểm bắt đầu quan sát: 29/10/2026 00:27:35 +07:00. Milestone overnight trước đã hoàn tất6/6, evidence `OVERNIGHT_ENGINEERING_20261029/handoff_result.json`, finalize00:25:29. Không kiểm thử hardware/deploy. Servo/pump giữ LOCKED.

## Tiến độ tuần tự

| Chặng | Offline | Production / phần cứng |
|---|---|---|
|1 AI/camera/state contract|PASS OFFLINE 00:33|NOT_VERIFIED|
|2 Fault injection/recovery|PASS OFFLINE 00:36|NOT_VERIFIED|
|3 Resources/backpressure|PASS OFFLINE; kết quả quan sát07:12|NOT_VERIFIED|
|4 API/Flutter/security|PASS OFFLINE 07:40 — được giao tiếp tục riêng|NOT_VERIFIED|
|5 Staging/rollback/handoff|PASS OFFLINE 08:25 — RCv2 đã đóng gói/kiểm thử|NOT_VERIFIED|

Source authoritative: `FULL_HARDWARE_INTEGRATION_20261027/payload`; bundles HX711_REFERENCE_PORT, CAT_APPROACH_DOG_BUZZER, E2E_OFFLINE_DEMO, LIVE_CAMERA_REMOTE_PREP et OVERNIGHT conservés. Aucun `JETSON_REAL_CAMERA_DEPLOY_20261028*` trouvé au top-level. Services actifs: information owner, état live non relu par SSH.

## Chặng1 — data-flow contract và thay đổi thực chất

**Trước:** legacy `cat_dog_trt -> stdout -> C++ ai_state_tap -> ai_latest(id=1)`; candidate `roi_ai_source` tự ghi cùng `ai_latest`, giữ cùng `DB-ai.lock`. Hai writer không ghi song song nếu lock đúng nhưng candidate và tap không thể pipeline chung; metadata ROI dễ mất nếu dùng legacytap, stdout candidate không tương thích.

**Sau (candidate, chưa deploy):** một `roi_ai_source` giữ `DB-capture.lock`, một capture/inference; producer không gọi SQLite nữa. Mỗi record `FORCAT_FRAME_V1 {json}` đi qua **Python `tools/ai_frame_tap.py`** giữ cùng `DB-ai.lock` tương thích namespace của C++ legacytap. Đây là sole state writer. Preview cùng packet/image/metadata đi worker HTTP; không ghi history/SQLite. Legacy detector/C++tap/supervisor vẫn nguyên vẹn. Adapter mới cũng parse được legacy `ENGINE_CONTRACT`, `DETECTIONS CAT/DOG`, `NONE ... MODE=... PROCESSED=...`, DOG priority; sau recordmodern đầu tiên không cho label-only legacy ghi đè metadata.

### Ownership/schema/transaction

- Capture + inference + original-normalized bbox: C++ producer duy nhất. API/Flutter không mở webcam hoặc infer.
- Identity: `(host_boot_id, producer_epoch, source_frame_id)`; sequence riêng `roi_sequence`. Preview dùng cùng producer_epoch và frame_id của capture, không tự tạo identity khác.
- `ai_schema_version=1`, `data_source=REAL`, `simulated=false`, `actuator_execution=false`. UNKNOWN là trạng thái không có bằng chứng, NONE là frame hợp lệ không có CAT/DOG; không identity mèo.
- `roi_observation_ms == updated_monotonic_ms == capture_monotonic_ms`, cùng host boot/monotonic clock; adapter từ chối age>1500ms/future/mismatched stamp. Không refresh tuổi frame bằng thời điểm commitDB. Modern API reader dùng horizon1.5s; legacy horizon3s giữ tương thích.
- Cache existing table, một atomic UPSERT id1/transaction, timeoutSQLite20ms; không migration/event insertion/feed request. Watermark chỉ tiến sau commit thành công. Busy/I/O failure không tạo SUCCESS; old cache tự stale, EOF best-effort DISCONNECTED.
- `StateWire` inference stdout nonblocking:1in-flight line +1latest pending,≤32768bytes, không trộn partial lines. TensorRT diagnostics redirectstderr trong candidate; original detector source không sửa. Sink disconnect khiến candidate dừng an toàn, không actuator.
- Bridge và API chặn cache explicit MOCK/SIMULATED. Legacy row thiếu attribution vẫn backward-compatible; không tự gắn frame metadata giả. `ApproachFusion` reset temporal species khi producer_epoch đổi nhưng **giữ consumed approach event**, tránh duplicate AUTO_CAT sau detector restart.

### Evidence

`PRODUCTION_INTEGRATION_20261029/test_ai_contract.log`:16tests PASS (frame→SQLite→AiStateReader, duplicate/out-of-order, epoch retirement, legacy adapter, writer lock, stale/malformed/source isolation). `test_state_wire_test.log`: C++14 bounded/partial sink và no duplicate AUTO_CAT qua epochrestart PASS. `test_fusion_compat_test.log`:19affected existingcases/186assertions C++14PASS, chạy lại vì fusion thay đổi. Compile compatibility ban đầu lỗi missing producer_epoch initializer; thêm explicit default, không sửa user test.

Full ARM64 producer/bridge build chưa chạy vì Windows thiếu target CUDA/TRT/json-c environment; có focused portable tests, không claim live compilation. OS writer-lock contention test chạy trên Windows; cùng namespace flockLinux đã implement nhưng cần kiểm trên Nano trướccutover.

## Chặng2 — fault injection/recovery

`test_fault_recovery.log`:8new tests PASS. SQLite exclusive lock/20ms timeout không tiến sequence, retry sau unlock; I/O failure không tự GOOD (old cache phải STALE, cần frame mới); transaction abort giữ nguyên complete row; startup TensorRT failure/crash/EOF thành UNKNOWN; NONE/UNKNOWN không giữ CAT; API restart tạo hub rỗng rồi reconnect; AI writer + manual/scheduled inbox cùngDB không execute; fake servo đã đóng nhưng finalgross131 (delta36) bị OVERSHOOT, không SUCCESS.

| Fault | Expected safe outcome | Evidence |
|---|---|---|
|A Camera disconnect/reconnect|OFFLINE; không dùng old frame|new hub/reconnect test + historical camera tests|
|B Detector crash/restart|EOF UNKNOWN; epoch mới/temporal reset|new adapter + state_wire/fusion tests|
|C TensorRT init failure|DISCONNECTED, không CAT/feed|new startup failure test; actual TRT init NOT_VERIFIED|
|D UNKNOWN/stale|UNKNOWN/no action, không refresh capture age|new contract/fault tests|
|E NONE|NONE hợp lệ, không retain CAT|new fault test|
|F CAT+DOG|DOG priority/no CAT feed|affected19case compatibility rerun|
|G UART disconnect|fail-closed/no TX execution|retained E2E safety cases; source transport unchanged|
|H CRC error|không callback/output|overnight focused E2E + independent CRC7frames|
|I Duplicate seq/request|drop frame, no duplicate approach request|new adapter/wire/fusion tests|
|J ESP32 reboot|boot/link reset; old-session rejected|overnight restart11checks retained|
|K HX timeout/INVALID|no feed, never0g fallback|retained inox27tests + overnight E2E|
|L Wrong calibration/bowl baseline|block/invalidate baseline|retained inox tests old mount/calibration/boot/tare/leftover|
|M Post-close mass increase|final overshoot blocks SUCCESS|new food-in-flight fault test|
|N SQLite busy/I/O|atomic oldrow; no authority/progress; stale|new actual SQLite lock/trigger tests|
|O API restart while viewing|new hub OFFLINE; old viewers cleared|new fault test|
|P Slow/disconnected viewer|bounded/latest, cleanup|historical timeout tests; resource stage adds coverage|
|Q PIR warm-up/noise|qualified telemetry invalid/settling; no feed|overnight PIR16checks/current-loop coverage|
|R Echo timeout/reflection|INVALID/null not0; no approach|overnight4channel27checks + affected FSMcases|
|S Manual+scheduled near-concurrent|one inbox identity per source; no physical success|new concurrent actualSQLite integration + retained scheduled transactiontests|
|T Restart with PENDING|request stays undecided; actualnull/executionfalse|new inbox recreation test; retained no-catchup/dedupe tests|

Coverage records mix new tests with explicitly retained evidence; không chạy lại toàn bộ A–T nếu implementation không ảnh hưởng. ACK vẫn receipt only; không có adapter code tạo FEED_SUCCESS. Faulttests dùng local tempSQLite/fake clock, không productionDB/actuator.

## Chặng3 — resource/performance engineering

Chặng3 bắt đầu sau checkpoint00:36:20. Lần kiểm tra giờ sau focused test trả về **07:12:58 +07:00**, xác nhận lại07:13:14; đã quá deadline05:00. Không có mốc quan sát trung gian để suy ra chính xác thời điểm vượt hạn, và không dùng thời gian test vài giây làm bằng chứng đồng hồ không đổi. **Không bắt đầu chặng4/5.** Chỉ lưu kết quả và báo cáo sau khi phát hiện quá hạn.

### Thay đổi và kiểm tra

- Existing capture tạo `cv::Mat frame` mới mỗi read rồi move vào LatestSlot; inference không mutate ảnh, preview giữ immutable refcount. Không clone nguyên ảnh trên inference thread, không cameraowner mới. Chưa có ARM64/OpenCV memory benchmark thực tế.
- Preview queue bổ sung bound metadata≤4096bytes, dimensions≤4096×4096 trước enqueue; pending1, preview6FPS, worker encode/HTTP độc lập, targetfit640×480, JPEG≤512KiB. Network deadline250ms/HTTP chỉ ở encoderworker; không chặn inference.
- Tìm/sửa gap replay: FrameHub trước đây quên frame ID khi frame stale bị xóa. Thêm watermark retained và bounded retired epochs16 để duplicate frame/old producer không được sống lại sau stale expiry. Camera status trả producer_epoch cho attribution.
- `test_resources_test.log`: C++14 thread/backpressure PASS,10checks,240offers khi fakeencoder bị giữ bằng promise; peak3 ownedimages, cuối test0; queue pending1/latest240; close đánh thức waiter. Local Windows elapsed **2.3873ms**, chỉ là fake-payload handoff test, **không phải Jetson FPS/GPU/JPEG benchmark**. Không dùng số này để dự đoán640×480 encode throughput.
- `test_stream_resources.log`:2focused tests PASS cho stale-watermark/retires và4viewers/oneJPEGslot/noDBfiles.
- Vì `live_stream.py` thay đổi, chạy lại affected historical `test_live_camera.py`: **27tests PASS** (file hiện có27cases; verification historical từng ghi32 bao gồm5middleware/manual-body cases ngoài file). Không ghi đè log/report cũ; log mới trong production bundle. Không chạy full backend/Flutter regression.
- State cache chỉUPSERTid1; streaming không ghi image/history vàoSQLite, không snapshot vào disk. Preview counters nằm trong RAM, stderr startup/shutdown/one-time warnings; không bổ sung log-file unbounded. Log rotation systemd/journald live chưa đọc, NOT_VERIFIED.
- Thread safety: demand atomic, LatestSlot mutex/CV, inference-only last_offer_; state stdout một thread. Test không phải TSAN hoặc proof không còn mọi race. Shutdown driver cancellation/OpenCV encoder worst-case trên Nano chưa kiểm định.

## Executive summary và trạng thái bàn giao

Hoàn tất **5/5 chặng chuẩn bị offline** với code và focused evidence. Chặng4 và chặng5 được người dùng giao tiếp tục riêng sau lần dừng theo deadline. Chặng5 chốt evidence **29/10/2026 08:25:26 +07:00**. Candidate integration đã chuyển từ directDB producer sang **framed stdout → sole-writer adapter**, được bọc bằng managed supervisor để writer giữ lock/commit sẵn sàng trước khi producer khởi động. Legacy detector/C++tap vẫn giữ nguyên cho runtime hiện tại và rollback. **Production deployment chưa được thực hiện hoặc nghiệm thu.**

**Production staging preparation đã hoàn tất**, khác với production/physical acceptance. Release mới chứa đầy đủ source và web sauPhase4; bundle overnight cũ không được chọn làm nguồn triển khai. Không có flash, SSH, UART/device mở, camera thật, actuator, service stop/restart, runtime/network/productionDB/NVS changes trong phiên chuẩn bị này. Không công bố production/physical PASS.

## Files changed

Tất cả đường dẫn dưới đây tương đối `D:\for_cat`; thay đổi chỉ Windows workspace.

**Source cập nhật:**

- `FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device/roi_ai_source.cpp` — bỏ SQLite writes, capture lock riêng, producer identity, framed nonblocking stdout, stderr diagnostics.
- `.../device/state_wire.h` — mới, bounded partial-line/latest stdout transport C++14.
- `.../device/preview_publisher.h` — preview dùng producer_epoch cùng AI record thay vì identity độc lập.
- `.../device/preview_queue.h` — metadata/dimension budgets.
- `.../device/approach_fusion.h` — reset temporal AI qua epochrestart, giữ consumed approach; default field tương thích aggregates cũ.
- `.../device/esp32_bridge.cpp` — loại cache explicitSIMULATED/MOCK, truyền producer_epoch cho fusion.
- `.../app/ai_frame_contract.py` — mới, schema/source/freshness validation, OS writer lock, canonical UPSERT và legacy protocol adapter.
- `.../tools/ai_frame_tap.py` — mới, bounded stdinCLI, startup/EOF DISCONNECTED; không camera/UART/inference.
- `.../app/ai_state.py` — modern freshness1.5s, source isolation và identityfields.
- `.../app/camera/live_stream.py` — watermark/retired epochs và producer_epoch status.

**Focused tests/tools mới `PRODUCTION_INTEGRATION_20261029/`:** `verify.py`, `test_ai_contract.py`, `test_state_wire.cpp`, `test_fusion_compat.cpp`, `test_fault_recovery.py`, `test_resources.cpp`, `test_stream_resources.py`; `native/*.exe`, compile/test logs, `result_*.json`, `HANDOFF_STATE.json`.

Frontend Flutter đã sửa tối thiểu ở chặng4 (chi tiết bên dưới); không redesign. Firmware ESP32 **chưa sửa/build lại** trong milestone này. C++14 native fake test executables đã build ở chặng1–3, không phải ARM64 inference binaries; chưa full-compile changed ROI producer/publisher/bridge vì thiếu targetCUDA/TRT/json-c trên Windows. Source và binary/report previous overnight giữ nguyên làm checkpoint lịch sử.

## Test/build evidence

Evidence root: `D:\for_cat\PRODUCTION_INTEGRATION_20261029`.

| Evidence | Kết quả |
|---|---|
|`test_ai_contract.log`|16Python tests PASS|
|`test_state_wire_compile.log`, `test_state_wire_test.log`|C++14 build/test PASS, stalled/partial stdout + epoch no duplicateAUTO_CAT|
|`test_fusion_compat_compile.log`, `test_fusion_compat_test.log`|Affected19cases186assertions PASS|
|`test_fault_recovery.log`|8new fault tests PASS, actual tempSQLite locks/abort/concurrency|
|`test_resources_compile.log`, `test_resources_test.log`|C++14 build/test PASS,10checks/240offers, peak3ownedimages|
|`test_stream_resources.log`|2new stream resource tests PASS|
|`test_live_camera.log`|27affected existing camera tests PASS|
|`result_test_resources_test_stream_resources_test_live_camera.json`|Combined last-stage evidence with timestamp; physicalfalse|

Không có full ARM64 build/engine deserialization/Jetson benchmark, deployment, live restarts hoặc physical sensor/actuator tests. Pipeline C++ syntax/ABI trên Nano vẫn là blocker bắt buộc trước deploy; portable tests không thay thế bước đó.

## Remaining blockers / severity

| Mức | Vấn đề | Next action |
|---|---|---|
|HIGH|Target ARM64/TRT ABI và engine probe chưa thực thi; không được suy từ Windows|Owner preflight/nativebuild, backup rồi supervised cutover/probe; dùng RCv2 mới, không launcher overnight directDB|
|HIGH|Live systemd unit/environment/camera ownership chưa đọc; không biết rollback live paths chính xác|Owner read-only inventory/backup trước mọi thay đổi; không guess units|
|HIGH|HX persistence/currentRAMcontext saureset vàservo closed-loop35g chưa nghiệmthu; staticHXđãPASS/accuracyaccepted|Giữlocks; integrationverification riêng, không fullweightretest/optimize|
|HIGH|Owner báo ESP32 firmware HX711_REFERENCE, bridge chỉ chấp nhận diag_current_hardware, valid telemetry=0|Giữ ESP32_TELEMETRY_PASS=NOT_VERIFIED; không đổi firmware/nới parser; camera/API-only rollout cần explicit acknowledgement|
|MEDIUM|New Python adapter required3.8+ (integration3.11), Linux flock interoperability và piped process shutdown cần targetverification|Dependency/ABI preflight, isolated ARM64 build và sandbox integration|
|MEDIUM|StateWire có thể drop intermediate state khi cache consumer chậm; JPEG preview có thể mới hơn latest committedDB|Chặng4 đã kiểm epoch/frame IDs, freshness và không overlay status lên JPEG; không giả định mọi lần poll AI/status đều cùng frame|
|MEDIUM|PIR qualified telemetry từ overnight chưa tích hợp end-to-end vào systemstate bridge/UI; legacy rawmotion vẫn tồn tại|Không diễn giải legacy CONFIGURED là physical validation; qualified PIR integration là công việc sensor riêng, không dùng PIR làm feed authority|
|MEDIUM|Driver cancellation, actual JPEG CPU/memory, CUDA/TRT init và network latency chưa kiểm trênNano|Owner-supervised resource checks, không dự đoán JetsonFPS từ Windows|
|LOW|Old optional ROI candidate chưa ownerreview bbox thực tế|Giữ FULL_FRAME; không bật ROI từ ảnh chén trống|

## Deployment bundles và exact rollback instructions

**Release mới:** `D:\for_cat\PRODUCTION_INTEGRATION_20261029\release_candidate_v2` —273files sauPhase4. ManifestSHA256 `8045b7a0406ad95aca9c00cc36c0f2bc5d46163bbe2a9dc2fb8f8ed508810db6`. Xem `docs/README.md` trong release và phầnChặng5 bên dưới. Old `OVERNIGHT_ENGINEERING_20261029/release_camera` vẫn là historical checkpoint217files, không dùng làm production release hoặc nguồn web mới.

Chưa cutover nên **hiện tại không cần chạy rollback runtime**; legacy runtime vẫn giữ nguyên. Bộ rollback mới có khả năng restore hai user-unit drop-ins dựa trên actual backup sau này, không chỉ đổi staging pointer. Nó không tự restoreDB/network/bridge và không tự chạy khi healthFAIL. Owner phải chủ động xác nhận:

```sh
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
REL=/home/toan/forcat-staging/releases/release_candidate_v2
BACKUP=/home/toan/forcat-backups/rc-v2-before-cutover
"$PY" -B "$REL/tools/control.py" rollback --release "$REL" --backup "$BACKUP"
# Chỉ trong maintenance window đã review backup/journal:
# Lặp lại lệnh trên với --apply --confirm RESTORE_PREVIOUS_USER_UNITS
```

DefaultDRY_RUN. Khi ownerapply: verify backup/hashes và owner edits; stop API/AI qua `systemctl --user`, kiểm camera/writerfree; restore đúng prior90-forcat-rc-v2.conf hoặc bỏ đúng drop-in mới đã kiểm, daemon-reload usermanager, start lại chỉ units đãactive trướcbackup. Không đụng baseunits/bridge/detector/engine/database. Nếu user thay baseunit/drop-in saubackup/cutover thì tool refuse, không ghi đè userwork. SQLite backupAPI snapshot là disaster-recovery evidence; DBrestore là thao tác riêng cần đóng mọi writer và bảo toàn DB+WAL+SHM, không tự copy đè DBđang chạy.

## First human-supervised action và thứ tự tiếp tục

1. **Hành động vật lý đầu tiên:** kiểm tra commonGND/mount chén và HX711 logic3.3V với nguồn module5V; giữ servo/pump khóa, theo `REAL_HARDWARE_BRINGUP_20261028.md`. Chưa flash/test từ agent.
2. **Hành động phần mềm tiếp theo:** owner chuyển RCv2 vào NEW inbox ngoài production và chạy exact read-only preflight ở phầnChặng5. Agent đã hoàn tất5/5offline và dừng; không tự deploy hoặc bắt đầu milestone mới.
3. Sau ownerreviewpreflight: stage/nativebuild/privateconfig/consistentbackup rồi mới supervised camera/API cutover; targetABI/runtime/network/ESP/HX/actuator vẫn chưa nghiệm thu. DefaultDRY_RUN của tools không thay runtime hoặc mở camera; mọiapply phải explicit confirmation.
4. Không coi stdout ACK/cache write/previewLIVE là FEED_SUCCESS hoặc physicalPASS; giữ actuatorlocks tới current-mount+mechanicalvalidation và explicit supervised authorization.

## Chặng4 — API / Flutter / security contract validation

**Phạm vi phiên tiếp nối:** chỉ chặng4 theo yêu cầu mới, không áp dụng việc tự tiếp tục chặng5. Đọc handoff3/5 trước khi sửa; chỉ chạy lại16tests contract của chặng1 vì `AiStateReader` bị thay đổi, không chạy lại native/fault/resource suites chặng1–3 không liên quan.

### Lỗi thực tế đã sửa

1. **API AI thiếu capture timestamp/age và provenance khi unavailable.** `app/ai_state.py` trả `captured_monotonic_ms`, `age_seconds`, `frame_metadata_available` và identity hiện có; modern rows được kiểm tra bằng validator của framed contract, schema phải int1. UNKNOWN không còn mặc định tự gắn source legacy stdout khi chưa đọc được cache. Legacy protocol vẫn tương thích và không được gán frame metadata giả.
2. **SIMULATED/REAL relabel race.** Controller trước đây có thể giữ `decoded=true` khi source hoặc producer_epoch đổi, làm ảnh đã giải mã của nguồn cũ nhận nhãn mới. Bây giờ đổi source/epoch sẽ tăng generation, bỏ decoded và về CONNECTING; chỉ callback của ảnh generation mới được chuyển LIVE.
3. **Late response / callback từ phiên xem cũ.** Thêm viewing-intent token cho start/stop/async polling; response cũ không cập nhật phiên vừa bật lại hoặc tạo timer cũ. Panel capture generation cho decoded/error callbacks, không cho ảnh đã tháo cập nhật phiên mới.
4. **HTTP same-origin chưa đủ cho remote camera.** Controller giờ yêu cầu HTTPS cho host ngoài exact loopback (`localhost`, `127.0.0.1`, `::1`); HTTP loopback giữ cho offline demo. Remote HTTP bị chặn trước khi gửi request. Mất quyền401/403 sẽ xóa LIVE/decoded; recovery cần ảnh mới.
5. **Nested AI provenance chưa được Flutter kiểm tra.** `FeederState` chặn explicit MOCK/SIMULATED AI trong REAL SystemState, kiểm modern frame identity/capture timestamp/age≤1.5s; NONE không hiện confidence của một animal detection.

### API–Flutter compatibility evidence

- **13 new focused API cases** sử dụng actual `StateTap -> tempSQLite -> AiStateReader -> RealHardwareProvider -> FastAPI`; CAT/DOG/NONE, legacy `/api/v1/status` và canonical `/api/status`, producer_epoch/source_frame_id/capturetime, modern freshness, UNKNOWN khi stale/source sai.
- Camera status và MJPEG `X-Frame-Id`/JPEG giữ đúng tuple producer/frame trong fixture cùng frame; source flags REAL/SIMULATED không bị trộn. JPEG là dữ liệu synthetic test, **không phải physical REAL evidence**. Không yêu cầu banner AI và preview luôn cùng lần poll: chúng có thể khác age/frame; frontend không vẽ bbox từ status lên ảnh khác.
- Sensor disconnected/stale ẩn giá trị; mấtAI hoặccamera không tạo feedcommand, không làm safety chuyển trạng thái được phép. Backend test assert transport không phát sinh feed và worker không tự chạy.
- `api_contract_fixture.json` được export trực tiếp từ FastAPI test rồi chính Flutter tests đọc qua `FORCAT_PHASE4_FIXTURE`; không dùng hai fixture tự viết riêng để giả định schema khớp.
- HX711 hiện có API `weight.grams` theo host calibration authority cũ; **gross/baseline/food_delta từ `bowl_mass.py` chưa wired vào API runtime**. Giữ unavailable/null; không thêm số giả hoặc coi gross130/food_delta35 là actual dispensed. Model/history test xác nhận request RECEIVED/decisionnull vẫn pending, không FEED_SUCCESS; dry-run actualgrams luôn null.

### Security verification

- VIEW_CAMERA-only xem status/ảnh được nhưng POST preview/manual bị403; FEED_MANUAL identity có thể enqueue dry-run idempotent, endpoint manual-actuation cũ vẫn503 với bridge mode. Received202 không biến thành completion/history success.
- Unauthorized identity, missing identity, wrongHost, wrongOrigin và HTTP-forwarded-proto đều403. Producer token không dùng được như viewer/feed credential; tailnet VIEW_CAMERA identity không đủ quyền privateproducer endpoint. Viewer5 bị429 khi đã có4viewer.
- MJPEG stream lease300s được kiểm bằng deterministicclock: hết lease đóng multipart và giải phóng viewer; lần mở mới phải qua auth. Flutter401/403 xóa decoded và reconnect mới. **Không có app session/token-expiry service mới**: Tailscale Serve chịu trách nhiệm identity session; existing stream bị giới hạn lease, không claim có immediate remote-session revocation giữa stream hoặc kiểm Tailscale thật. SystemState WS vẫn theo auth handshake hiện hành, chưa thêm session service.
- Không có producer secret trong source `lib/`; scan không thấy Bearer/private-key/producer-token material. Sentinel server token không có trong REAL/MOCK built assets hoặc Flutter source. Không in/đưa token vào streamURL. Đây là local contract/asset verification, không phải pentest hay xác nhận mạng thật.

### Files thay đổi trong chặng4

Backend authoritative snapshot:
- `FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/app/ai_state.py`.

Flutter chính `D:\DA_KT_NC\feeder_demo`:
- `lib/feeder_state.dart` — provenance/modernAI contract, NONE confidence.
- `lib/live_camera_controller.dart` — source/epoch/intent generations, HTTPS,401 handling.
- `lib/live_camera_panel.dart` — bind image callbacks theo generation.
- `test/production_phase4_test.dart` —10new tests, gồm3cross-language API fixture cases.

Evidence/tools trong `PRODUCTION_INTEGRATION_20261029`:
- `test_phase4_api.py`, `phase4_verify.py`, `phase4_evidence.py`.
- `phase4/api_contract_fixture.json`, `phase4/*_result.json`, full test/analyze/build logs và **`phase4/result.json`** (hashes/time/readiness).
- Offline build outputs `phase4/web_real/`, `phase4/web_mock/`. **Không phải staging/deployment bundle**, không triển khai và không thay `release_camera` cũ.

### Kết quả thực tế

| Kiểm tra | Kết quả | Evidence trong `PRODUCTION_INTEGRATION_20261029/phase4/` |
|---|---|---|
|Backend/security focused|**36 PASS** =13newAPI +16affectedAI contract +7bad-cache reader cases|`backend_focused.log`, `backend_result.json`|
|Flutter focused|**33 PASS, 0 skipped** =10new +23affected existing camera/state/backend/HX/mock cases|`flutter_focused.log`, `flutter_result.json`|
|Flutter analyze|**PASS — No issues found**|`flutter_analyze.log`|
|Flutter Web REAL release build|**PASS**|`flutter_build_real.log`, `build_result.json`|
|Flutter Web MOCK release build|**PASS**, mainJS khác REAL|`flutter_build_mock.log`, `build_result.json`|
|Fixture/artifact hashes + secret sentinel|**PASS**|`result.json`, source and evidence SHA256|

Lần thu thập đầu bị Python import shadowed bởi checkout root cũ khi pytest collect test dưới snapshot; runner đã pin `pythonpath` đúng authoritative payload như focused camera runner trước đây, rồi36tests PASS. Đây là lỗi test-runner import path, không sửa production để che lỗi. Sau khi bổ sung HTTPS guard đã chạy lại affected Flutter tests/analyze/build; bảng trên là kết quả cuối, không cộng các lần chạy lặp.

**Remaining blockers:** full ARM64/CUDA/TensorRT compile/ABI, Linux process/lock/supervisor, actual MJPEG camera/network/Tailscale, production bundle/cutover/backup/rollback và current-mount HX/actuator validation vẫn NOT_VERIFIED hoặc chờ chặng5. Không thay actuator authority, không tạo migrationDB, không mở camera/serial, không flash hoặc restart/deploy.

**Checkpoint chặng4:** `WEB_API_INTEGRATION_OFFLINE_READY=YES`. Khi chốt chặng4 đã dừng theo yêu cầu; chặng5 bên dưới được thực hiện theo yêu cầu riêng tiếp theo.

## Chặng5 — production staging và safe deployment preparation

### Release/manifest/source authority

Path: **`D:\for_cat\PRODUCTION_INTEGRATION_20261029\release_candidate_v2`**. Bundle mới273files, không copy bất kỳ source/assets từ `release_camera` cũ. Authoritative payload + currentPhase1–4; detector/geometry reference từ `OFFLINE_REVIEW_20261024/project/jetson/ai` là dependency source của currentproducer; firmware headers từ authoritativeguard_tuning để compilebridge portable, không chứa firmwareflash. Web lấy trực tiếp `phase4/web_real` và `phase4/web_mock`, hash khớp qualificationPhase4; Flutterlib/pubspec kèm để traceability. Không rebuild/rerun frontend đãPASS vì source không đổi.

- `manifest.json`: từngfile có sourcepath, `${RELEASE_DIR}`destination, SHA256,bytes,groupA–J,role,dependencies,overwrites_production=false và requires_arm64_build. Systemdtemplate có activationdestination riêng và yêu cầu verifiedbackup trướcoverwrite.
- `manifest.sha256`: **`8045b7a0406ad95aca9c00cc36c0f2bc5d46163bbe2a9dc2fb8f8ed508810db6`**.
- `SHA256SUMS`: per-artifact checksums; SHA256 của filechecksum **`663509918d6f7d2aa71aec5c024be2868be51394c2ae5348ee69a8643a38db6f`** được ghi trong phase5/result.json.
- `dependencies.json`, `schema/contract.json`, `schema/additive_reference.sql`, `systemd/candidate-override.conf.in`, `docs/README.md` là phần của manifest. Không chứa liveDB/NVS/engine/privateproducer token hoặc .envproduction.

Lưu ý digest manifest là integritypin, không phải chữ ký xác thực; owner so sánh hash qua kênh tin cậy. Release đã qualified thì giữ immutable; packagecontrol yêu cầu Python`-B` để không tạo pycache phá manifest.

### Scripts thực tế đã tạo

Trong `phase5/tools/`, được đóng gói vào `release_candidate_v2/tools/`:

| File | Vai trò |
|---|---|
|`control.py`|CLI integrity/preflight/stage/configure/build/backup/probe/cutover/verify/rollback; defaultDRY_RUN cho mọi write/build/probe/HTTP; exactconfirmation + Linuxgate|
|`integrity.py`|Strict manifest/checksum/path/symlink/extra-file checks; streaming SHA256; verifiedbackup receipts|
|`preflight.py`|Read-only arch/compiler/Python/OpenCV/TRT/CUDA/engine/cameraowner/permissions/memory/disk/userunits/effective-safe-env/DBschema|
|`native_build.py`|C++14 build riêng vàoNEW stagingdir; chọn CUDApath thực từpreflight;4native binaries/logs/receipt, không run/deploy saucompile|
|`engine_probe.cpp`|Target-only runtime/headerABI + engine deserialization/bindings probe; không camera/inference; chỉ chạy saulegacyAI đãstop|
|`runtime_config.py`|NEW private0600 config/token, initialVIEW_CAMERA-only; cố địnhMOCK/MOCK/MOCK+stateREAL/shadowtrue; không sửa .envproduction|
|`managed_runtime.py`|CandidateAI/API entrypoints; StateTap writer giữcanonical lock và initialcommit/ready handshake trướcproducer; peer exit cleanup; samecapture/epoch/frame; systemd restart/backoff|
|`operations.py`|Consistent readonly-sourceSQLitebackup + unitfiles, controlled two-user-unit cutover, exactbackup-based rollback; noautoRollback|
|`post_verify.py`|BoundedGET-only health/state/status/MJPEG/unauthorizedcheck; camera/APIcontract tách systemtelemetry blocker và physicalstates|

Windows packager/qualification: `phase5/build_release.py`, `test_release.py`, `test_packaged_python.py`, `test_packaged.cpp`, `verify.py`; generatedlocal schema snapshot được giữ trong `phase5/work`, không phải productionDB và không đưa vào release. Sourceapplication/Phase1–4 không sửa trong chặng5; các readinessYES trước giữ hiệu lực bằng exactsource/webhashcheck và packaged import/contract proof.

### Exact first commands (owner thực hiện sau)

**Windows PowerShell:** xác nhận inboxremote chưa tồn tại và hostđúngNano, rồi:

```powershell
scp -r "D:\for_cat\PRODUCTION_INTEGRATION_20261029\release_candidate_v2" toan@server-jetson:/home/toan/forcat-inbox-rc-v2
```

**Jetson — lệnh đầu tiên, chỉ đọc:**

```sh
/home/toan/for_cat/.venv/jetson-integration/bin/python -B /home/toan/forcat-inbox-rc-v2/tools/control.py preflight --release /home/toan/forcat-inbox-rc-v2 --production-root /home/toan/for_cat
```

Không sử dụng systemPython3.6. Preflight cần Python3.11, PythonSQLite>=3.24choUPSERT, pydantic>=2, OpenCV4/json-c/sqlite3pkg-config, CUDA/TRT headers/libs, aarch64. Ubuntu18.04 có thểlinkSQLite3.22: script sẽblock, không tự nângOS/package. Enginehash historical phải khớp; khác thì review chứ không replace. Minfree512MiBdisk/256MiBMemAvailable chỉ là startinggate, không đảm bảo performanceNano. Live service env và user-unit paths chưa đọc trong phiên này.

### Backup/build/cutover flow

Full commands/confirmation strings nằm trong release`docs/README.md`. Stage mới ở `/home/toan/forcat-staging/releases/release_candidate_v2`; build mới ngoàiimmutable release, ví dụ `/home/toan/forcat-staging/build/release_candidate_v2/run1`. Buildcompileproducer/bridge/legacytap/probe nhưng **không install/start bridge mới**, không cutover saubuild.

Trước mọi runtimewrite, owner backupvàoNEW `/home/toan/forcat-backups/rc-v2-before-cutover` bằng SQLitebackupAPI consistent và user-unit fragments/drop-ins/active states/protectedhashes. integrity_check phảiok, receiptfiles checksummed. Schemacheck tên/type/PK và extraNOTNULLno-default phải compatible; missingtables chỉ additiveCREATEIFNOTEXISTS bởi apphiện hành; không DROP/ALTER/DELETE/reset/migrationdestructive.

Cutover chỉ khi ownerapply với `CUTOVER_CAMERA_API_ONLY`, privateconfig và matchingARM64receipt, verifiedbackup, explicit `--ack-telemetry-blocker`. Nó stopAPI rồiAI qua **systemctl --user**, dừng cả supervisor cũ; yêu cầuunitsinactive/camerafree/writerlockfree. Targetengineprobe saustopAI, targetsystemd-analyze trướcinstall; sauđó chỉwrite hai90-forcat-rc-v2.conf drop-ins, daemonreload, kiểm effectiveExecStart rồi startAPItrướcAI. Unknown lifecyclehooks hoặc owneredits/missingbackup/busydevice/probefailure đềuSTOP; không killall/force/autoRollback.

Managedpipeline dùng chính `app.ai_frame_contract.StateTap` và WriterLock đãPASS, bọcentrypoint để handshake/processcleanup; standalone `tools/ai_frame_tap.py` vẫn được đónggói. LegacyC++tap không chạy cùngnewwriter. Mộtproducer mộtCapture/inference, previewworker/latestqueue không tạo cameramới. Restart là cảgroup, backoff5s/startlimit5per60s, KillModecontrol-group. No UART/controlcommand hoặc actuatorpermission được thêm.

### Focused verification và kết quả

| Bằng chứng | Kết quả |
|---|---|
|`phase5/focused_tests.log`|**34 PASS**: exactmanifest/group/source/webhash, paths/tamper/defaultDRYRUN/confirmation/Linuxgate, schema/import/dependencies, fakebackup/cutover/rollback, writerready/cleanup, postverifylabels và fuser-error fail-closed|
|`phase5/packaged_cxx14_compile.log`|**C++14 BUILD PASS trên Windows**, compile againstheaders thực trongRCv2|
|`phase5/packaged_cxx14_test.log`|**PASS**, fakeStateWire/preview/fusion/bindingcontract; ARM64buildNOT_VERIFIED|
|BundledPython subprocess|**PASS** từreleasepath: compatibleadapter→tempSQLite→reader, duplicate/SIMreject/stale; appimport/create withmockcapture, nofeed|
|Phase4 source/web qualification|**MATCH**; không chạy lại36backend/33Flutter/analyze/build củaPhase4|
|`phase5/result.json`|273files, checksum/evidencehashes, readiness/time, knowntelemetryblocker và physicalfalse|

Testsystemd/camera/probe đều fake; DB là temp/local riêng. Không có `systemd-analyze` targetPASS hoặc targetARM64/CUDA/TRT probePASS từ Windows. Source originaldetector/C++producer không bị rewrite trongchặng5.

Lỗi chuẩn bị đã xử lý: Windows tempfileDB cleanup bị pendingconnection làmpackagingdở; giữ sandboxworkspace và chỉresume exactincompletecopy đãverify, không overwriteunknownfiles. Tests đầu phát hiệnWindowsPath backslash trong renderingLinuxunit/buildargv; đã chuẩn hóaPOSIX. Qualify thêm selectedCUDAroot không giảđịnhsymlink và rollbacktừchối baseunitowneredit. `fuser` code1 kèm permission/device error không được coi camera-free; cảcutover lẫnruntime đều failclosed. Draft chỉrefresh trướcfinalqualification, không sửa releaseđãfreeze hoặc userfiles. Kết quả34PASS trênlàlầncuối, không cộng reruns.

### Post-deploy acceptance / security / blockers

Toolverify mặcđịnhplan; owner `--apply --confirm VERIFY_READ_ONLY` mới gửiGETbounded. Localcheck dùngtrustedloopbackidentityheaders, **không chứng minh TailscaleServe thật**. Nó kiểmAPIhealth, modernAI REAL/nonSIM/fresh/epoch, cameraREAL/MJPEG/latestbudget, safetyexecutionfalse và unauthorized403; khôngPOSTfeed/privateproducer/UART.

Camera/APIcontract có thểPASS nhưng overall **BLOCKED_ESP32_TELEMETRY** khi validtelemetry=0. Không promote flagsphysical. SaulocalPASS, ownerreview existingServeconfig, backupmapping, privateHTTPSsameorigin `/flutter/`, LAN+tailnet rồiphoneWiFiOFF/4G+Tailscale. `--remote` dùngHTTPSTLS thật, khôngforgedServeheaders; chưathựchiện. Không toolnào chỉnhnetwork/Serve/Funnel/router. Existing300sMJPEGlease/VIEWscope vẫn giữ, không giảđịnhimmediate sessionrevocation.

**Blocker rõ ràng:** owner hiện báo `/dev/ttyACM0` mode`HX711_REFERENCE`, bridge chỉhỗtrợ`diag_current_hardware`, telemetryhợplệ0. Khôngflash/đổifirmware, không nớiparser đểacceptmọimode; telemetry/HX/servo/pump phải nghiệmthu riêng. APImaintainsnull/UNKNOWN vàlocks khi khôngcódữliệu; bowlgross/fooddelta vẫn chưa wiredliveAPI. LegacyservicesACTIVE là thôngtinowner, không phải liveinventory doagentđãđọc.

**Chốt5/5offline:** `JETSON_PRODUCTION_STAGING_READY=YES` nghĩa bundle/scripts/evidence sẵn cho supervisedtargetacceptance. **Không có productiondeploy/cutover, camera/serialopen, flash, service/systemd/network/productionDB/NVS changes.** Dừng, không tự triểnkhai hoặc mởmilestonemới.

## Readiness flags (scope đã kiểm chứng)

### Latest backup acceptance + Web hardware preparation (kit-only extension)

ActualA/B readonly each16777216bytes SHA56a04d58…6d9a8e16matchingPASS. ActualMD5
table0x8000 khớpsensorbuild; bootloaderchecksum/hashvalid, app0validoldHXreference
381984bytes/SHA820cdeec…3a4b9826, app1erased. OTAstandardIDFmetadata chọncandidate
app0/0x10000; runtimebank vẫnNOT_VERIFIED. LocalrollbackextractPASS, actualrestore
NOT_VERIFIED. Khônglượt3/oldexitcode, không đổi/sourceproduction hoặc RCv2.

Handoff hiện hành `HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/TELEMETRY_COMPATIBILITY_HANDOFF.md`;
backup detail ở `BACKUP_AND_WEB_HANDOFF.md`, pre-flash gates ở `PRE_FLASH_GATES.json`.
Existing4channelJSON/newkit fullframes4280–4295bytes vượtoldbridge4096; không
được assumeWebtelemetryready. Separatekitbridgecandidate8192 +qualifiedPIR/FWgrams
forwarding đã qua **Windows C++14/json-c parser 12 nhóm PASS / session17 checks**.
Toàn bộ POSIX Bridge ARM64 vẫn **NOT_RUN**, có owner-run default-PLAN build/replay
script Python3.6-compatible riêng, không serial/service access. OptionalFastAPI
router/JSN1geometry/log export/OLED/button và FlutterpanelreuseUI có31backend+8FlutterPASS/analyzeclean,
khôngđượcmount/deploylive. BuzzerWeb testdefaultdisabled409: sensorimage không có
manualGPIO2capability vànochangingrealUARTexecutor. Không dùngDOGwarning đểtestâm.
KhôngWATER_ROI/drinkingAI, khôngservo/pumpcontrol. RCv2giữqualificationcũ nhưng
khôngthaycho newqualifiedhardwaretestbundle; source/codecandidate cầncontrolled
targetbuild/deployreview riêng. ExistingHXstaticacceptance khôngbịhạ hoặc yêu cầuretest.
JSN2 giữ roleTBD/null waterpercent. Actual C++ replay→temporarySQLite→realreader/
provider→API đã PASS, fixture OFFLINE_TEST_ONLY, không phải physicalUART. Board trên
Jetson/BridgeACTIVE-invalidmode và CAT/DOG/NONE visible qua `/app`/`/kiosk` là latest
owner report; agent không poll runtime. APPflash tiếp tục NO-GO vì actualrunningbank,
4ECHO measured protection, power/RAM/USB review và nativeARM64 evidence còn thiếu.

### HX711 physical-static acceptance correction —29/10/2026

Đo tĩnh đã thực hiện trên ESP32-S3 thật, HX711GPIO4/5/loadcell1kg/tôinox; owner
chấpnhận tare/loadresponse5/10/20/35g và latest35g→34.981g, abs.error0.019g≈0.054%.
**Không tốiưu thêm, không yêu cầuweightseriesretest.** Hồ sơscoped vàprovenance:
`HARDWARE_PHYSICAL_BRINGUP_20261029/HX711_ACCEPTANCE.json`, `HX711_EVIDENCE_NOTES.md`.
Đãverify436samples của4originalarchivedphysicalwindows/hashes. Latest34.981g là
owner-confirmedtrial khác archive35gmean34.582390; matchinglatest rawfilechưalocal,
attachexistinglogkhi có, khônggánnhầmrawsession/khôngyêucầuđolại.
RAMpersistence saureset vàclosed-loopservo35g NOT_VERIFIED làintegrationgates
riêng, không phải staticmeasurementFAIL. Không đổicoefficients/protocol/firmware,
không mởACTauthority. LatestownerA/B đãcomplete vàdirectfilehashPASS; xemkit
`web_hardware/BACKUP_AND_WEB_HANDOFF.md`, không yêu cầu lượt3/oldexitcode.

```text
AI_DATA_CONTRACT_READY=YES
FAULT_INJECTION_OFFLINE_PASS=YES
CAMERA_RESOURCE_OFFLINE_READY=YES
WEB_API_INTEGRATION_OFFLINE_READY=YES
JETSON_PRODUCTION_STAGING_READY=YES
ARM64_TENSORRT_BUILD_PASS=NOT_VERIFIED
JETSON_REAL_CAMERA_PASS=NOT_VERIFIED
TAILSCALE_REMOTE_PASS=NOT_VERIFIED
ESP32_TELEMETRY_PASS=NOT_VERIFIED

JETSON_PHYSICAL_INTEGRATION_PASS=NOT_VERIFIED
HX711_PHYSICAL_STATIC_TEST=PASS
HX711_STATIC_MEASUREMENT_PHYSICAL_PASS=YES
HX711_35G_REFERENCE_MEASUREMENT=PASS
HX711_MEASUREMENT_ACCURACY_ACCEPTED=YES
HX711_RETEST_REQUIRED=NO
HX711_CALIBRATION_PERSISTENCE=NOT_VERIFIED
HX711_CLOSED_LOOP_DISPENSE_35G=NOT_VERIFIED
ACTUATOR_PHYSICAL_PASS=NOT_VERIFIED
```
