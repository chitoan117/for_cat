# Bản thảo nội dung có bằng chứng — forr_cat

**M2 — PRE-HARDWARE SOFTWARE CANDIDATE.** Đây là bản thảo phương pháp/thiết kế và kết quả kiểm thử phần mềm. Chưa có kết quả nguyên mẫu vật lý, dữ liệu mèo thật hoặc mô hình train. Những phần đó dùng đúng nhãn **[CHỜ KẾT QUẢ THỰC NGHIỆM]**.

## 1. Lý do chọn đề tài

Theo dõi lịch sử tiếp cận, ăn và uống có thể hỗ trợ người nuôi quan sát sinh hoạt của mèo. Camera cung cấp bằng chứng hành vi; cân có thể hỗ trợ ước lượng lượng thức ăn khi phép đo đã hiệu chuẩn. Một ý định cấp thức ăn từ giao diện hoặc AI không đủ để bảo đảm thao tác vật lý an toàn. Vì vậy đề tài kết hợp máy tính nhúng xử lý quan sát với MCU chịu trách nhiệm điều kiện an toàn tại chỗ. Báo cáo không suy ra bệnh, cảm xúc hoặc kết luận chắc chắn về sở thích từ một ảnh.

## 2. Mục tiêu và phạm vi

Mục tiêu cuối cùng là nhận diện mèo mục tiêu, theo dõi phiên ăn/uống, lưu lịch sử, hỗ trợ ý định cấp thức ăn/nước và nghiên cứu **BEHAVIORAL PREFERENCE TREND** từ nhiều phiên có evidence phù hợp. Phạm vi đã đạt ở M2 gồm nền tảng phần mềm, tooling, policy, driver foundations và kiểm thử host/compile. Việc hoạt động trên Nano, camera/MCU/cảm biến thật, cơ khí/chấp hành, dữ liệu/model và Web/App thực tế chưa được chứng minh.

## 3. Kiến trúc hệ thống

Kiến trúc hiện hành duy nhất: camera USB thông thường → Jetson Nano → USB serial → ESP32-S3 N16R8 ứng viên → cảm biến/UI và servo/bơm dự kiến. Web/App hiện có trao đổi REST với Jetson. Diagram và vai trò theo `REFERENCE_ARCHITECTURE.md` / `SYSTEM_BLOCK_DIAGRAM.md`. N16R8, pin và USB route là thông tin ứng viên chưa kiểm chứng, không phải cấu hình board đã đo.

Jetson quản lý camera/OpenCV, interface runtime AI, xác nhận phiên theo thời gian, fusion, SQLite và REST. ESP32-S3 quản lý input sensor, RTC/persistence và quyền an toàn chấp hành cuối cùng. Phân tách này tránh đưa quyền GPIO vật lý trực tiếp cho kết quả inference hoặc request mạng. Việc an toàn thực tế khi mất nguồn/crash vẫn cần thử nghiệm; phân tách thiết kế không tự chứng minh an toàn điện/cơ khí.

## 4. Camera và luồng quan sát

Camera là thiết bị USB thông thường; AI dự kiến chạy trên Jetson. Có abstraction mock/USB/file, budget xử lý và worker phải được khởi động rõ ràng. Replay/test video tổng hợp kiểm tra decoder/lifecycle, không phải evidence chất lượng camera tại bát. Frame format/crop/ROI và mốc thời gian phải được ghi rõ. Source file FPS là metadata decoder, không tự là tốc độ inference hoặc FPS Nano đo được.

**Lắp camera, chất lượng hình, FPS/dropouts trên Jetson:** [CHỜ KẾT QUẢ THỰC NGHIỆM]

## 5. REST API và lưu trữ

FastAPI cung cấp health/readiness/status, lịch sử, typed sessions và vòng đời request cấp thức ăn. SQLite giữ generic events, typed records và ledger request với schema, retention và xử lý lỗi. API defaults local/mocks; không tự chạy camera thật hoặc tự kích hoạt model. Frontend cũ ngoài repo; hợp đồng API không đồng nghĩa client đã tích hợp được.

Idempotency-Key giúp truy xuất lại trạng thái đã lưu mà không gửi lại ý định đã nhận chỉ vì client retry. REQUEST_RECEIVED/PENDING khác kết quả SUCCESS/REJECTED/ERROR. Thiết kế có giới hạn và write barriers; độ bền SD/NVS khi mất nguồn thật chưa được kiểm chứng.

**Môi trường Nano, persistence/power loss và frontend/network thực tế:** [CHỜ KẾT QUẢ THỰC NGHIỆM]

## 6. UART v1

Wire contract giữ nguyên: `A5 5A | VERSION:u8 | REQUEST_ID:u32 LE | COMMAND:u8 | LENGTH:u16 LE | PAYLOAD:0..256 | CRC16:u16 LE`. CRC-16/CCITT-FALSE bao phủ VERSION đến PAYLOAD; baud115200. Python/C++ dùng cùng7 golden vectors. Parser/link kiểm tra kích thước, CRC, ID và timeout. CRC chống sai dữ liệu truyền, không phải xác thực mật mã.

ACK chỉ xác nhận nhận frame. Kết quả thao tác phải dùng FEED_STATUS tương quan ID; GET_STATUS một byte không chứng minh sensor/actuator readiness. V1 không có telemetry sensor đầy đủ hoặc payload target grams; extension mới chỉ ở mức kế hoạch versioned. Không sửa wire để làm báo cáo đẹp hơn.

**USB link thật, RTT/unplug/replug giữa Jetson và ESP32-S3:** [CHỜ KẾT QUẢ THỰC NGHIỆM]

## 7. An toàn cấp thức ăn

Portable controller kiểm tra RTC, food availability, cân hợp lệ, servo readiness, target bounds, giới hạn ngày/cooldown và persistence trước desired-open. Có precheck lặp lại, write-ahead inspection latch, no-progress/total timeout và hoàn tất sau persistence. Reset không tự resume lượt cấp chưa rõ outcome. Đây là logic software; desired-open trong fixture không phải servo đã chuyển động.

Normal HW_SAFE từ chối physical execution; API SERIAL cũng chặn feed tại chỗ. Servo interface disabled, không PWM/angles/pulse widths. Cân/RTC lỗi phải chặn hoặc dừng ý định phụ thuộc nó. Điều kiện này đã được kiểm tra bằng host/fake I/O, chưa phải stop/jam/closure evidence thực tế.

**Độ chính xác dispense, đóng gate, jam/current, outcome vật lý:** [CHỜ KẾT QUẢ THỰC NGHIỆM]

## 8. An toàn nước

Water policy có stable-sample/hysteresis, yêu cầu tiến triển, maximum-runtime và sensor/pump-fault OFF. Diagnostic dùng calibrated optional level và **hypothetical** pump readiness để báo would_request_pump; physical_pump_on luôn false. Pump interface không switching GPIO. Percentage hình học không phải thể tích nước uống. Pump bị kẹt ON vật lý cần thiết kế feedback/fail-safe riêng, không thể chứng minh bằng policy flag OFF.

**Đo mức nước, flow/current/stop/leak/dry-run/power-noise:** [CHỜ KẾT QUẢ THỰC NGHIỆM]

## 9. Kiến trúc cảm biến

Có HX711 raw/average/tare/calibration domain, DS3231 presence/read/explicit set/BCD/calendar/OSF, bounded ultrasonic core dùng cho food/water với geometry riêng, SSD1306 tối thiểu, button intent/debounce và active-buzzer patterns. Pin truyền qua cấu hình; mặc định chưa gán bị từ chối trước GPIO. Health/snapshot giữ optional value, timestamp/freshness và không nâng HEALTHY từ compile success.

Calibration record version/CRC riêng với safety counters, không factor/geometry giả định. Codec/fake I/O và adapter compile có evidence; accuracy, timing và NVS retention/interruption trên board thật chưa có. Sensor diagnostic ASCII không phải normal UART v1.

**Wiring/voltage/range/geometry/calibration và vận hành MCU thật:** [CHỜ KẾT QUẢ THỰC NGHIỆM]

## 10. Phương pháp dataset

Capture session explicit, dry-run mặc định, session ID và metadata/version/source hash, duration/frame/storage limits, không silent overwrite. Collection target không tự thành ground truth. Human labels có UNKNOWN/UNSURE/SKIP; multi-cat/occlusion phải được ghi rõ. Sampling temporal spacing, exact dedup và near warnings hạn chế frame gần giống.

Split theo session và source; kiểm tra exact/near duplicates qua split, integrity, class coverage, diversity, imbalance và usable rate. Dataset release lưu hash/version/counts/validation, không chỉ tên thư mục. Roboflow optional; local classification sidecar giữ session identity, metadata mất thì không vào final split. Không dùng final test để chọn threshold/early stopping.

**Corpus thật, số phiên/lớp, usable rate và label agreement:** [CHỜ KẾT QUẢ THỰC NGHIỆM]

## 11. Phương pháp AI và temporal behavior

Task decomposition: detector → crop/track → identity → behavior → temporal → session/sensor fusion → history/API. Interface/candidate/experiment/inactive registry/evaluation đã có; chưa có trainer/weights/executor được validate. UNKNOWN là abstention/ambiguity, không cưỡng ép thành owner. Multi-cat hiện xử lý bảo thủ; TrackLedger chỉ là boundary nhận ID từ caller, không phải tracker association đã triển khai.

Temporal engine xác nhận positive evidence qua nhiều frame, giới hạn dropout và kết thúc ở positive cuối; không kéo dài eating qua đoạn không thấy. Evaluation tách frame confusion/metrics và event start/end/overlap/false/missed. Identity báo riêng OTHER_CAT→OWNER_CAT và chiều false rejection. Threshold chọn trên validation với quy trình định trước, không chép accuracy/FPS của model tham khảo.

**Detector/identity/behavior accuracy, event errors, ONNX/TensorRT/Nano performance:** [CHỜ KẾT QUẢ THỰC NGHIỆM]

## 12. Fusion và phương pháp xu hướng thức ăn

Consumption chỉ có ý nghĩa khi before/after weights ổn định đã kiểm chứng, subject/feed association sạch và không có food-added/confounder làm sai phép trừ. Phiên ambiguous không được coi là clean preference data. Food trials ghi food ID/variant, portion, freshness, vị trí bát, time-of-day/time since feed và disturbance; không tự suy ra đói.

Trend là công thức heuristic configurable trên nhiều distinct sessions, báo consumption ratio, approach latency, duration, leftovers, repeat visits và lý do thiếu dữ liệu. Các weights/min-session/threshold mặc định chưa được khoa học/real-data validate; không báo statistical confidence nếu chưa tính. Drinking report giữ volume null và daily report không đưa chẩn đoán sức khỏe.

**Consumption error và BEHAVIORAL PREFERENCE TREND thật:** [CHỜ KẾT QUẢ THỰC NGHIỆM]

## 13. Bảo mật và chiến lược kiểm chứng

API local mặc định, explicit CORS không thay authentication, trusted-local model/data paths, schema/hash checks và inactive registration. Không upload dữ liệu/API keys, không endpoint raw GPIO hoặc public exposure. Auth/TLS/deployment review và privacy xử lý footage thật vẫn cần làm trước sử dụng tương ứng. Dependency consistency không phải vulnerability certification.

Tách UNIT/HOST INTEGRATION/SIMULATION/COMPILE/PHYSICAL BENCH/REAL DATA/FULL SYSTEM theo `VERIFICATION_VALIDATION_MATRIX.md`. Current quality baseline301 Python,3271 native,7/7 vectors,18/18 guards,11/11 builds là kết quả software layers; static/generative/chaos/sparse-hourly soak không là hardware reliability. Không điền các số này vào bảng AI/hardware. FMEA ghi effect/detection/mitigation/evidence, không risk scores tự đặt. Rerun tại `PRE_HARDWARE_RELEASE_CANDIDATE.md` lấy từ log thật;217/1328 là checkpoint bàn giao trước đó.

## 14. Kết luận ở M2

Đã chuẩn bị software/tooling/driver foundations và tài liệu tái lập/bàn giao. M3/M4 chưa đạt; dataset/model/final demo chưa có. Không tăng tiến độ từ thêm tài liệu hoặc mock. Dừng phát triển pre-hardware; bước tiếp theo phải lấy evidence thực từ thiết bị/dữ liệu/training. Kết luận hiệu quả nguyên mẫu cuối cùng: **[CHỜ KẾT QUẢ THỰC NGHIỆM]**.
