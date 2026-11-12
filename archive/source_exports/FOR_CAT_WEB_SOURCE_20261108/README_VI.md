# SOURCE WEB FOR CAT — bản bàn giao 08/11/2026

Gói này chứa frontend Flutter và backend Python của hệ thống đang sử dụng, cùng bản web release lấy trực tiếp từ Jetson. Source frontend lấy từ `D:/DA_KT_NC/feeder_demo`; backend lấy từ `/home/toan/for_cat/jetson`. Các file ứng dụng gốc không bị sửa khi đóng gói.

## Mở phần nào để làm báo cáo?

| Thư mục / tệp | Nội dung |
|---|---|
| `frontend/lib/` | Toàn bộ mã Dart giao diện và kết nối API |
| `frontend/web/`, `frontend/assets/` | Trang khởi động, biểu tượng và font |
| `frontend/test/` | Kiểm thử frontend |
| `frontend/pubspec.yaml`, `pubspec.lock` | Khai báo và khóa phiên bản thư viện |
| `backend/jetson/app/` | FastAPI, dữ liệu trạng thái, SQLite, lịch ăn và API |
| `backend/jetson/tools/fc_live_bridge.py` | Giao tiếp UART ESP32 ↔ SQLite ↔ AI; bản đã có heartbeat dự phòng |
| `backend/jetson/tools/fc_ai_tap.py` | Đọc kết quả nhận diện TensorRT vào SQLite |
| `backend/jetson/tests/` | Kiểm thử backend |
| `web_release/` | Bản web đã biên dịch đang được Jetson phục vụ |
| `docs/KIEN_TRUC_VA_BAO_CAO.md` | Kiến trúc, ánh xạ chức năng và lưu ý khi viết báo cáo |
| `docs/API_REFERENCE.md`, `openapi.json` | Bảng API và hợp đồng API xuất từ máy thật |
| `integration/esp32/` | Source firmware hiện tại để tham khảo phần giao tiếp phần cứng |

`docs/README_FRONTEND_CU.md` là tài liệu lịch sử, có các mô tả DRY RUN/hiệu chuẩn đã cũ. Hãy dùng hướng dẫn bàn giao này và tài liệu kiến trúc cho trạng thái hiện tại.

## 1. Chạy thử giao diện trên laptop, không cần phần cứng

Môi trường frontend đã dùng: Flutter **3.47.6**, Dart **3.13.5**; xem `docs/flutter_sdk_snapshot.json`. Cài Flutter và thêm `flutter` vào PATH trước khi chạy.

```powershell
cd frontend
flutter pub get
flutter run -d chrome --web-port 5173 --dart-define=FEEDER_MODE=mock
```

Đây là chế độ dữ liệu mô phỏng có nhãn MOCK, phù hợp chụp ảnh chức năng và trình bày bố cục. Thử các tình huống bằng URL `http://localhost:5173/?fixture=cat`, `?fixture=dog`, `?fixture=offline`, `?fixture=stale`, `?fixture=timeout`. Ảnh chụp chế độ này cần ghi rõ là mô phỏng trong báo cáo.

## 2. Chạy backend và bản web release trên laptop

Yêu cầu Python **3.11**. Chạy từ thư mục gốc của gói:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/jetson/requirements-realtime.txt
./scripts/run_backend_demo.ps1
```

Sau đó mở **http://127.0.0.1:8000/app**; tài liệu API ở **http://127.0.0.1:8000/docs**. Script dùng SQLite mới `backend/jetson/data/report_demo.db`, camera/serial mô phỏng và tắt worker lịch tự động. Không chạy bridge thiết bị trong bước này. Bản giao diện là REAL release nhưng dữ liệu API demo được đánh dấu MOCK; không coi đây là dữ liệu cảm biến thật.

Các dependency chỉ cần tải khi cài môi trường lần đầu. Bản `web_release` đã kèm CanvasKit và font cục bộ. `127.0.0.1` chỉ truy cập dịch vụ trên chính máy đang mở trình duyệt.

## 3. Build lại frontend từ source

```powershell
./scripts/build_web.ps1
```

Kết quả ở `web_build_local/`, có `forcat_build.json` để backend kiểm tra. Bản `web_release/` bàn giao được giữ nguyên. Muốn backend phục vụ bản mới, đổi biến `FORCAT_FLUTTER_WEB_DIR` trong script chạy từ `web_release` sang `web_build_local`.

Flutter REAL mặc định gọi API cùng máy chủ qua HTTP và WebSocket. Khi phát triển riêng frontend, có thể dùng `--dart-define=FEEDER_API_BASE_URL=http://<IP-Jetson>:8000/` cùng cấu hình CORS phù hợp; trình duyệt HTTPS vẫn có giới hạn khi gọi HTTP riêng. Cách triển khai đang dùng là backend phục vụ frontend cùng origin.

## 4. Kiểm thử source

```powershell
cd frontend
flutter analyze
flutter test
```

Backend: cài `backend/jetson/requirements-test.txt`, đứng tại `backend/jetson`, chạy `python -m pytest -c /dev/null` trên Linux hoặc chỉ định các bài cần kiểm tra trên Windows. Một số bài phụ thuộc Linux, C++, codec hay công cụ ngoài cần môi trường bổ sung. Không khẳng định toàn bộ test chạy được với requirements runtime tối thiểu.

## Dữ liệu và triển khai phần cứng

Không kèm database vận hành, ảnh camera, SSH key, mật khẩu hoặc trạng thái đăng nhập Tailscale. Bản local tạo database mới. Các script bridge và AI trong source là mã tích hợp thực tế của Jetson, có đường dẫn thiết bị/SQLite riêng; cần cấu hình và kiểm thử khi mang sang máy khác.

Trên Jetson thật, API dùng REAL state, bridge riêng sở hữu UART và AI TensorRT xuất kết quả qua bộ tap. Một số tên/biến hợp đồng cũ vẫn chứa `DRY_RUN`; bridge hiện tại có thể phát lệnh điều khiển thật. Hãy đọc luồng xử lý trong tài liệu kiến trúc trước khi mô tả hay triển khai phần này.

`docs/FILE_MANIFEST.json` lưu SHA-256 các file trong gói; `docs/remote_manifest.json` đối chiếu file lấy từ Jetson. Đây là bản chụp source ngày 08/11/2026, không chứa thay đổi trong tương lai.
