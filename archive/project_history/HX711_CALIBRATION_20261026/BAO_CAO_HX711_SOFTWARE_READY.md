# HX711 — SOFTWARE READY, chờ TEST 0 g thật

## Trạng thái milestone

- **SOFTWARE READY**: đã triển khai quy trình thu nhiều mẫu, fit nhiều điểm,
  kiểm tra độc lập, lưu hệ số và hiển thị gram hợp lệ trong SystemState/Flutter.
- **PHYSICAL CALIBRATION IN PROGRESS — AWAITING ZERO**: phiên đã chuẩn bị,
  nhưng người dùng chưa đặt tải và chưa chạy TEST0.
- **PHYSICAL PASS: chưa được cấp.**0 điểm quả cân thật,0 model active.
- **NOT TESTED**:0/5/10/20/30/35g thật, vòng kiểm chứng và persistence sau restart.
- **BLOCKED**: servo/pump, AUTO và cấp thức ăn vật lý; actual_dispensed_grams=null.

Phiên: hxcal_91ca4d57d8c24e5d92a3f063a8b01494.
Evidence: /home/toan/for_cat/evidence/hx711_calibration_20261026T041547966931Z/.

## Audit: dữ liệu đang nằm ở đâu?

Firmware tham chiếu của app đã flash trước đây đọc raw signed24-bit, channelA/
gain128, DOUT4/SCK5. Có lệnh lấy trung bình1..64 sample, tare, cal một điểm,
validate và save/load. Công thức firmware là(raw-offset)*grams_per_count.

NVS dùng namespace m4-calibration, key sensors-v2, record39byte phiên bản1 có
CRC16, chứa tare/factor HX và cả geometry cảm biến khác. Runtime trước đợt này
báo firmware_calibrated=false. Offset/factor MCU không được telemetry chuẩn
truyền ra, nên được ghi UNKNOWN/null, không suy đoán0. Bridge/SystemState trước
đó chủ động giữ gramnull/DEFERRED. Không đọc lại hoặc ghi NVS trong đợt này.

## Có cần flash không?

**Không cần flash cho cách triển khai milestone này.** Calibration thực hiện
trên Jetson từ raw thật mà C++ bridge hiện có cung cấp. Không gửi lệnh serial
tare/cal/save; không đổi firmware, pin, AI model/engine hoặc controller.

Calibration lưu trong cùng events.db qua3 bảng tách biệt:
- hx711_calibration_sessions
- hx711_calibration_points
- hx711_calibration_active

Model/point có SHA256 và binding USB/HX pins/mode. Đổi Meal Plan/config không
xóa hệ số. Bắt đầu phiên tare/calibration mới sẽ làm model cũ không còn active.
Gram host không tự biến thành quyền điều khiển cơ cấu hoặc calibration firmware;
C++ Feed Arbiter vẫn giữ chặn vật lý như trước.

## Offset/factor được tính thế nào?

Mỗi điểm chờ5giây rồi thu30giây, yêu cầu ít nhất25 báo cáo raw độc lập trên
span ít nhất25giây. Không dùng một sample tức thời. Loại outlier chỉ ở mức nhỏ,
có lưu nguyên mẫu; bất thường liên tiếp hoặc spread/drift cao bị chặn.

Tare/offset là trung bình robust của điểm0g. Với r0 là offset, ri là mean raw
ở mi gram:

```text
counts_per_gram = Σ[mi*(ri-r0)] / Σ[mi²]
grams_per_count = 1 / counts_per_gram
grams = (filtered_raw - r0) * grams_per_count
```

Hệ số có thể âm nếu raw giảm khi tăng tải; gram vẫn phải tăng đúng chiều tải.
Fit dùng0/5/10/20/30/35g. Candidate chưa tạo gram chuẩn trên app. Cần vòng NEW
0/5/10/20/30/35/0 để xác minh độc lập, rồi mới activate. Giá trị candidate dùng
tên candidate_grams để phân biệt; actual_dispensed_grams vẫnnull.

## Tiêu chí bench đề xuất

Sai số theo cân danh định: +/-max(0,1g;1% reference).
Tương ứng0g±0,1;5g±0,1;10g±0,1;20g±0,2;30g±0,3;35g±0,35g.
Spread cửa sổ<=0,2g, sigma<=0,05g, drift hai nửa cửa sổ<=0,1g.
Không tự nới tolerance để đạt PASS. Chưa có thông số capacity/certificate của
load cell/quả cân; nếu mức nhỏ không đạt thì báo hạn chế/BLOCKED. Đây là kiểm
chứng bench theo reference người dùng, chưa là chứng nhận metrology.

## API/UI

- /api/status và WS hiện có: weight.raw_counts, grams, calibration_state,
  stable/stability_state, offset/factor, cửa sổ mẫu, spread/stddev, age.
- GET /api/hx711/status: hx711.raw/raw_counts và cùng metadata đo.
- GET /api/hx711/calibration: phiên, criteria, điểm đã thu và model active.

Chỉ có API đọc; các thao tác calibration do CLI local rõ ràng. Trước khi valid,
gramnull. Live gram dùng10 báo cáo khác nhau/span>=8s, không dùng một sample;
missing/stale/binding sai/checksum sai/outside range sẽ đểgramnull. UI hiện
STABLE/UNSTABLE và metadata; dữ liệu sensor thật không bị thay bằng mock.

## Kiểm tra persistence sau này

Sau khi fit+validation thật đạt và activate, model ở trạng thái
CALIBRATED_PENDING_PERSISTENCE. Ghi ID/offset/factor, người dùng reset ESP32
hoặc reboot Jetson, rồi đo NEW0/35/0 ở phase persistence. Công cụ kiểm tra
host/MCU restart xảy ra SAU activation, các điểm vẫn đạt và hệ số không thay.
Lệnh finish chỉ nhận PHYSICAL_PASS sau các bằng chứng đó và xác nhận của người
dùng. API restart là phép thử reload hữu ích, chưa thay cho gate restart này.
Hiện các phép thử persistence thật đều NOT TESTED.

## Regression

- Backend đầy đủ:428 PASS, gồm29 case calibration và toàn bộ worker tests.
- M4/HX C++ UBSan:3351 assertions PASS với I/O giả lập.
- Fake dispense:9 nhóm/99 assertions và9 kiểm tra35g PASS, không là thử cơ cấu.
- pip check / diff check PASS.
- Flutter analyze sạch,34 tests PASS, build REAL release PASS.
- API/Chromium thật: raw hiện được, gram/tare/factornull,0 điểm vật lý,
  worker vẫn RUNNING, không POST điều khiển.

## File thay đổi

Backend mới: app/hx711_calibration.py, app/hx711_view.py,
app/api/hx711_routes.py, tools/hx711_calibration.py,
tests/test_hx711_calibration.py (đều dưới jetson/).
Sửa jetson/app/main.py và system_state.py để gắn measurement view.

Flutter: lib/feeder_state.dart, lib/main.dart, test/hx711_state_test.dart;
snapshot ở frontend/feeder_demo cùng thay đổi. Tài liệu/config:
docs/HX711_HOST_CALIBRATION.md, docs/CURRENT_PROJECT_STATE.md,
docs/FLUTTER_FRONTEND.md, config/hardware_current.json;
drop-in40-flutter-real.conf chọn artifact hx711_calibration_20261026_r1.

Firmware, C++ controller/bridge, AI model/engine và36-file staged index giữ nguyên.

## DỪNG TẠI ĐÂY: người dùng làm TEST 0 g

Giữ khay/cơ khí lắp bình thường làm nền tare, bỏ toàn bộ quả cân/thức ăn khỏi
khay; không chạm tay, kéo dây hay rung bàn. Chỉ chạy lệnh này trên Jetson:

```sh
/home/toan/for_cat/.venv/jetson-integration/bin/python /home/toan/for_cat/jetson/tools/hx711_calibration.py capture --session hxcal_91ca4d57d8c24e5d92a3f063a8b01494 --phase fit --mass-g 0
```

Chờ khoảng35giây, gửi toàn bộ JSON. Kết quả lúc này vẫngrams=null vì chưa có
scale hợp lệ; raw window/tare_candidate_counts là dữ liệu cần xem trước.
Chưa đặt5g hoặc chạyfit/activate. Quy trình đầy đủ các bước sau đã lưu trong
docs/HX711_HOST_CALIBRATION.md và sẽ được hướng dẫn từng bước sau TEST0 thật.
