# HX711 + chén inox — bàn giao phần mềm

> Acceptance addendum29/10/2026: owner đãchấpnhậnstaticphysicalmeasurement,
> latest35g=34.981g/error0.019g≈0.054%; `HX711_RETEST_REQUIRED=NO`.
> Xem `HARDWARE_PHYSICAL_BRINGUP_20261029/HX711_ACCEPTANCE.json` vànotes.
> FIT/VERIFY/38g workflowbên dưới làhistoricalrunbook, không làyêucầu lặplại
> initialweightseries hoặcoptimizeaccuracy hiện đãaccepted. Persistence và
> servo closed-loop35g vẫn NOT_VERIFIED; calibration-current sauflash làflowriêng.

Chốt phần mềm lúc 29/10/2026, tiếp nối evidence ngày 28/10; các báo cáo cũ được giữ nguyên.

`HX711_BOWL_OFFLINE_READY=YES`; `HX711_STATIC_MEASUREMENT_PHYSICAL_PASS=YES`;
`HX711_MEASUREMENT_ACCURACY_ACCEPTED=YES`; `HX711_RETEST_REQUIRED=NO`;
`HX711_CALIBRATION_PERSISTENCE=NOT_VERIFIED`; `HX711_CLOSED_LOOP_DISPENSE_35G=NOT_VERIFIED`.
Servo GPIO6 và pump GPIO7: **LOCKED**. Không flash, mở UART, tare hoặc chạy phần cứng trong phiên chuẩn bị.

## Source và bằng chứng

Source chính: `FULL_HARDWARE_INTEGRATION_20261027/payload` và `guard_tuning/esp32` bên trong cùng snapshot.

- `payload/jetson/app/bowl_mass.py`: baseline theo session/mount/calibration/boot/tare generation; kiểm tra cửa sổ ổn định, INVALID, drift, leftovers, overshoot, timeout và quan sát bữa ăn.
- `payload/jetson/app/hx711_view.py`: tùy chọn `HX711_CURRENT_MOUNT_ID` chặn active model cũ không có binding tương ứng; không migrate hoặc kích hoạt model.
- Firmware: `include/m4/inox_mount_binding.h`, `src/hx711_reference_diag.cpp`, profile `diag_hx711_inox` trong `platformio.ini`.
- Harness: `E2E_OFFLINE_DEMO_20261028/sim_support.h` có baseline chén tùy chọn, mặc định giữ behavior cũ.
- Tool/log/tests: `REAL_HARDWARE_BRINGUP_20261028/`.

Evidence `result.json`: 27 Python tests PASS; fake firmware inox 81 assertions PASS; reference compatibility 96 assertions PASS; E2E gross95→130 thêm35g, consumed30g LIKE, leftovers chặn mở fake servo. Hai profile `diag_hx711_inox` và `diag_hx711_reference` BUILD PASS. Không chạy lại full E2E cũ.

Firmware mới: `REAL_HARDWARE_BRINGUP_20261028/firmware/diag_hx711_inox/firmware.bin`, **384848 bytes**.
SHA256: `1d334986e1ca066f674bc70c8a1a13931f948d47c8511ac36403a333fdd02974`.
ELF, bootloader, partitions và hash đầy đủ ở cùng thư mục / `result.json`.

## Khối lượng và giới hạn tích hợp

`dispensed = gross_after - gross_before`; `consumed = meal_start - meal_end`.
Target là **35g thêm vào**, không phải tổng chén+food35g. Không trừ chén hai lần, không cấp bù khi cân giảm do ăn.
Gross là calibrated scale reading: nếu calibration lấy chén rỗng làm origin, gross không phải khối lượng vật lý tuyệt đối của chén. Tool ghi rõ bowl-anchored origin.

Module bowl policy đã kiểm thử nhưng chưa nối vào live feed runtime/API/servo. Locks vẫn giữ. Cửa sổ cân ổn định không tự chứng minh chén rỗng, không bị thay hoặc không có lực tiếp xúc cố định; cần owner xác nhận mounting.

## Buổi sáng: cân trước, actuator sau

1. **Thao tác đầu tiên:** owner kiểm tra common GND, mounting chén không chạm khung, và mức logic HX711 DOUT/SCK an toàn3.3V cho ESP32 khi module được cấp5V. Không suy luận nguồn5V đồng nghĩa logic an toàn. Servo/pump giữ không cấp quyền hoạt động.
2. Owner tự flash **app-only 0x10000** bằng binary trên, chỉ khi partition layout hiện tại đã xác nhận phù hợp. Không erase flash/NVS; không dùng profile servo demo. Xác nhận đúng cổng thay vì mặc định COM8.
3. Serial monitor115200: `mount INOX_20261029_A CONFIRM`, rồi `status`. Chọn mount ID mới nếu cơ khí đổi. **Không `t`, không `reference CONFIRM`**. Đóng monitor trước capture; một serial owner.
4. PowerShell, tạo session mới và capture bowl-only30s:

```powershell
$py = 'D:\for_cat\.venv\Scripts\python.exe'
$tool = 'D:\for_cat\REAL_HARDWARE_BRINGUP_20261028\bowl_log.py'
$session = 'D:\for_cat\REAL_HARDWARE_BRINGUP_20261028\physical_INOX_20261029_A'
& $py $tool new --directory $session --mount-id INOX_20261029_A
# Thay COMx bằng cổng vừa xác nhận; các lệnh capture chỉ gửi status.
& $py $tool capture --session $session --port COMx --phase BASELINE --reference-g 0 --seconds 30
```

5. **Fresh FIT** cùng boot: lần lượt capture `--phase FIT --reference-g 0`, sau đó5/10/20/35/38, mỗi điểm30s. Sau mỗi quả cân, nhấc quả cân ra nhưng giữ chén, capture `--phase FIT_RETURN --reference-g 0`. Đợi ổn định trước từng capture. Không tare giữa các điểm. Dùng cùng lệnh capture trên, thay phase/mass; không chạy vòng lặp tự động khi cần đặt quả cân thủ công.
6. `& $py $tool fit --session $session` tạo frozen `calibration_candidate.json`. Nếu lỗi, giữ evidence, tìm nguyên nhân; không refit để che sai số. Candidate không phải nghiệm thu.
7. Owner đọc **pair mới trong candidate**, mở monitor cùng boot và gửi `esp32-cal OFFSET_COUNTS COUNTS_PER_GRAM CONFIRM` với hai số thực tương ứng; không dùng pair mounting cũ. Đóng monitor.
8. **Independent VERIFY**: capture VERIFY0, VERIFY5/RETURN0, VERIFY10/RETURN0, VERIFY20/RETURN0, VERIFY35/RETURN0, VERIFY38/RETURN0;30s mỗi điểm. Không điều chỉnh pair giữa các bước.
9. Sau khi owner xem các VERIFY/RETURN đạt tiêu chí, owner tự gửi `cal-save INOX_20261029_A CONFIRM`. Đây là ghi NVS explicit của owner, không auto-authorize hardware. Reboot thật; khai báo lại `mount INOX_20261029_A CONFIRM`, xem `status`; capture REBOOT_EMPTY0, REBOOT_VERIFY35, REBOOT_RETURN0. Boot nonce phải đổi, NVS pair/binding phải khớp.
10. `& $py $tool analyze --session $session`. Gửi nguyên session gồm raw bin/log, capture JSON, candidate và analysis. Analyzer luôn `physical_pass=false`; review evidence riêng mới quyết định nghiệm thu.

Tiêu chí: nonzero sai số≤±0.70g, return/bowl-zero≤±0.20g; mỗi cửa sổ≥60 samples, span≥25s; range≤.20g, sigma≤.05g, drift≤.10g; không INVALID/gap/reboot giữa điểm. NVS persistence phải kiểm tra bằng boot mới. Mất calibration, mount khác, leftover hoặc chén xô lệch phải block. Các kết quả historical zero drift không được đổi thành PASS.

## Các bài vật lý tiếp theo (chưa thực hiện)

- HC1: boot tại15cm không có event; đưa40cm giữ≥2s rồi15cm cho3 mẫu hợp lệ≤1500ms, sau đó40cm≥2s. Giữ20–30cm không rearm; timeout không được coi0cm. Test4 kênh tuần tự, quiet80ms; JSN dùng khoảng cách ngoài blind zone theo module thực tế, không mặc định20cm hợp lệ.
- Buzzer-only binary historical `CAT_APPROACH_DOG_BUZZER_20261028/firmware/diag_dog_buzzer/firmware.bin`: owner chỉ chạy khi sẵn sàng giám sát, `test CONFIRM`; GPIO2 ACTIVE_LOW3.3V,2×200ms/gap200ms/cooldown60s. Không chạy lúc ngủ; không phải nghiệm thu hiện tại.
- Jetson: trước khi build/deploy, owner đọc `uname -m`, version Python integration venv, `pkg-config --modversion opencv4`, engine SHA256, `systemctl is-active` cho3 services, `fuser /dev/video0` và V4L2 inventory. Không mở detector/camera thứ hai. Updated ARM64/TensorRT runtime chưa được xác minh; xem overnight deployment runbook khi có.

**BLOCKED_PHYSICAL:** điện áp logic, fresh current-mount logs, return/reboot stability, servo closure/food flow/overshoot, sensor geometry và buzzer thật. Không có physical PASS từ bản chuẩn bị này.
