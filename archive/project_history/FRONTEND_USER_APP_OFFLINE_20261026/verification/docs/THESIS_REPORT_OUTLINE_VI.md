# Dàn ý báo cáo luận văn — forr_cat

Nguồn hiện hành: `CURRENT_PROJECT_STATE.md`, `REFERENCE_ARCHITECTURE.md`, `PRE_HARDWARE_FINAL_BASELINE.md`. M2; chỉ có bằng chứng host/simulation/compile. Trạng thái bên dưới là mức sẵn sàng viết, không phải công nhận hệ thống vật lý hoàn thành.

| Chương / mục | Nội dung và nguồn | Trạng thái |
| --- | --- | --- |
| CHƯƠNG1 — Tổng quan đề tài:1.1 | Bối cảnh, nhu cầu theo dõi ăn/uống; không chẩn đoán sức khỏe | READY TO WRITE NOW |
| 1.2 | Mục tiêu, phạm vi, đối tượng, giới hạn M2 | READY TO WRITE NOW |
| 1.3 | Phương pháp, đóng góp phần mềm, cấu trúc báo cáo | READY TO WRITE NOW |
| CHƯƠNG2 — Cơ sở lý thuyết:2.1 | Camera USB, xử lý ảnh, detector/crop/identity/behavior; bổ sung tài liệu học thuật đã kiểm chứng | READY TO WRITE NOW |
| 2.2 | Jetson/MCU, UART/REST/SQLite, thời gian monotonic/UTC | READY TO WRITE NOW |
| 2.3 | Dataset leakage, metrics, temporal events, confounders | READY TO WRITE NOW |
| CHƯƠNG3 — Phân tích và thiết kế:3.1 | FR/NFR/SAFE, traceability, use cases | READY TO WRITE NOW |
| 3.2 | Kiến trúc duy nhất, quyết định thiết kế, sequence diagrams | READY TO WRITE NOW |
| 3.3 | Failure modes và chiến lược xác minh/kiểm chứng | READY TO WRITE NOW |
| CHƯƠNG4 — Thiết kế phần cứng:4.1 | BOM ứng viên, vai trò phần cứng, bảng pin chưa gán | READY TO WRITE NOW (thiết kế dự kiến) |
| 4.2 | Board/pin/nguồn/wiring thực tế, ảnh lắp đặt, cơ khí | WAITING FOR HARDWARE |
| 4.3 | Hiệu chuẩn cân/siêu âm/RTC, servo/bơm, reset/power | WAITING FOR HARDWARE |
| CHƯƠNG5 — Thiết kế phần mềm:5.1 | FastAPI/config/service, camera/replay, database/history | READY TO WRITE NOW |
| 5.2 | UART v1, feed lifecycle/ACK, MCU policies/persistence/diagnostics | READY TO WRITE NOW |
| 5.3 | Tool capture/data/evaluation/report, kiểm thử host, bảo mật | READY TO WRITE NOW |
| 5.4 | Deploy Nano, USB thật, frontend thật, phục hồi thực tế | WAITING FOR HARDWARE |
| CHƯƠNG6 — Xây dựng mô hình AI:6.1 | Phân rã task, label/annotation, protocol/splits, experiment config | READY TO WRITE NOW (phương pháp) |
| 6.2 | Corpus thật, phân bố/quality/diversity/usable rate | WAITING FOR DATASET |
| 6.3 | Huấn luyện, chọn checkpoint/threshold, ablation | WAITING FOR AI RESULTS |
| 6.4 | ONNX/TensorRT/Jetson correctness/performance/shadow | WAITING FOR HARDWARE + WAITING FOR AI RESULTS |
| CHƯƠNG7 — Thực nghiệm và đánh giá:7.1 |301 Python,3271 assertions,7 vectors,18 guards,11 builds; static/chaos: phạm vi host | READY TO WRITE NOW |
| 7.2 | Camera FPS,serial RTT,cân,siêu âm,feeding/water/power | WAITING FOR HARDWARE |
| 7.3 | Identity/FAR/FRR, behavior frame/event, multi-cat | WAITING FOR DATASET + WAITING FOR AI RESULTS |
| 7.4 | Consumption/preference, liên kết vision–sensor–Web/App | WAITING FOR HARDWARE + WAITING FOR DATASET + WAITING FOR AI RESULTS |
| CHƯƠNG8 — Kết luận và hướng phát triển:8.1 | Kết luận ở M2, phần làm được/chưa chứng minh | READY TO WRITE NOW |
| 8.2 | Kết luận hiệu quả nguyên mẫu cuối cùng | WAITING FOR HARDWARE + WAITING FOR AI RESULTS |
| 8.3 | Hướng tiếp theo theo evidence gates, không thêm mock | READY TO WRITE NOW |

Phụ lục: requirements/traceability, wire/API contract, cấu hình/phiên bản/hash, lệnh tái lập, bảng kết quả trống, evidence index. Không lấy FPS fixture hoặc confusion matrix kiểm thử làm kết quả mô hình. Tài liệu tham khảo thực sự phải chọn/đọc/trích dẫn; `REFERENCE_MAP.md` chỉ là điểm bắt đầu, không phải danh mục nghiên cứu đã thực nghiệm.
