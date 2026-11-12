# R2 changes / compatibility / safety audit

Đã đọc đầy đủ overnight PROGRESS_REPORT, TEST_RESULTS,216-linecandidatepatch,
SOURCE_BASELINE(27inputreferences) và verification_summary. Stage kiểm digest
overnightmanifest `c12fc0b7b748686b97eac013e2e60351eb22c254c767eaff121d013525628a54`
và payloadhashes, R1qualifiedmanifest `2d9c5d18e8b911874b033b4e93784ba7a34f591011002c46411a191c5196099c`.
SOURCE_PROVENANCE.json pin từng nguồn; không apply patch lên baseline.

| Thành phần | R1 → overnight → R2 | Compatibility / decision |
|---|---|---|
| CoreBridge esp32_bridge.cpp | Không đổi | SHAfebbe90a…; earlydefaultPLAN/read-only gated serial/noDOGTX giữ nguyên |
| telemetry/framer/channel/session | Không đổi | MAX8192, strictkitID/schema2/ultra1; đúng4pins;unsafe latch/freshness |
| food_roi.h | Giữ GCC75_R1 formattingfix | SHA f07f3ceb…; JSON/Unicode/numeric/ROI semantics không đổi |
| dog_warning_protocol.h | Không đổi | Không thêmUARTcommands/capability |
| dispense_bench.h | OvernightappendTARGET_OVERSHOOT, R2 thêm rawfreshguard | Header-only bench/simulation, không linked thành liveBridge feedtransport |
| diagnostics.py | Nhận overnightadapter | Wire/canonicalcache vẫnHEALTHY; diagnosticDTO chuẩn hóaOK/INVALID, age/reason/provenance |
| Flutterpanel | Nhận overnightpanel + R2fixtures | Hỗ trợ R2DTO/missingage graceful; sourceSIMULATED/mockbanner; không mountproduction |
| owner_behavior.h | Giữ overnight SIM-only policy | Không cấpidentityOWNER cho public/genericCAT; noactuator; no trainedmodel |
| offlinehistorypanel | Giữ overnight mock-only view | ACK/PENDING≠SUCCESS; sourceguardSIMULATED/physicalfalse |

## API/ABI cụ thể
- `diag_four_ultrasonic` là **profile**, wiremode thật vẫn `diag_current_hardware`.
  R2 không accept profile làm mode, không rewriteHX711_REFERENCE để checompatibility.
- FirmwarekitID/schema, sensorIDs/TRIG/ECHO, safetyflags, framebound và normalized
  cachecontract không đổi. Không có firmwareimage/partitionoffset update trongR2.
- `Reason::PERSISTENCE_FAULT=19` giữ nguyên; appendTARGET_OVERSHOOT=20. R2static_assert
  kiểm ordinal và Observationstandard-layout. Publicmethodsignature/datafields của
  controller giữ nguyên; thêmprivateinlinehelper không thêmstatefield.
- **Không giả định binaryABI cross-architecture hoặc mixR1object/R2headers.** R2
  targetbuild compile lại toàn bộ test/Bridge units vớiGCC7.5. BenchReason20 không
  là FEED_STATUSwirecode20: Backend test code0x14 phải giữPENDING, khôngSUCCESS.
- Existing `/api/v1/status`, `/feed/manual`, feeding/drinking-history/sessionroutes
  và authscopes giữ nguyên. Optionaldiagnosticrouterv1 **chưa deployproduction**.
  R2mappingOK/INVALID khácR1HEALTHY/measurement-state/SENSOR_ERROR: dùngpairedR2UI;
  strictconsumer cũ cần reviewadapter. Không tuyên bố semanticbackwardcompatibility
  cho consumer hardcodeR1channelstates. Canonical `/system` source không bị sửa.
- Diagnosticfields age/reason/telemetry_time là additions; clockhostmonotonic và
  deviceuptime tách biệt, không truyền thành UTC. Mockfixtures ởASGI/Flutter được
  sourceSIMULATED; rawwire giữgenuineprotocol và có FIXTURE_PROVENANCE.jsonsidecar.

## Overshoot protection
Overnight chặn **stable average** >35.2, nhưng launchPulse mới có thể nhận131g
gross khi baseline95 và vẫn mở; widenedstablewindow có thể average36g thành35.1g.
Probe dùng cùng testsource với overnightheader tái hiện cả2. R2 đọc qualified
fresh distincttimestamp saubaseline, chặn rawadded>target+tolerance trong cả tick
và launchPulse, global45g cap vẫn ưu tiên; faultclose/PWMoff/pendinginspection.
Settledguard cũ vẫn là defense thứ2. Biên34.8/35/35.2 và36 được test riêng.

Guard chỉ có ý nghĩa cho active transaction/qualified observations. Mẫu invalid/
stale không thành sốđo hợp lệ; finalCOMPLETE dựa trên settledwindow đã qualify.
Inertialfood rơi thêm **sau** terminalstatus, sensornoise/settling/mechanism và
tolerance vật lý vẫn NEEDS_PHYSICAL_VALIDATION; R2 không tự chứng minh accuracy.

## Không có source conflict được apply vào R1
R2 chỉ giữ minimalportableincludeclosure, không kéo incompleteCUDA/shadow/OpenCV
producer sources vào owner-run target. Backend tests dùng canonicalPythonapp từ
authoritativepayload **read-only trênWindows**; R2adapter/UI làreviewcandidate.
Native owner script Python3.6 không import Backend/Pydantic/Flutter. Targetbackend
Python/runtime/APIdeploy và GPUABI vẫn NOT_RUN, không được suy từ nativePASS.

Manualbuzzer capfalse/disabled, realfeedRPC bịblock, servo/pumpproductionLOCKED,
sensorfirmwarebin đãqualified không rebuild. Newsourcefix không tự xuất hiện trong
firmware đang chạy. Sau mọi PASS software, APPFLASH vẫnNO_GO tới reviewriêng.
