# FOR_CAT — GCC75_R2 consolidated source candidate

**R2 ARM64 = NOT_RUN. APP FLASH = NO_GO. Không deploy production.**

R2 kết hợp coreBridge GCC75_R1 đã owner-confirmedPASS với overnight API/UI,
simulationpolicy và controllerbenchfix trong **một source tree riêng**. Không có
ESP32firmwarebin mới, CUDA/model binary, serviceunit hoặc productionDB trongdelta.
Servo/PumpLOCKED; manualbuzzerDISABLED. `COMPATIBILITY_REVIEW.md` ghi rõ scope/ABI.

## Windows regression đã thực hiện
Run mới: `validation_windows_20261030_005707/result.json`.
- C++14 strict builds:6file-testexecutables; wholePOSIXBridgeWindows **NOT_RUN**.
- FOOD_ROI10groups/115checks; session17; inheritedbehavior/35g11groups/158checks.
- R2dispense16cases/126checks; parser26cases; timeline6cases.
- **47 backend/API tests**, **28 Flutter tests**, analyze sạch, mỗi suite chạy một
  lượt full riêng trongR2, không cộng kết quả overnight hoặc repeatedruns.
- R2tooling11tests:manifesttamper/missing/traversal, freshoutput/defaultPLAN và
  Windowskhông được promote thànhARM64. Xem WINDOWS_TOOLING_RESULT.json.

Lệnh tái chạy khi review/thay đổi liên quan (NEW output, không overwrite):
```powershell
& 'D:\for_cat\.venv\Scripts\python.exe' -B 'D:\for_cat\CANDIDATE_GCC75_R2_20261029\verify_windows.py'
```
Rawlogs/derivedfixtures ởnew `validation_windows_*`; sourcefixtures cố định. Fresh
WindowsC++ executables dùng chính R2headers, không dùng cachedR1parserexe choAPI.

## Transfer delta / nguồn được giữ nguyên
`DELTA_FILES.txt` là exactrelativefilelist của `R2_SOURCE_DELTA.zip`. Gói gồm nguồn
R2 thayđổi/mới và smallunchangedR1includeclosure cần cho build standalone. Đây không
phải whole-repository copy. Không copyWindowsvenv/json-c .a/.exe, backups hay images.
Root590manifest, GCC75_R1delta, overnightpackage/source/testrecords được hash-pin,
không rewrite. Newmanifest riêng `TRANSFER_MANIFEST.json` / `.sha256`.

USER dùng SFTP vào **NEW** remote root:
`/home/toan/for_cat/hardware_diag_candidate_gcc75_r2_20261029`

Giữ directorylayout bên trongZIP. R1root vẫn là
`/home/toan/for_cat/hardware_diag_candidate_20261029`; đặc biệt giữ nguyên
`web_hardware/native_arm64_gcc75_r1_20261029_171958/` và tất cảlogs/PASS.
Agent không SSH/upload. Không overlay candidate vào .native-build/production.

## Owner-run ARM64 GCC7.5 — file-only

Chạy bằng terminalUSER. So sánh SHA256 manifest/ZIP với recordWindows bàn giao;
verifier có `--expected-sha256` để pin digest ngoài gói.

```bash
R2=/home/toan/for_cat/hardware_diag_candidate_gcc75_r2_20261029
python3 -B "$R2/verify_transfer.py"
python3 -B "$R2/native_arm64_r2.py"
```

Expected:first `transfer_integrity=PASS, revision=GCC75_R2`; second `mode=PLAN_ONLY`,
ARM64_NATIVE_TEST_PASS=NOT_RUN. Hai lệnh không build, tạooutput hay chạmdevice/service.

Sau review, USER chạy **BUILD_AND_FILE_REPLAY_ONLY**:

```bash
OUT="$R2/native_arm64_r2_$(date +%Y%m%d_%H%M%S)"
python3 -B "$R2/native_arm64_r2.py" --execute BUILD_AND_FILE_REPLAY_ONLY --out "$OUT"
RC=$?
printf 'SCRIPT_EXIT_CODE=%s\nOUTPUT_DIR=%s\n' "$RC" "$OUT"
```

Output phải NEW directchildR2root, prefixnative_arm64_r2_; mọiR1/existing/outside
path bị từ chối. Compiler7.5.0, Python3.6-compatible stdlibscript; pkg-configjson-c/
sqlite3developmentdeps phải có sẵn. Build tuần tự `-std=c++14 -O1 -Wall -Wextra -Werror`;
không cài/updatepackage. Cần USER chọn lúc tài nguyên phù hợp; chưa benchmarkCPU/RAM.

7binaries: parser_replay, test_session, test_food_roi, logic_tests, timeline_probe,
dispense_regressions, **whole esp32_bridge.cpp**. Chỉ testexecutables và Bridge
defaultPLAN / negative-dogwarning được chạy, cwd NEWoutput. Không --live-serial,
device discovery/capture, daemon/service/camera, actuator hoặcDBproduction.

PASS cần exit0, result.json `ARM64_NATIVE_TEST_PASS=true`, revisionGCC75_R2,
whole_posix_bridge_compile=PASS, các program/replaycounts đúng, post-testmanifest
integrityPASS, no sentinelDB/log/lock sideeffects. Gửi result.json +compile/testlogs,
compiler/dependencyversions và hashbinaries. Fail: giữ directory/errorlogs; không
skipWerror hoặc ghi đè R1. Lỗi trước tạooutput có thể chỉ có consoleerror.

NativePASS chỉ qualify **native build/file replay**, không tự qualify FastAPI/
Flutter trên Nano, OpenCV/TensorRT, liveprotocol/35gmechanics hoặc APPflashgate.

## Blocking gates còn lại
Ownercatdataset/enrollment thiếu; onlysynthetic-ownerpolicy, không trainedmodel.
CurrentESP32runningpartition, decodedsecurity/eFuse/antirollback, ECHO13/17/15/10,
powerisolation, RAM-lossACK và reviewedmaintenance/rollback route vẫn theo
`HARDWARE_PHYSICAL_BRINGUP_20261029/maintenance_readiness/`. Không tự approvegates.
R1ARM64PASS được giữ nguyên; nó không phải R2ARM64PASS.
