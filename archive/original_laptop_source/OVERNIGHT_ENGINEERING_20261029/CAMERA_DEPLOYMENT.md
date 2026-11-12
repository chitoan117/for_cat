# Camera deployment preparation — giữ streaming đã PASS

Không đổi C++ capture/queue/encoder, FastAPI stream hoặc Flutter source trong phiên overnight. Dùng artifacts `LIVE_CAMERA_REMOTE_PREP_20261028` đã PASS:32backend tests,20015queue assertions,6camera/24overview Flutter tests,analyze,REAL/MOCK web builds,localhost synthetic MJPEG/browser. Đây là evidence historical, không rerun toàn bộ và không phải camera Jetson thật.

## Source/ảnh cùng frame

`roi_ai_source.cpp` lấy một packet từ existing capture, inference và preview cùng packet; `preview_queue.h` latest pending1; `preview_publisher.h` worker encode/network riêng, demand-only. Bounding boxes/ROI/class/confidence được burn cùng JPEG; Flutter không vẽ metadata polled khác frame. Viewer limit4, latest JPEG512KiB, stale2s, disconnect cleanup đã có trong backend. Không tạo camera owner bổ sung.

## Preflight mới (không launch)

Sau khi owner copy/stage release theo `DEPLOYMENT_RUNBOOK.md`, tạo server-only config **ngoài release và webroot**, trên Jetson:

```sh
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
REL=/home/toan/forcat-staging/releases/release_camera
# Thay hostname và identity bằng giá trị thật; không dùng chuỗi ví dụ để deploy.
"$PY" "$REL/tools/prepare_remote_config.py" --output /home/toan/forcat-private-new --hostname ACTUAL_HOST.ts.net --viewer VIEWER_LOGIN
"$PY" "$REL/tools/camera_preflight.py" --config /home/toan/forcat-private-new/server-env.json --bundle "$REL"
```

Config/token/access phải regular private files0600; không in token, không lưu vào Flutter. Preflight kiểm tra original providerMOCK/MOCK/MOCK+stateREAL, API loopback, CORSempty, exact HTTPS `.ts.net`, view-only identity tách operator, REAL static artifact hash, `/flutter/` base href và không có token trong assets. Giá trị hostname phải lowercase thật. Tool tạo config có thể cấp thêm operator riêng qua `--operator`; mặc định chỉ VIEW_CAMERA, không FEED_MANUAL.

Preflight **không** kiểm tra network đang hoạt động hoặc start API/camera. Chỉ sau owner maintenance window mới dùng launcher đã chuẩn bị; launcher `run_secure_api.py` là lệnh start thật, không phải preflight và không có plan mode. Nó trỏ DB canonical; không chạy cạnh API production8000, không chạy khi đang ngủ. Staging test API phải có DB sandbox riêng và profile được review, không dùng launcher canonical một cách vô ý.

`run_cpp_preview.py` mặc định plan; `--execute` mở camera thật, cần owner xác nhận camera và AI-writer đã được chuyển khỏi legacy service. Không pipe producer vào tap; không chạy hai detector. Giữ FULL_FRAME mặc định, candidate ROI chưa review không enable.

## LAN rồi 4G/5G

1. Owner kiểm tra local loopback API/MJPEG và stream status, bật/tắt viewer, mất camera/reconnect,1→4 viewers, viewer5 bị giới hạn. Confirm frame/class/ROI cùng ảnh; theo dõi AI latency/FPS khi viewer chậm. Không cấp thức ăn.
2. Kiểm tra trên LAN qua **cùng HTTPS tailnet origin** với điện thoại/laptop đã tham gia tailnet. API vẫn loopback; không bind public/LAN để bypass auth. Serve HTTPS do owner cấu hình sau review, không Funnel. `serve_private.sh` chỉ plan mặc định; không chạy `--apply` trong phiên này. Nếu port443 đã phục vụ app khác, dừng để review config/rollback trước.
3. Điện thoại tắt Wi-Fi dùng4G/5G và Tailscale; mở cùng URL `/flutter/`. Xem/Tắt, LIVE/CONNECTING/OFFLINE/ERROR; thật phải có REAL source, synthetic phải SIMULATED. View-only không được manual feed/system mutation. Logout/identity không allowlist bị403. Không chụp/log producer token.
4. Khi lỗi: tắt viewer, giữ production baseline, đọc status/log; không bật providerREAL hoặc resetDB để vượt lỗi. Trước thay Serve cần owner lưu config hiện hành; không dùng `tailscale serve reset` làm rollback chung vì có thể xóa mapping khác.

## Rollback

Chưa có cutover/network changes trong overnight nên không có live rollback cần chạy. Staging pointer rollback có script/backup riêng; live runtime/network rollback cần cấu hình thực tế trước thay đổi. Static web được phục vụ cùng API origin từ `web_real/`, base `/flutter/`; không deploy nó sang Pages cross-origin để truy cập private stream.

`LIVE_CAMERA_JETSON_DEPLOY_READY=YES` = bundle/config-validation/preflight preparation. ARM64 build, physical webcam stream, Tailscale LAN/4G, service cutover đều **NOT VERIFIED**. Không đặt `REAL_CAMERA_STREAM_PASS`.
