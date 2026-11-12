# LIVE CAMERA + SECURE REMOTE VIEW — offline preparation 2026-10-28

**LIVE_CAMERA_OFFLINE_READY: YES.** Đã có demo video **SIMULATED chạy thực tế trên Windows**, FastAPI MJPEG và Flutter Web REAL cùng origin; không mở webcam/ESP32, không SSH/flash hay cài/login Tailscale. CAMERA_PHYSICAL_PASS và REMOTE_ACCESS_PASS **chưa được xác minh**.

## 1. Source và files changed

Backend/C++ authority: `FULL_HARDWARE_INTEGRATION_20261027/payload`, không dùng checkout `D:\for_cat\jetson` cũ. Firmware/HX711/ROI core/E2E được đối chiếu bằng hashes, không sửa thuật toán hoặc pin map.

Trong `payload/`:
- **Thêm** `jetson/app/camera/live_stream.py`: latest JPEG hub, metadata validation, status/MJPEG/private producer endpoints, viewer/resource bounds và cleanup.
- **Thêm** `jetson/app/camera/remote_access.py`: loopback/host/origin/Tailscale identity và VIEW_CAMERA/FEED_MANUAL/CONTROL_SYSTEM scopes.
- **Thêm** `jetson/app/http_middleware.py`: giữ nguyên empty-body contract của manual feed bằng ASGI pass-through, tránh BaseHTTPMiddleware bọc stream vô hạn.
- **Sửa** `jetson/app/main.py`: chỉ wiring hub/router/lifespan/access; chặn Python USB capture khi C++ stream owner được bật.
- **Sửa** `jetson/tools/run_api.py`: `proxy_headers=False` để kiểm tra socket peer thật.
- **Thêm** `jetson/device/preview_queue.h`, `preview_publisher.h`: bounded handoff, worker JPEG/annotation/loopback publisher.
- **Sửa** `jetson/device/roi_ai_source.cpp`: cấp frame/metadata cùng packet cho preview sau inference; không đổi detector/decoder/engine.

Flutter source chính `D:\DA_KT_NC\feeder_demo`:
- **Sửa** `lib/user_pages.dart`: thêm camera panel riêng ở trang “Bữa ăn của MÈO”, stable key; không redesign hoặc đổi các trang khác.
- **Thêm** `lib/live_camera_controller.dart`, `live_camera_panel.dart`, `live_camera_image.dart`, `live_camera_image_web.dart`, `live_camera_image_stub.dart`, `test/live_camera_test.dart`.
- Giữ state camera khi backend cập nhật/reorder; dừng request khi Tắt camera hoặc rời trang. REAL/MOCK tách biệt, MOCK có nhãn SIMULATED.

Tooling/evidence trong `LIVE_CAMERA_REMOTE_PREP_20261028/`: `synthetic_video.py`, `demo_server.py`, focused tests/verify scripts, `browser_smoke.cjs`, `build_flutter.py`, `finalize.py`; remote-prep helpers/config templates được liệt kê ở phần6. `CAT_APPROACH_DOG_BUZZER_20261028/verify_jetson.py` chỉ được cập nhật manifest header cho lần build tương lai, **không chạy SSH**.

Không thay frontend artifact `WEB_FINAL_20261027`; build mới ở bundle riêng. `verification.json` xác nhận hash các core E2E/HX711/ROI/Feed Arbiter/UART/Scheduled Worker và WEB_FINAL cũ được bảo toàn. Servo/pump vẫn **LOCKED**, HX711 **PHYSICAL_VALIDATION_PENDING**.

## 2. Kiến trúc frame sharing thực tế

```text
USB webcam (future Jetson)
  -> existing C++ latency::Capture / LatestSlot — ONLY capture owner
  -> existing Detector::infer: OpenCV + YOLOv8n320 + TensorRT FP16
  -> AI state / ROI evidence (existing canonical DB)
  -> optional preview Queue (pending depth1, newest replaces old)
     -> lower-priority JPEG worker (no camera open, no GPIO)
        -> same-packet bbox/ROI/class/confidence/frame-id/capture timestamp
        -> resize fit<=640x480, burn annotations, JPEG quality configurable
        -> authenticated loopback HTTP -> FastAPI FrameHub (latest JPEG only)
           -> bounded MJPEG clients -> Flutter Web native image
```

- Preview callback không encode/network trên AI thread; truyền immutable Mat reference và metadata cùng packet. Worker tạo ảnh resize riêng để vẽ, không sửa frame đầu vào detector.
- Dùng lại primitive `latency::LatestSlot`; một frame pending và một frame đang xử lý, không có hàng đợi kéo dài theo viewer. Consumer chậm không giữ inference chờ HTTP.
- Worker hạ nice của riêng encoder thread xuống10 trên Linux; HTTP có deadline250ms. Preview lỗi/config sai sẽ disable preview, không làm chết AI.
- C++ target preview **6FPS**, fit tối đa640×480 giữ aspect ratio; `FORCAT_JPEG_QUALITY=30..90`, default70. Đây là cấu hình mục tiêu, **không phải đo FPS thực tế trên Jetson**.
- Producer chỉ encode khi có viewer hoặc viewing-intent lease. Khi tắt xem, intent hết trong2s và demand polling/lease tối đa khoảng1s bổ sung; AI capture vẫn tiếp tục.
- FastAPI giữ1 JPEG, default tối đa4viewer, tối đa512KiB/JPEG, metadata4KiB. Mỗi stream chỉ giữ snapshot đang gửi; send timeout5s, stream lease300s, frontend renew trước khi lease hết. Không ghi video thường trực ra đĩa.
- Frame được gắn annotations **ngay trong JPEG**. Backend kiểm tra frame-id/metadata-id/overlay-id, JPEG dimensions, tọa độ, source REAL/SIMULATED và timestamp trước khi fan-out. Flutter không vẽ bbox từ status poll lên một ảnh khác.
- Capture timestamp hiện hành là monotonic **sau camera read**, không phải sensor exposure time. Khi nguồn mất/stale, clear latest frame và trả CAMERA_OFFLINE; không thay bằng ảnh giả.

## 3. Endpoint và ranh giới quyền

| Endpoint | Quyền/ý nghĩa |
|---|---|
| `GET /api/v1/camera/status` | VIEW_CAMERA; CAMERA_ONLINE/OFFLINE, source, viewer count, frame age/dimensions/budget |
| `GET /api/v1/camera/status?watch=true` | VIEW_CAMERA; short viewing-intent lease để bootstrap encoder không người xem |
| `GET /api/v1/camera/mjpeg` | VIEW_CAMERA; `multipart/x-mixed-replace; boundary=frame`, JPEG/no-store/private |
| `GET /internal/camera/demand` | Loopback + private producer bearer token, không nhận Serve/user/origin forwarded context |
| `POST /internal/camera/frame` | Cùng producer-only boundary; bounded body/metadata; không ghi feed/device state |

`?frames=1..60` là tùy chọn hữu hạn cho kiểm tra/client đọc ngắn. Không có camera endpoint nào tạo feed request hoặc gọi servo/pump.

**Default secure:** stream disabled; chưa cấu hình access thì camera denied. Khi bật video, app từ chối cấu hình Python USB camera (kể cả injected provider) để tránh capture thứ hai.

### Tailscale Serve profile

- API chỉ bind **127.0.0.1**, một uvicorn worker, **proxy_headers=False**. Không public8000, không router port-forward, không Funnel.
- Serve HTTPS là trusted proxy; app yêu cầu socket peer loopback, exact tailnet hostname, `X-Forwarded-Proto:https`, `Tailscale-User-Login` nằm trong **server-side allowlist**, và same-origin. Duplicate/foreign/malformed headers bị từ chối.
- Ranh giới tin cậy bao gồm **Serve và local processes trên Jetson**. Không coi headers từ một peer mạng/LAN/tailnet trực tiếp là identity đã xác thực. Serve phải cung cấp/sanitize identity headers theo contract; cần kiểm tra phiên bản thực tế khi triển khai, không có fallback insecure.
- VIEW_CAMERA cho xem camera/static UI và các dashboard GET/WebSocket cần để hiển thị trang. **Không** cho POST manual feed/preview; FEED_MANUAL là quyền riêng. Các API ghi khác cần CONTROL_SYSTEM, mặc định không cấp.
- Quyền HTTP không mở khóa feeding: actor safety/arbiter/HX711 authority vẫn giữ nguyên. Actor production tiếp tục locked.
- Producer token chỉ có ở file server0600 và C++ loopback request, không ở Flutter/query URL. Tailscale user/viewer, kể cả operator, không dùng identity header để upload frame.
- LOCAL_DEMO chỉ tin loopback + Host localhost/127.0.0.1 và chỉ cho đọc; không phải profile truy cập Internet. API disabled profile gặp forwarded remote headers sẽ fail closed.

## 4. Kết quả test/build và bằng chứng

| Kiểm tra thực sự đã chạy | Kết quả |
|---|---|
| Backend focused: camera/security/lifecycle và5 case empty-feed-body bị ảnh hưởng | **32 PASS** |
| Portable C++14 preview queue/stamp, strict warnings | **20015 assertions PASS**;20000 offers khi consumer bị giữ, pending limit1 |
| Flutter camera/controller/widget tests | **6 PASS** |
| Existing affected overview/user_app_offline cases | **24 PASS** trong milestone; không full regression |
| Flutter analyze | **No issues found** |
| REAL và MOCK web release, local CanvasKit/font | **PASS**, khác hashes; WEB_FINAL artifact cũ giữ nguyên |
| Actual localhost HTTP MJPEG:2 viewers + viewer cap +3 JPEG decode | **PASS**,640×480, disconnect viewer count về0, không feed |
| Chrome + compiled Flutter REAL + synthetic API | **PASS** LIVE·SIMULATED; CAT/DOG/NONE; ROI overlay; Tắt camera hủy image/viewer |
| Browser external resources / write requests | **0 external requests, 0 runtime exceptions, chỉ GET** |
| Tailscale live / ARM64/CUDA/TensorRT mới / webcam thật | **NOT_VERIFIED** |

Coverage: MIME/boundary/content-length; disconnect/send-timeout/shutdown/reconnect; source epoch/duplicate/stale/invalid JPEG/metadata wrong id/wrong dimensions; latest-frame drop/bounded viewer memory; ROI ON/OFF và FULL_FRAME; source SIM không lọt REAL contract; unauthorized/missing/forged remote identity, host/origin/proto/scopes; VIEW_CAMERA không POST feed; WebSocket cùng boundary; không view thì dừng encode nhưng synthetic capture tiếp tục.

Blocker đã sửa tối thiểu: body-bound middleware cũ được port sang ASGI pass-through để không bọc/giữ response video vô hạn;5 feeding-body contract cases xác nhận giữ nguyên. Camera panel thêm key/keep-alive vì status backend có thể thêm/bớt widget trước nó; regression test xác nhận camera không reset OFF. Windows synthetic server dùng selector loop và graceful timeout để cleanup socket/disconnect ổn định.

Bằng chứng trong `D:\for_cat\LIVE_CAMERA_REMOTE_PREP_20261028\`:
- `verification.json`, `backend_focused.log`, `preview_compile.log`, `preview_test.log`.
- `windows_http_result.json`, `browser_result.json`, `flutter_build_result.json`, build logs.
- **`flutter_simulated_live.png`**, **`flutter_simulated_roi_dog.png`**, **`flutter_simulated_none.png`**, `simulated_http_frame.jpg`: đều synthetic, không ảnh webcam thật.
- Flutter test/analyze đã PASS từ tool invocation trong milestone; verification ghi rõ provenance, không chạy lại chỉ để chép log. Browser/video evidence là kiểm tra bổ sung trên bản build thực.

## 5. Chạy demo video Windows ngay, không cần thiết bị

```powershell
& "D:\for_cat\.venv\Scripts\python.exe" "D:\for_cat\LIVE_CAMERA_REMOTE_PREP_20261028\demo_server.py" --port 8765
```

Mở **http://127.0.0.1:8765/app**, cuộn tới CAMERA TRỰC TIẾP → Xem camera. Nguồn được đánh dấu **SIMULATED**, tuần tự CAT/DOG/NONE, ROI minh họa và frame-id/timestamp gắn trên ảnh. Tắt camera đóng request. Ctrl+C dừng demo.

Demo dùng database riêng trong `demo_runs/<UTC>/synthetic_camera.sqlite3`, scheduled worker tắt, không serial/camera/model. Không dùng database production. Trong venv Windows hiện chưa có WebSocket server adapter nên dashboard cũ có thể dùng REST fallback/hiển thị reconnect; **MJPEG không phụ thuộc WebSocket** và đã được Chrome xác minh độc lập.

Lệnh focused khi cần chạy lại:
```powershell
& "D:\for_cat\.venv\Scripts\python.exe" "D:\for_cat\LIVE_CAMERA_REMOTE_PREP_20261028\verify_backend.py"
& "D:\for_cat\.venv\Scripts\python.exe" "D:\for_cat\LIVE_CAMERA_REMOTE_PREP_20261028\verify_native.py"
& "D:\for_cat\.venv\Scripts\python.exe" "D:\for_cat\LIVE_CAMERA_REMOTE_PREP_20261028\verify_windows_http.py"
node "D:\for_cat\LIVE_CAMERA_REMOTE_PREP_20261028\browser_smoke.cjs"
```

## 6. Chuẩn bị Jetson/Tailscale — lệnh tương lai, chưa thực thi

Không blind-copy checkout Windows/snapshot lên Jetson. Đối chiếu source hiện hành, backup, áp dụng các file/delta liệt kê ở phần1; giữ original detector/engine và worktree/index. Copy REAL artifact mới vào release directory riêng.

Yêu cầu: project Python>=3.10 (venv trước đây là Python3.11), FastAPI/uvicorn đang dùng; không dùng system Python3.6 của Nano. OpenCV/CUDA/TensorRT phải đúng SDK đang có. WebSocket adapter (`websockets`/`wsproto` hoặc uvicorn standard) chỉ cần cho realtime state API, không phải MJPEG; chưa cài thêm ở milestone này.

Ví dụ sau khi source đã được cập nhật trên Jetson:
```sh
ROOT=/home/toan/for_cat
PY="$ROOT/.venv/jetson-integration/bin/python"
PREP="$ROOT/LIVE_CAMERA_REMOTE_PREP_20261028"
BIN="$ROOT/.native-build/live_camera_20261028"
mkdir -p "$BIN"
sh "$ROOT/scripts/build_roi_ai_source.sh" "$BIN/roi_ai_source"

# Thay bằng hostname/login thật; tạo thư mục config MỚI, không ghi đè config owner.
"$PY" "$PREP/prepare_remote_config.py" --output "$HOME/.config/for-cat-camera-v1" \
  --hostname ACTUAL_MACHINE.ACTUAL_TAILNET.ts.net --viewer VIEWER_LOGIN --operator OPERATOR_LOGIN

# Terminal1: API + REAL Flutter cùng origin; backend loopback, không proxy-header rewriting.
"$PY" "$PREP/run_secure_api.py" --config "$HOME/.config/for-cat-camera-v1/server-env.json" \
  --repo "$ROOT" --flutter-web-dir /ABSOLUTE/NEW_CAMERA_RELEASE/web_real

# Terminal2: chỉ sau khi đã dừng camera owner cũ; helper từ chối nếu fuser thấy bận.
"$PY" "$PREP/run_cpp_preview.py" --config "$HOME/.config/for-cat-camera-v1/server-env.json" \
  --repo "$ROOT" --binary "$BIN/roi_ai_source" --roi-config - --device /dev/video0 --execute
```

`CAMERA_PROVIDER=MOCK`, `AI_RUNTIME=MOCK` trong API profile nghĩa là **không chạy legacy Python capture/inference**; nguồn video/AI thực ở process C++ và `FORCAT_STREAM_SOURCE=REAL`. Nó không đổi stream thực thành mock. Không chạy `run_existing_ai.sh` hoặc producer khác đồng thời. C++ còn giữ canonical AI-owner lock; viewer không mở camera.

Config/tools đã chuẩn bị: `prepare_remote_config.py`, `run_secure_api.py`, `run_cpp_preview.py`, `tailscale-access.example.json`, `tailscale-grants.example.json`, `serve_private.sh`. Không có secret cố định, không thực hiện cài đặt hay login.

Khi Jetson có Internet và owner đã cài Tailscale từ nguồn chính thức:
```sh
sudo tailscale up --advertise-tags=tag:for-cat
# Owner tự login/approve device, HTTPS/MagicDNS và merge/review grants trên tailnet.
sudo tailscale serve --bg --https=443 http://127.0.0.1:8000
tailscale serve status
```

Chỉ expose **HTTPS443 trong tailnet**. Không port-forward router, không Funnel, không Cloudflare Tunnel ở milestone này. Review policy đang có để tránh grant allow-all chồng lấn. Allowlist app vẫn bắt buộc, kể cả tailnet ACL rộng hơn dự kiến.

Mở **https://ACTUAL_MACHINE.ACTUAL_TAILNET.ts.net/app**: Flutter/API/MJPEG cùng origin. Không mở raw8000 từ mạng ngoài. Không tin forwarded identity khi dùng server `--proxy-headers` hoặc bind public; launcher đã cố định ranh giới an toàn.

### Cloudflare Pages hiện tại

Trang Pages là origin khác và không tự có đường vào camera tailnet riêng. Camera panel chặn cross-origin; không mở CORS rộng, không đưa producer token vào web để né lỗi. Cách truy cập đã chuẩn bị là **bản REAL Flutter tương ứng được FastAPI phục vụ qua Tailscale Serve cùng origin HTTPS**. Pages có thể tiếp tục dùng cho mục đích khác; chưa triển khai Cloudflare Tunnel/Access.

## 7. Checklist LAN → điện thoại4G/5G sau này

- [ ] Áp dụng source có kiểm tra/backup, rebuild native ARM64 trong SDK thực; giữ engine FP16/model hashes. Không coi Windows PE/test exe là ELF Jetson.
- [ ] Một capture owner: dừng owner cũ có kiểm soát, kiểm tra fuser/AI lock, Python USB mode bị chặn. Đo AI FPS khi có/không viewer.
- [ ] LAN kiểm tra từ session được bảo vệ (Serve/tailnet): CAT/DOG/NONE, bbox và ROI cùngframe-id/timestamp; mất webcam báo OFFLINE, reconnect tự phục hồi.
- [ ] Đo preview640×480/fit aspect, FPS/CPU/RAM/frame-age P50/P95 trên Nano; target5–10FPS chưa được chứng minh bằng tests Windows.
- [ ] Mở đủ viewer/slow client, vượt cap bị từ chối; Tắt/rời trang trả viewer count; encode dừng sau lease ngắn nhưng AI vẫn chạy. Shutdown không giữ socket/task vô hạn.
- [ ] Điện thoại bật4G/5G và Tailscale, đăng nhập login được allowlist/grant, vào HTTPS/app. Tắt Tailscale hoặc dùng user chưa được phép phải không xem được.
- [ ] VIEW_CAMERA không POST feed/preview/schedule; FEED_MANUAL là scope riêng và vẫn không bỏ safety lock. Forged headers từ mạng/host/origin sai phải bị từ chối.
- [ ] Xác minh Serve version cấp/sanitize identity headers đúng contract; chỉ loopback backend, không public port8000. LOCAL_DEMO không dùng làm cấu hình remote.
- [ ] Servo/pump LOCKED; HX711 PHYSICAL_VALIDATION_PENDING. Không lấy bất kỳ video SIMULATED hoặc mock completion nào làm physical evidence.

## 8. Phần chưa xác minh

Chưa có Jetson/webcam/ESP32: updated ARM64/CUDA/TensorRT/OpenCV encoder build, camera exposure/driver latency, voltage/actuation, FPS/thermal behavior và hiệu quả ROI trên camera thật đều **NOT_VERIFIED**. Chưa chạy Tailscale daemon/Serve/HTTPS/ACL trên mạng thật hay điện thoại4G/5G. Không có CAMERA_PHYSICAL_PASS hoặc REMOTE_ACCESS_PASS.

**LIVE_CAMERA_OFFLINE_READY: YES**
