# Windows build và source/guard analysis

## Môi trường thực tế và lỗi Jetson

JetsonUbuntu18.04/ARM64/systemPython3.6.9 gặpUnknownPackageErrorlinux_aarch64;
pioarduino55.03.311 tải được nhưng yêu cầuPython3.10–3.14. Kit build trênWindows,
không nâng systemPythonJetson, không hạ platform hoặc thay framework.

Build dùng executable hiện có `C:\Users\chito\.platformio\penv\Scripts\python.exe`.
Initialterminalinspection từng trảPython3.14.3/Core6.1.19; **actual finalbuild log**
ghi Python3.11.9, PlatformIO6.2.0.post1, esptool5.3.0, platform55.03.311,
Arduino3.3.11, frameworklibs5.5.5, Xtensa14.2.0+20260121. Không có pipinstall,
frameworkreplace hoặc OSupgrade do agent. Dùng version trong `build_result.json`
và full logs làm provenance của artifacts, kiểm version trước rebuild trênmáy khác.

```powershell
& "D:\for_cat\.venv\Scripts\python.exe" -B "D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029\tools\build_windows.py"
& "D:\for_cat\.venv\Scripts\python.exe" -B "D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029\tools\verify_offline.py"
```

Hai script không có targetupload/erase; không mởserial. Rebuild chỉ khi source hoặc
buildenvironment thay đổi. Môi trường riêng chưa cần tạo vì Windows đã buildPASS;
nếu thiếuvenv/toolchain, dừngBLOCKED_ENVIRONMENT và chuẩn bịvenv riêng, không sửa
môi trường hiện có hoặc fallback sang framework khác. Lỗi `pio pkg list` Unicode
trên console cũ không phải lỗi compiler; buildtool đặt UTF8 cho subprocess/logs.

## Authority và isolation

Upstream mới nhất trênWindows là `FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32`,
đã có HXgolden, inox binding, PIRwarm-up và isolatedbenches. Headerhash đối chiếu
acceptedRCv2; source remote `stage/firmware/esp32` do owner cung cấp chưa được
SSH/read hiện tại. `SOURCE_REFERENCE.json` giữ hashes và nêu rõ NOT_COMPARED_REMOTE.

Trong snapshot kit chỉ chọn explicit sourcefilters:
- `diag_four_ultrasonic`: `diagnostics.cpp`; MODE7/QUAD1/CURRENT1/HXinstalled1,
  SENSOR_BRINGUP1, S3NO_PSRAM1, normalactuators0, servodiagnostic0/pumpdiagnostic0.
- `diag_dog_buzzer`: `dog_buzzer_diagnostic.cpp`; khôngAIreceiver/normalmain.
- `diag_servo_bench`: `servo_bench.cpp`; physicalbenchpermission1 cục bộ, ordinary
  feeding vẫn0. GPIO6PWMoffboot, chưaconfigured/ARM thì khôngmove.
- `diag_pump_bench`: `pump_bench.cpp`; PHYSICAL_ENABLE0/OFF_LEVEL-1, khôngGPIO7write.

`main.cpp` chỉ chứa ordinaryentry khiMODE0 và khôngbench; không được compile vào
các image trên. `dispense_bench.cpp` nằm trong upstreamreference nhưng không có
environment được build/flash trong kit; không closed-loop/automaticfood dispense.
Boardguards chốngACTUATOR_OUTPUTS1, BOARD_HAS_PSRAM, mixedbench/sensor/nativeCDC và
unknownpumpOFFlevel. `include/board_config.h` là path thật (không phải m4/board_config.h).

Kit-only changes: firmwareID/status, explicitNO_ECHO/OUT_OF_RANGE reason without
changing driver validity/sequence; sensorstation rejecttare/cal/save/buzzercommands;
buzzerACTIVE_LOW ack+max3sequences/boot+stop; servo immediatePWMstop latchedFAULT;
pumpstatus identity. CoreHXreader, ultrasonic scheduler/pins/timeout, servo pulse
envelope và pump off/pulse policy không bị thay để vượt build.

## Boot/runtime limits

Sensor:4echo OFFboot; ordered scheduler, quiet80ms (RAMchoice60/80/100), mỗi channel
ít nhất500ms, echo timeout30ms; acquisition tránh serialwork khi đang bắt echo.
`NO_ECHO`/`OUT_OF_RANGE` là measurement_state bổ sung, distance null khi invalid;
legacy mode/state giữ tương thích. PIR60swarm-up/100msdebounce, rawmotionlegacy
khác qualifiedmotion_stable. RTCpins -1 trongquad; không pollDS1302.

Buzzer: GPIO2 HIGH trướcOUTPUT, khôngsoundboot, driverack bắt buộc,2ON200ms/gap200,
60scooldown, max3tests/boot, STOPHIGH. Không dùng genericACTIVE_HIGH branch.
Servo:1000–2000us electricalbound, **testspan≤100us**, configureonce/boot,
max3arms/moves, armexpiry2s, movementhold250ms, closereturnhold350ms,
harddeadline3s. ARM có thể chuyển động; STOPPWMoff latchedFAULT, khôngauto-rearm.
Pumpactive source (chưa shipbinary):20–500ms pulse, max3/boot,1scooldown,
2sarmexpiry, autostop. OFFbias trướcsetup phải đo ngoài firmware.

Board manifest title gốc là DevKitC-1-N8/8MB; 16MB là explicit upload/partition
override như authority, được kiểm bằng imageheader/SCons/table. Đây không phải
xác nhận silkscreen exactmodule. Không BOARD_HAS_PSRAM; không bật PSRAM chưa xác minh.

## Future pump image — không chọn cực tính bằng phần mềm

Chỉ sau khi owner đo module với tải an toàn/ngắt motor, bootOFFbias và ghi
`USER_OBSERVED` thật, có thể build trênWindows:

```powershell
# Thay OFF_LEVEL bằng số0 hoặc1 đã ĐO; không chạy với placeholder.
& "D:\for_cat\.venv\Scripts\python.exe" -B "D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029\tools\build_windows.py" --pump-off-level OFF_LEVEL --observation "OWNER_REVIEWED_FILE.json"
```

Không có evidence thì script refuse. OFF0→activeHIGHvariant; OFF1→activeLOWvariant.
Đây là lựa chọn dựa trên owner measurement, không proof từ tênF5305S. Conditional
artifacts/report tách khỏi4baselineimages. Không build activepump trong phiên này;
hostfakes test cả2polarity không biến chúng thành polarity đã nghiệmthu.
