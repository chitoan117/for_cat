# Phase4 — R2 offline hardening, owner policy update applied

Candidate riêng, không gọi là R3. R1/R2 đã khóa giữ nguyên. **Aim35g; final band
30–40g inclusive (±5g)** là tiêu chí mới. ±0.2g chỉ còn trong evidence lịch sử của
baseline, không là nghiệm thu mới. **APP FLASH NO_GO; servo/pumpLOCKED; buzzerDISABLED.**

## Công việc hoàn tất / evidence thực
- Controller audit/state-machine fixes: `evidence/baseline_safety` failure và
  `fixed_safety_pm5` **12cases/101checks PASS**; masspolicy **11cases/58checks PASS**.
- Nativefile parser/framer/session:24snapshots xuyên lớp; session **9checks PASS**.
- Connected temporarySQLite/FastAPI E2E + data tests: **22pytestcases PASS** ở
  `evidence/backend_20261030_112615` (1E2Ecase nối24transportstates, không gọi24unit tests là E2E).
- Behavior **134C++checks PASS**; preference/dataextras **17pytestcases PASS**.
- Flutter **22unique tests PASS**: latestportabledependencyrun21 tại
  `flutter_20261030_114952` + newbaselinecomparison1 tại `flutter_20261030_121738`.
  Analyze sạch. Không cộng lượt chạy21 trước đó vào sốunique.
- Release **41unique cases PASS**:35initial +2nativePLAN/output +4DOSdevicenames;
  targeted20namechecks bao gồm16cũ, không cộng thành57.

Không chạy lại qualifiedR2suite47/28/115 nếu không cần; tests mới kiểm source đã
thay đổi. Các run trung gian thất bại giữ trongevidence: unusedparametercompile,
Windows temporaryDB cleanup và initial candidateINSERT thiếukind; đã sửa trước
kết quả PASS. Không chỉnh log baseline hoặc biến lỗi thành PASS thủ công.

## Trạng thái
VERIFIED PASS: WindowsC++14 strict builds, staticPython3.6grammar choownertools,
newsource integrity/archive checks, Flutteranalyze.
SIMULATION PASS: các suite trên, fakeOutput/mocktransport/tmpDB/MockClient.
NOT_RUN: hardeningGCC7.5ARM64, wholePOSIXBridgeWindows, targetGPU/camera/deploy.
BLOCKED: realowneridentitydataset/model và pre-flashbank/security/electricalgates.
NEEDS_PHYSICAL_VALIDATION: accuracy/mechanics/settling/lateinertia/powerloss/recovery.

Code: `candidate/`, `tools/`, `tests/`; policy `fixtures/feeding_policy.json`.
Xem7report còn lại cho bug/evidence/coupling/ownercommands. Không SSH, Serial,
camera, physicalactuator hoặc productionDB/service operation đã thực hiện.
