# CAT APPROACH / DOG BUZZER — ROI offline handoff 2026-10-28

## Trạng thái hiện tại

**ROI_OFFLINE_SOFTWARE_READY: YES** — source, core C++14, fake-clock tests và công cụ hiệu chỉnh từ ảnh đã hoàn tất trên Windows.

- Mặc định **FULL_FRAME**: không có ROI/chưa hiệu chỉnh ROI vẫn nhận diện toàn khung. Không coi FULL_FRAME là bằng chứng vật thể ở khay.
- **ROI_ENABLED**: thiếu/sai tọa độ, chưa review/calibrate, sai camera binding hoặc thiếu bbox → BLOCK quyết định phụ thuộc ROI.
- HC-SR04/temporal/cooldown/arbiter vẫn bắt buộc. AUTO_CAT chỉ **DRY_RUN/BLOCK**; target35g; servo/pump **LOCKED**, HX711 **PHYSICAL_VALIDATION_PENDING**.
- Trong phần việc ROI offline này: không SSH, không camera/webcam, không serial/ESP32, không flash, không train/download model, không sửa frontend WEB_FINAL và không chạy lại bộ test cũ.

## Góc camera cố định do owner cung cấp — ROI đề xuất từ ảnh

Owner xác nhận ảnh đính kèm là góc camera sẽ giữ cố định. Ảnh hiển thị1920×1080,
góc thấp gần ngang mặt sàn; bát inox ở tiền cảnh bên dưới, bị cắt bởi mép dưới
và mép trái ảnh. Chai ở giữa, bút bên phải, chân bàn/ghế phía sau và dây bên phải
là nền/đồ vật; ảnh không có CAT/DOG và không có bbox detector.

- Phần bát **nhìn thấy** ước lượng khoảngx=0..0.64,y=.76..1.00. Đây không phải
  toàn bộ bát và không phải mask/pixel segmentation. Không thể suy ra khoảng cách
 20cm từ chai/bút/bát nếu không có calibration hình học; HC-SR04 vẫn đo khoảng cách.
- Vì detector cho **bbox cả con vật**, rectangle chỉ bó sát vành bát sẽ thường
  loại nhầm con vật ở gần: phần thân/tâm bbox có thể nằm phía trên vành. Dùng vùng
  tương tác rộng hơn trước khay làm **candidate** cho bộ lọc hiện có:
  **x1=.02,y1=.40,x2=.75,y2=1.00**, tương đương(38.4,432)→(1440,1080) trên ảnh1920×1080.
- Đây là tọa độ khởi đầu **ước lượng bằng quan sát ảnh**, không phải vùng đã xác
  nhận bằng chuyển động/bbox con vật. Vùng có thể chứa chai/nền; ROI không biến
  chúng thành CAT/DOG, quyết định vẫn phải xuất phát từ detector, temporal và HC1.
- File mới: `FULL_HARDWARE_INTEGRATION_20261027/payload/config/food_roi.fixed_camera.candidate.json`.
  Có tọa độ nhưng vẫn `mode=FULL_FRAME`, `enabled=false`, `calibrated=false`,
  review ID rỗng. Như vậy nhận diện hiện tại được giữ và bật ROI_ENABLED khi chưa
  review sẽ BLOCK, không giả lập kết quả hiệu chỉnh.
- Sơ đồ mới: `CAT_APPROACH_DOG_BUZZER_20261028/fixed_camera_roi_proposal.svg`.
  **Đây là sơ đồ vẽ lại vị trí ước lượng, không phải overlay xử lý trực tiếp ảnh gốc.**
  Ảnh gốc chỉ có trong conversation attachment, chưa được lưu/hash bằng tool.
- Giữ nguyên quy tắc tâm bbox trong rectangle và≥50% bbox giao ROI. Không đổi
  sang suy đoán đầu/mõm/chân từ bbox cả con vật. Nếu chỉ đầu lọt khung, detector
  có thể không nhận ra hoặc bbox lớn bị loại; ảnh trống này chưa giải quyết được.
- Mới chạy riêng test candidate C++14: **35 assertions PASS**; kiểm tra load config,
  FULL_FRAME/ROI_ENABLED chưa review, synthetic CAT/DOG/nền/mép vùng,1920×1080,
 1280×720,640×360 và trường hợp bbox lớn bị loại. Không chạy lại các test đã PASS.
  Log/manifest: `fixed_camera_roi_test.log`, `fixed_camera_roi_result.json`;
  helper: `test_fixed_camera_roi.cpp`, `verify_fixed_camera_roi.py` trong bundle hiện có.
- Source thuật toán ROI, firmware, HC/buzzer/HX711 và arbiter không thay đổi ở bước
  phân tích ảnh này. Chưa có CAMERA_PHYSICAL_PASS hoặc bbox động vật thật được kiểm tra.

Khi có ảnh thật chứa CAT/DOG ở các vị trí gần/bên cạnh khay, có thể đối chiếu bbox
với vùng candidate rồi chốt review ID/ROI_ENABLED qua tool ảnh hiện có. Không cần
đổi góc camera ngay hoặc kết nối thiết bị để hoàn tất phần đề xuất offline này.

## Files changed — phần ROI

Source authority: `D:\for_cat\FULL_HARDWARE_INTEGRATION_20261027\payload\`, không dùng checkout `D:\for_cat\jetson` cũ.

Trong `payload/jetson/device/`:
- **Thêm** `food_roi.h`: cấu hình JSON bounded/strict, mode, hình học ROI, chuẩn hóa pixel và inverse letterbox, policy cho metadata có/không có bbox.
- **Sửa** `roi_species.h`: optional ROI, lọc bbox, DOG priority, input INVALID fail-closed.
- **Sửa** `roi_ai_source.cpp`: mặc định FULL_FRAME, dùng bbox thật từ detector C++ hiện có, phát bbox/coordinate-space/mode/eligibility; không tạo tọa độ khi không có bbox.
- **Sửa** `approach_fusion.h`: scope FULL_FRAME/ROI_ENABLED dùng lại temporal và HC event hiện hành.
- **Sửa** `esp32_bridge.cpp`: `--roi-mode`, đọc legacy/global đúng scope, chặn mode mismatch; log `tray_membership_proven=false` cho FULL_FRAME.
- **Sửa** `roi_review.cpp`: thêm `--image FILE NEW_CONFIG_JSON` cho hiệu chỉnh từ ảnh lưu sẵn; camera chỉ là lựa chọn tương lai khi người dùng gọi rõ ràng.

Khác:
- `payload/config/food_roi.example.json`: default FULL_FRAME/disabled, tọa độ null.
- `guard_tuning/esp32/test/approach_dog_cases.cpp`: fixture cũ được ghi rõ ROI_ENABLED để giữ ý nghĩa test sau khi default đổi; **không chạy lại**.
- `CAT_APPROACH_DOG_BUZZER_20261028/test_bridge_pty.py`, `verify_jetson.py`: cập nhật schema/header cho lần rebuild Jetson tương lai; **không chạy** trong phần offline này.
- **Thêm** trong bundle hiện có: `test_roi_offline.cpp`, `verify_roi_offline.py`, `roi_calibrate_image.html`, `roi_calibration_math.js`, `test_roi_calibration.js`.

Artifacts mới trong `D:\for_cat\CAT_APPROACH_DOG_BUZZER_20261028\`:
`roi_offline_result.json`, compile/test logs, `native/test_roi_offline.exe`, `roi_synthetic_cases.jsonl`, **`roi_synthetic_preview.svg`**. Đây là test Windows và mô phỏng, không phải firmware hay dữ liệu camera thật.

## Cấu hình và thuật toán

### FULL_FRAME / ROI_ENABLED

| Chế độ | Hành vi |
|---|---|
| FULL_FRAME — mặc định | Giữ CAT/DOG/NONE toàn ảnh. Tọa độ/metadata hiệu chỉnh ROI chưa có hoặc không dùng không chặn nhận diện. Không trả IN_ROI hay tự gán vị trí khay. |
| ROI_ENABLED | Cần hình chữ nhật hợp lệ, `calibrated=true`, `review_id` không rỗng và bbox hợp lệ trong hệ tọa độ camera gốc. Ngoài ROI không sinh AUTO_CAT/DOG_WARNING. |

- Tọa độ: `0 ≤ x1 < x2 ≤ 1`, `0 ≤ y1 < y2 ≤ 1`. Không tự điền ROI khi thiếu.
- Trong file: `mode` chọn chế độ; `enabled` nếu có là bật/tắt rõ ràng và được ưu tiên. CLI `--roi-mode FULL_FRAME|ROI_ENABLED` là override tường minh. Tool xuất hai trường nhất quán.
- File không có/rỗng hoặc `{}` → FULL_FRAME; yêu cầu tường minh ROI_ENABLED với file rỗng/thiếu → BLOCK. JSON hỏng, trùng key, sai mode/bool bật-tắt, quá4096 bytes bị từ chối; không silently đổi ROI_ENABLED lỗi sang FULL_FRAME.
- Khung hình thực/bbox sai, NaN/Infinity, bbox rỗng/đảo chiều/ngoài biên → INVALID. Một bbox CAT/DOG không hợp lệ làm quyết định scene fail-closed, tránh bỏ qua DOG lỗi rồi cho CAT ăn.
- Quy tắc **IN_ROI**: tâm bbox nằm **bên trong** ROI và diện tích giao chiếm **ít nhất50% diện tích bbox**. Chạm mép/giao rất nhỏ hoặc bbox lớn bao quanh khay nhưng giao ít đều không đủ. Đây là ngưỡng hình học bảo thủ, chưa phải đánh giá độ chính xác camera thực.
- CAT+DOG hợp lệ trong vùng đang xét: DOG priority; không AUTO_CAT. NONE/offline/stale/không đáng tin: không feed, không beep.

### Đúng hệ tọa độ

`geometry_validation::Detector::infer()` dùng preprocessing/postprocess C++ hiện hành: bỏ pad letterbox, chia scale, clip/truncate về pixel ảnh gốc rồi chuẩn hóa. ROI nhận trực tiếp bbox **NORMALIZED_ORIGINAL**; không inverse-letterbox lần hai.

Core có adapter có tên rõ cho original-pixel và raw-network-pixel bbox. Adapter letterbox dùng float scale, kích thước resize làm tròn, pad nguyên, clip/truncate như decoder hiện hành; bbox network sai biên/resize rỗng bị INVALID. Không suy đoán320x320 là kích thước camera.

Producer bổ sung danh sách bbox thật vào cache, coordinate-space và kích thước frame. Bản ghi chỉ có nhãn legacy được giữ cho FULL_FRAME, ghi nhận bbox không có; **ROI_ENABLED từ chối**. Danh sách debug tối đa8 bbox, có cờ truncation; quyết định scene vẫn xét tất cả detections.

## Rào chắn giữ nguyên

- HC1 GPIO12/13: ENTER20cm, RELEASE>30cm; valid5–20cm;3 mẫu liên tiếp/1500ms; far liên tục2000ms mới arm/re-arm. Một state machine dùng chung CAT/DOG; boot gần không tạo event.
- MH-FMD GPIO2, **3.3V ACTIVE_LOW**: HIGH OFF,2 tiếng×200ms, gap200ms, cooldown60000ms. Không thay firmware/state machine này trong phần ROI.
- Temporal hiện hành, AI timestamp/freshness, cùng cửa sổ event, chống trùng và transport session giữ nguyên. Producer/bridge chọn mode khác nhau sẽ BLOCK, không downgrade.
- AUTO_CAT qua **FeedArbiter hiện có**,35g, cooldown tối thiểu2h. Thiếu HX711 physical authority vẫn DRY_RUN_BLOCKED; không có mở servo/pump.
- Hash kiểm tra trong `roi_offline_result.json` xác nhận HX711 reference port/calibration, ultrasonic scheduler, warning protocol, approach/buzzer policy, temporal policy, FeedArbiter và Scheduled Worker không bị sửa bởi phần ROI.

## Test thực sự đã chạy — Windows, offline

| Kiểm tra mới | Kết quả |
|---|---|
| Core C++14 native, `-Wall -Wextra -Wpedantic -Werror` | **PASS**, không warning |
| ROI/fake-clock suite | **27 cases,663 assertions PASS** |
| Math/export của công cụ hiệu chỉnh ảnh, Node | **12 cases PASS** |
| JSON xuất từ tool JS → parser C++ thật | **PASS** |
| Synthetic visualization | **8 scenes SVG**, dữ liệu từ kết quả C++ |

Bao gồm đầy đủ13 tình huống yêu cầu: CAT/DOG trong/ngoài ROI, mixed scene, chạm mép; FULL_FRAME thiếu ROI; ROI_ENABLED thiếu ROI; dữ liệu lỗi; letterbox640×480/1280×720/480×640/641×479 và nhiều độ phân giải; stale/offline; AUTO_CAT qua arbiter bị block; DOG_WARNING với mock GPIO2. Bổ sung bật/tắt, timestamp tương lai, camera binding, thiếu bbox, mặc định mode, malformed/duplicate JSON và500 input xấu bounded không crash.

Chạy lại **chỉ phần ROI mới khi cần**:

```powershell
& "D:\for_cat\.venv\Scripts\python.exe" "D:\for_cat\CAT_APPROACH_DOG_BUZZER_20261028\verify_roi_offline.py"
```

## Hiệu chỉnh sau này bằng một ảnh webcam thật

1. Mở `D:\for_cat\CAT_APPROACH_DOG_BUZZER_20261028\roi_calibrate_image.html` trong trình duyệt Windows. Tool độc lập, chạy từ file, không gọi webcam/network và không thuộc frontend sản phẩm.
2. Chọn **ảnh thật nguyên khung**, đúng vị trí/hướng/crop camera dự định dùng. Kéo rectangle quanh vùng khay ăn, xem tọa độ chuẩn hóa.
3. Chọn ROI_ENABLED, nhập review ID, xác nhận checkbox đã review rồi tải `food_roi.reviewed.json`. Ảnh mô phỏng không phải dữ liệu hiệu chỉnh camera thực.
4. Khi triển khai lại sau này, dùng config này với producer và chọn cùng mode ở bridge. Muốn tắt ROI, đặt `enabled=false`/FULL_FRAME cho hai phía; không cần train hoặc đổi model.
5. Ảnh đổi độ phân giải được xử lý bằng tọa độ chuẩn hóa; nếu đổi góc nhìn, crop hoặc vị trí khay/camera thì phải review lại ảnh. Chưa có ảnh thật vẫn dùng FULL_FRAME.

## Giới hạn xác minh

- Kết quả firmware/bridge trước phần optional ROI vẫn lưu tại `CAT_APPROACH_DOG_BUZZER_20261028/result.json`, `jetson_result.json` và build logs. Chúng là bằng chứng lịch sử, không được gộp thành kết quả rebuild cho source ROI mới.
- Chưa compile/rebuild toàn bộ executable ARM/Linux chứa CUDA/TensorRT/OpenCV hoặc chạy bridge POSIX/PTY trong phần việc offline này. Các bản ELF đã build ở giai đoạn trước là **historical, chưa chứa optional ROI mới**; không coi chúng là build mới.
- Source adapter producer/bridge đã cập nhật; cần rebuild trên môi trường Jetson/SDK tương ứng khi có lại môi trường đó. Các test Windows xác minh core/config/geometry/fusion được chia sẻ, không thay thế xác minh linker/runtime SDK.
- Chưa xác minh ROI trên ảnh webcam thật, độ chính xác detector thực, âm thanh/mức điện áp buzzer hoặc độ trễ/vị trí vật thể tại khay. Chưa có CAMERA_PHYSICAL_PASS/HX711_PHYSICAL_PASS.
- Không có thao tác phần cứng cần người dùng thực hiện ngay. Phần ROI offline kết thúc tại đây.

**ROI_OFFLINE_SOFTWARE_READY: YES**
