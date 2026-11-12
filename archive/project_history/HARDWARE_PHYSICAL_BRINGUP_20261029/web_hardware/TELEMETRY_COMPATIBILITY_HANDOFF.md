# Telemetry compatibility, pre-flash gates & Web diagnostics

**Update GCC75_R1:** USER đã chạy ARM64 thật và full Bridge compile FAIL do
7 misleading-indentation diagnostics trong `food_roi.h` (GCC7.5). Header đã sửa
bố cục, Windows edge/differential tests PASS; R1 ARM64 retest chưa chạy, nên
`ARM64_NATIVE_TEST_PASS=false`. Handoff đồng bộ 9 files/lệnh NEW-directory:
**`gcc75_fix/ARM64_GCC75_R1_HANDOFF.md`**. Baseline 279-file evidence được giữ nguyên
ở `gcc75_fix/baseline/`; `KIT_REVISION.json` ghi revision mới.

Đây là handoff hiện hành của candidate. Phân tích backup chi tiết vẫn ở
`BACKUP_AND_WEB_HANDOFF.md`. Quy trình: OpenCode chuẩn bị offline → USER thực
hiện từng bước được review → gửi log → đánh giá. **APP flash hiện NO-GO.**

## 1. Kết quả đã kiểm chứng

| Phạm vi | Kết quả | Evidence |
|---|---|---|
| C++14 parser/framer, json-c thật trên Windows | 12 nhóm PASS | `native_parser_result.json`, `native_parser_tests.log` |
| Session state machine, clock xác định | 17 checks PASS | `session_tests.log` |
| Backend/API và file integration | 31 tests PASS | `backend_tests.log`, `result.json` |
| Flutter controller/widget | 8 tests PASS, analyze sạch | `flutter_tests.log`, `flutter_analyze.log` |
| ARM64 owner-run replay harness | 26 cases đã chạy bằng Windows parser | backend test; không phải ARM64 acceptance |
| Toàn bộ POSIX Bridge trên ARM64 | **FAIL owner GCC7.5; R1 retest NOT_RUN** | xem GCC75_R1 handoff |
| Flash/deploy/new diagnostic Web trên hardware | **NOT_VERIFIED** | chưa thực hiện |

Backend integration mới dùng **output của executable C++ thật** từ full firmware
loop fixture → temporary SQLite `esp32_latest` → `Esp32StateReader` →
`RealHardwareProvider` → optional API router. Fixture và clock là OFFLINE_TEST_ONLY,
không phải UART vật lý. Shared kit tools 58 tests, firmware fake loops 17 cases và
6 compile guard rejections giữ nguyên evidence PASS của milestone trước.

Chỉ candidate trong kit được sửa. Production payload, primary Flutter và
`release_candidate_v2` không được patch. Finalizer đối chiếu upstream hashes và
273 files của accepted RC. Không SSH, serial, camera, service hoặc actuator access.

## 2. Contract thực và những sửa đổi chính

- Wire mode thật: **`diag_current_hardware`**; kit profile:
  **`diag_four_ultrasonic`**; firmware ID: `FORCAT_PHYSICAL_KIT_20261029_V1`;
  telemetry schema 2 / ultrasonic schema 1. Không đổi tên mode trên wire.
- Full synthetic firmware reports dài 4280–4295 bytes, vượt parser cũ 4096.
  Candidate dùng cùng giới hạn 8192 cho parser/framer: đúng 8192 accepted,
  8193 dropped, không truncate thành JSON giả. Fragmented input đã kiểm thử.
- Default policy chỉ nhận đúng kit profile/identity/schema; các mode
  HX711_REFERENCE, servo/pump hoặc mode đoán đều bị reject. Legacy current-hardware
  chỉ chọn bằng option riêng; không dùng để né unsupported-mode.
- Strict types, duplicate-key/JSON/depth checks, đúng 4 IDs/pins/ranges/nulls;
  unsafe actuator report latches lỗi. Disconnect/startup/reboot invalidate cache;
  uptime đóng băng không làm mới progress; millis rollover không giả reboot.
- Bridge candidate mặc định **PLAN_ONLY** trước DB/discovery/serial. Live option
  riêng chỉ dành cho owner sau cutover review; serial O_RDONLY, dog-warning=1 bị
  reject. Không triển khai đường TX điều khiển.
- PIR chỉ hiện qualified stable motion sau warm-up, fresh và valid; không fallback
  raw motion. HX firmware grams chỉ là observation, không feed authority.
- JSN1 chỉ tính % khi geometry/mount thực đã review; mặc định null. **JSN2 role
  TBD**, distance độc lập, không tính water % kể cả copy nhầm geometry vào config.
- Web phân biệt STALE/DISCONNECTED/TIMEOUT/SENSOR_ERROR; OLED/button hiển thị
  telemetry có kiểu dữ liệu; stale/null không biến thành 0 cm/0 g/false.
- GET `/status`, `/events`, `/events/export` cần VIEW_CAMERA; POST `/observations`
  và `/buzzer-test` cần CONTROL_SYSTEM. Log journal riêng, giữ tối đa 256 events;
  export JSON bounded, `physical_pass=false`, không mở port hoặc tạo feed request.
- Flutter optional panel tái sử dụng AppCard/LiveCameraPanel, có TEST/MOCK label
  trong offline tests, export log, OLED/button, channel state và JSN2 TBD.
  Router/panel **chưa mount vào live production**.
- Buzzer Web vẫn disabled/409: current sensor image không có manual GPIO2
  capability/RPC. Fake executor chỉ kiểm contract, không là acoustic PASS. Không
  dùng DOG warning/AI tự động để thay manual test. Servo/pump vẫn LOCKED.
- Chỉ FOOD_ROI; không WATER_ROI/drinking AI. Owner đã thấy CAT/DOG/NONE qua `/app`
  và `/kiosk` là owner-reported runtime evidence, không phải qualification của
  candidate mới hoặc bằng chứng tray membership.

## 3. GO/NO-GO trước flash

Machine-readable review: `PRE_FLASH_GATES.json`. GO từng phần không tự cấp quyền
flash. Backup đã hoàn tất, **không đọc lượt 3 hoặc lấy LASTEXITCODE cũ**.

| Gate | Hiện tại |
|---|---|
| A/B 16MB, cùng SHA256 | GO |
| Unique MD5 partition table 0x8000 khớp image | GO |
| Sensor app 400304 bytes vừa app0 0x640000 | GO |
| Original app local rollback, checksum/hash hợp lệ | GO |
| Actual running partition từ existing boot evidence | NO-GO: chưa có |
| Security/eFuse/secure-boot compatibility review | NO-GO: chưa xác minh |
| Cả 4 ECHO đo tại ESP32 input, protection ≤3.3V | NO-GO: chưa có số đo |
| Servo/pump external power isolated, RAM-loss acknowledgement | NO-GO: chưa review |
| Port/USB identity và original Bridge state/exclusive ownership | NO-GO: cần owner review |
| Native ARM64 Bridge build/replay | NO-GO: owner compile FAIL, R1 retest NOT_RUN |

Board hiện trên Jetson `/dev/ttyACM0`, Bridge **ACTIVE theo owner** và báo invalid /
`unsupported firmware mode`. Không chiếm port để đọc lại; không suy current wire
mode chỉ từ backed-up HX711_REFERENCE. COM8 là Windows transport lịch sử, chỉ dùng
lại sau khi owner chủ động chuyển board và review identity/exclusivity.

Hashes đã xác minh:

| File | Bytes | SHA256 |
|---|---:|---|
| Mỗi full backup A/B | 16777216 | `56a04d58bd8063e64f6b043a6b91d2d412c64d75e563ee58d81a83666d9a8e16` |
| `artifacts/diag_four_ultrasonic/firmware.bin` | 400304 | `a6ad4b3f6e21c1cfb0714f41f518ca90a75f031705a7bae5a2bb4fa99ebb4b56` |
| `web_hardware/rollback_original_app_00010000.bin` | 381984 | `820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826` |

OTA metadata candidate app0 at 0x10000 không phải actual running-bank proof.
Local rollback image PASS không phải hardware restore PASS. NVS 0x9000,
otadata 0xe000, table 0x8000 và bootloader 0x0 không nằm trong app-only write plan.

**Lệnh USER đầu tiên, Windows file-only:**

```powershell
& "D:\for_cat\.venv\Scripts\python.exe" -B "D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029\tools\verify_manifest.py"
```

Expected: `software_integrity=PASS`, `physical_pass=false`. Nếu hash mismatch,
dừng và gửi output; không tự regenerate manifest để che mismatch.

## 4. Native ARM64 build/test — USER thực hiện trong staging mới

Copy kit vào **NEW staging path** do owner chọn, ví dụ
`/home/toan/for_cat/hardware_diag_candidate_20261029`. Giữ relative tree của
`web_hardware/bridge_candidate`, `native_arm64_check.py`, `test_output` và
`firmware/include`; không copy local Windows venv/json-c/build caches vào Jetson.
Không overlay source/bin/unit/DB đang chạy. Không cần OpenCode SSH.

Python script tương thích system Python 3.6; dependencies: existing g++ hỗ trợ
C++14, pkg-config, json-c và SQLite3 development headers/libraries. Không tự apt
install, pip install, restart service hoặc start live bridge. Chọn lúc tải nhẹ:
compiler chạy tuần tự một process, O1; không TensorRT/CUDA/camera workload mới.
CPU/RAM thực khi build vẫn cần owner quan sát, chưa có target benchmark.

Đầu tiên xem PLAN, không tạo output hoặc mở thiết bị:

```bash
python3 /home/toan/for_cat/hardware_diag_candidate_20261029/web_hardware/native_arm64_check.py
```

Sau review, build + **file-only tests**, giữ production Bridge hoạt động:

```bash
python3 /home/toan/for_cat/hardware_diag_candidate_20261029/web_hardware/native_arm64_check.py --execute BUILD_AND_FILE_REPLAY_ONLY --out /home/toan/for_cat/hardware_diag_candidate_20261029/web_hardware/native_arm64_gcc75_r1
```

Output phải là thư mục mới, không overwrite lần chạy trước. Script compile
`parser_replay`, `test_session`, `test_food_roi` và **toàn bộ `esp32_bridge.cpp`** bằng
`-std=c++14 -O1 -Wall -Wextra -Werror`. Include protocol header từ kit firmware;
link json-c/SQLite3 theo pkg-config. Test 26 file replay cases + session 17 checks
+ FOOD_ROI 10 groups / 115 checks,
chạy whole Bridge **chỉ default PLAN** với sentinel DB/log paths và kiểm không
tạo DB/log/lock. Không truyền `--live-serial`.

Gửi result.json trong NEW R1 output directory và các `*.log`, compiler/dependency
versions, source/binary/fixture hashes. PASS yêu cầu result
`ARM64_NATIVE_TEST_PASS=true`, `whole_posix_bridge_compile=PASS`, đúng 26 replay
cases / 17 checks, zero serial/camera/service effects. Thiếu dependency/compile
fail/test fail = dừng, gửi log, không fallback thay production binary. Hiện tại
chưa có R1 PASS evidence, nên **ARM64_NATIVE_TEST_PASS=false; ARM64_R1_RETEST=NOT_RUN**.

## 5. App-only plan/rollback — có điều kiện, CHƯA CHẠY

Trước khi sinh plan đầy đủ, existing actual boot log phải qua
`tools/physical_acceptance.py boot-gate`, bind backup hash và log hash. Evidence
không rõ bank thì giữ NO-GO; không tự reset để thử. Gate output là review, không
phải flash authorization.

Sau khi *tất cả* gate mục 3 được owner review và bank đúng 0x10000, dùng
`tools/flash_prepare.py` với accepted receipt, `--running-partition-review` đã
verify, `--boot-app-offset 0x10000`, `--ram-loss-ack`,
`--external-actuator-power-isolated`, đúng transport và đúng esptool version.
Tool chỉ sinh argv; không thực thi. Với esptool4.8.1 chọn `--esptool-style v4`
và đường dẫn Python3.11/esptool hiện có đã review. Không chạy trường historical
`full_backup_command` trong output: A/B đã hoàn tất.

Dạng app-only argv esptool **4.8.1** sau khi gate đủ (tham khảo, không copy-run
ở trạng thái hiện tại; `REVIEWED_*` là placeholders có chủ đích):

```text
REVIEWED_PYTHON311 -m esptool --chip esp32s3 --port REVIEWED_PORT write_flash --flash_mode keep --flash_freq keep --flash_size keep 0x10000 REVIEWED_KIT/artifacts/diag_four_ultrasonic/firmware.bin
REVIEWED_PYTHON311 -m esptool --chip esp32s3 --port REVIEWED_PORT verify_flash 0x10000 REVIEWED_KIT/artifacts/diag_four_ultrasonic/firmware.bin
```

Conditional rollback app-only dùng cùng reviewed port/bank, image local SHA820c…:

```text
REVIEWED_PYTHON311 -m esptool --chip esp32s3 --port REVIEWED_PORT write_flash --flash_mode keep --flash_freq keep --flash_size keep 0x10000 REVIEWED_KIT/web_hardware/rollback_original_app_00010000.bin
REVIEWED_PYTHON311 -m esptool --chip esp32s3 --port REVIEWED_PORT verify_flash 0x10000 REVIEWED_KIT/web_hardware/rollback_original_app_00010000.bin
```

Không erase, factory/full-flash, table/bootloader/NVS/otadata write. Nếu actualbank
khác 0x10000 hoặc layout khác, dừng, không thay offset theo phỏng đoán. Restore
app không phục hồi RAM calibration. HX static measurement/35g accuracy đã
OWNER-accepted PASS; persistence và closed-loop dispense35g vẫn NOT_VERIFIED,
không cần cân lại full weights hoặc tối ưu calibration.

## 6. Trình tự A–H sau review, không chạy nối tiếp tự động

**A — Pre-flash:** kiểm integrity, backup/rollback, boot-bank/electrical/power,
native ARM64 logs, đúng USB và lưu original Bridge unit/path/ExecStart/hash/state
trong owner evidence. Mọi gate đủ mới review app-only plan.

**B — Supervised app flash:** USER thực hiện theo plan đã duyệt, một serial
owner; dừng đúng Bridge trong window đã chọn, giữ original-state rollback,
không tác động camera/AI/API services. Lưu command/stdout/exit/verify evidence.

**C — Boot/UART:** USER kiểm firmware ID/profile/mode/schema thực bằng đúng
serial workflow đã review. Không đồng thời Bridge và serial tool. Không bật
ultrasonic trước measured ECHO gate. Lưu raw timestamped report, reset/calibration
loss scope; không gọi tare/cal/save tự động.

**D — Bridge candidate:** native build phải PASS trước cutover. Backup/hash binary
và original unit configuration; new binary/config ở new staging path. Owner
review riêng việc single-owner cutover, bounded capture và rollback. Invalid,
unsupported, frozen, missing/stale phải hiển thị lỗi/null, không reinterpret mode.
Rollback về original binary/config/state nếu candidate không ổn; không suy restore
old invalid telemetry thành sensor PASS. RCv2 immutable.

**E — Web:** qualified bundle mới mount optional router + panel, journal DB riêng,
existing auth/Tailscale HTTPS/same-origin; candidate chưa được deploy. Kiểm 4
distances độc lập, JSN1 geometry/null, JSN2 TBD, PIR warm-up, HX current authority,
OLED/button, disconnect/stale/timeout và exported observations. No fake REAL
fallback, no duplicate legacy raw PIR tile như qualified result.

**F — Camera/AI:** tái sử dụng sole existing capture; đối chiếu CAT/DOG/NONE và
same epoch/frame/capture timestamp/JPEG. FOOD_ROI thực phải khớp producer và
geometry đã review; FULL_FRAME không phải tray-membership proof. Không mở webcam
thứ hai hoặc thêm WATER_ROI.

**G — Buzzer:** current Web button phải disabled/409. Chỉ một profile/manual RPC
mới được qualify riêng, electrical review GPIO2 ACTIVE_LOW 3.3V, MCU-enforced
2×200ms/gap200ms/auto-off600ms/cooldown60s/budget3 mới cho manual test. Receipt/ACK
không tự là acoustic PASS; không dùng DOG warning thay thế.

**H — Servo/pump/35g:** vẫn LOCKED và là bench milestones riêng. Không Web feed
control trong candidate này. HX static PASS giữ nguyên; servo mechanics, F5305S
OFF polarity/priming và physical closed-loop35g không suy từ static measurement.

Kết thúc mỗi phase: gửi raw log + USER_OBSERVED + expected/actual, rồi đánh giá.
Không cấp physical PASS chỉ từ phần mềm hoặc command receipt.
