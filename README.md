# FOR_CAT — toàn bộ mã nguồn hệ thống cho mèo ăn/uống

Bản sao lưu đầy đủ được đánh dấu **backup-2026-11-12-complete** (bổ sung source cũ sau bản đầu backup-2026-11-12). Ngày **12/11/2026**: Jetson Nano chạy AI CAT/DOG + FastAPI, ESP32-S3 điều khiển phần cứng, Flutter Web giám sát/điều khiển. Giữ lịch sử Git cũ; thư mục `archive/` chứa các lần phát triển và bàn giao trước đây. `archive/original_laptop_source/` giữ thêm các source riêng/có khác biệt trong thư mục dự án cũ trên laptop.

| Thư mục | Nội dung |
|---|---|
| `esp32/` | Firmware hiện tại: `esp32.ino` + 7 header, bản offline R2 đã nạp ngày 11/11 |
| `jetson/app/` | Backend FastAPI, trạng thái, lịch ăn, hành vi, nước và mức dự trữ |
| `jetson/tools/` | UART bridge, AI tap và các công cụ trên Jetson |
| `jetson/ai/`, `ai/` | Nhận diện TensorRT C++ và mã chuẩn bị/huấn luyện/đánh giá AI |
| `frontend/` | Toàn bộ source Flutter, assets, kiểm thử, pubspec và dependency lock |
| `web_release/` | Bản Flutter REAL đã biên dịch, có tài nguyên cục bộ dùng offline |
| `models/` | Engine TensorRT đã export và các model tham chiếu có sẵn trên laptop |
| `firmware/offline_r2/` | File build firmware tương ứng, không chứa dump NVS/khóa bí mật |
| `hardware/proteus/` | File PCB `pet_feeder.pdsprj` |
| `hardware/uno_tests/` | Các sketch UNO tham chiếu servo, loadcell, pump |
| `systemd/`, `deploy/`, `scripts/` | Cấu hình dịch vụ, UART, build và triển khai |
| `archive/` | Source phiên bản cũ, các lần thử và scripts chẩn đoán; không nạp đè bản hiện tại |
| `BACKUP_MANIFEST.json` | SHA-256 từng tệp để kiểm tra bản sao |

## Trạng thái cần biết trước khi sử dụng

Đây là bản sao lưu source, **không phải tuyên bố toàn bộ phần cứng đã hoàn thiện**. Lần thử cuối ngày 11/11: OLED còn `KIEM TRA CUA`, giữ nút PCB chưa hiện `GIU5S XACNHAN`; lỗi manual/offline vẫn cần chẩn đoán. USB trên laptop lúc cuối chưa nhận COM, có thiết bị báo lỗi nhận dạng USB. Không tự bỏ khóa cửa hoặc lấy lại mốc cân khi chưa kiểm tra thực tế.

Jetson không SSH được tại thời điểm sao lưu. Backend được ghép từ bản export trực tiếp ngày 10/11 và các thay đổi đã triển khai có lưu trên laptop ngày 11/11. Bridge root là bản UART **a68b28…** đã triển khai; bản bulk-read **169456…** chỉ nằm trong archive, chưa triển khai. Firmware source root khớp bản R2 đã nạp/readback, SHA-256 **5e5f39e24cf46edb19998e06573779bb0d5f4345817da847be3a167d1c3ef2ec**.

Xem [hướng dẫn khôi phục](docs/KHOI_PHUC_TU_GITHUB.md), [trạng thái phần cứng](docs/TRANG_THAI_SAO_LUU_20261112.md) và tài liệu cũ trong `docs/`. Các mô tả cũ có thể dùng JSN/PIR/USB hoặc chân D2 cũ; đối chiếu bảng chân hiện tại trong tài liệu trạng thái.

## Truy cập cùng một ứng dụng

- Trên chính Jetson: `http://127.0.0.1:8000/app`, dùng được khi mất Wi-Fi nếu backend và nguồn còn hoạt động.
- Thiết bị cùng mạng LAN: `http://<IP-hiện-tại-của-Jetson>:8000/app`.
- Mạng ngoài/4G/5G: HTTPS Tailscale đã cấu hình; thiết bị phải có quyền trong tailnet và có Internet.

Không đưa lên repo: mật khẩu/token/SSH key, `.env` thật, dump flash/NVS, SQLite lịch sử vận hành, ảnh/video camera cá nhân, dataset ảnh và bộ cài/SDK/venv/cache. Đây không phải các tệp mã nguồn. Nếu cần giữ dữ liệu vận hành riêng, hãy sao lưu riêng trước khi xóa máy.

