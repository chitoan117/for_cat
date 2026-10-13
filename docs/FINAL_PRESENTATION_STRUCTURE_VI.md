# Cấu trúc trình bày cuối — 18 slide

Mỗi slide kết quả phải chỉ rõ HOST / SIMULATION / COMPILE hoặc REAL EVIDENCE. M2 không có kết quả AI/hardware cuối; dùng **[CHỜ KẾT QUẢ THỰC NGHIỆM]**, không bảng/ảnh giả.

| Slide | Nội dung nói/hiển thị | Evidence / trạng thái |
| --- | --- | --- |
| 1 | Tên đề tài, sinh viên/giảng viên, phạm vi M2 | Metadata người trình bày tự điền |
| 2 | Bài toán theo dõi ăn/uống và kiểm soát ý định an toàn | Không chẩn đoán sức khỏe |
| 3 | Mục tiêu/chức năng/giới hạn | Requirements |
| 4 | Kiến trúc duy nhất webcam→Jetson→USB→S3 | Block diagram hiện có |
| 5 | BOM/phần cứng ứng viên, pin chưa gán | Ảnh thật: chờ thực nghiệm |
| 6 | Jetson: camera/AI/session/API/SQLite | Software design; Nano chưa verified |
| 7 | ESP32-S3: sensors/local safety/persistence | Driver foundations; output disabled |
| 8 | REST/Web/App và UART/ACK/result | Contract, frontend ngoài repo |
| 9 | Dataset capture/session/labels/leakage/version | Tooling; corpus thật chưa có |
| 10 | AI detector→crop/track→identity→behavior | Candidate/interfaces, AI chưa train |
| 11 | Temporal eating/drinking và UNKNOWN/multi-cat | Host fixtures; không event mèo thật |
| 12 | Feeding policy/RTC/cân/limits/inspection | Desired flags khác chuyển động servo |
| 13 | Water hysteresis/fault/timeout/OFF | Pump thực tế chưa tested |
| 14 | Fusion/preference và confounders | Xu hướng hành vi, không “chắc chắn thích” |
| 15 | An toàn, security/FMEA/failure recovery | Gates/risks, không public exposure |
| 16 | Kiểm thử/tái lập:301/3271/7/18/11 + quality checks | Kết quả host cuối; AI/hardware bảng trống |
| 17 | Demo phần mềm hôm nay | SYNTHETIC / MOCK; theo recovery plan |
| 18 | Hạn chế, gates M3–M6, kết luận/freeze | Next evidence từ thiết bị/data/train thật |

Khi có real results, cập nhật slide tương ứng bằng bảng/log/hash thực, không xóa failure cases. Thời lượng chia theo buổi bảo vệ; không dùng synthetic metrics để lấp slide kết quả. Talk track ngắn hiện có: `PRESENTATION_TALK_TRACK_VI.md`.
