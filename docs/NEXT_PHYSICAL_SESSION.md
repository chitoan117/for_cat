# NEXT PHYSICAL SESSION — checklist sau OFFLINE RC 2026-10-26

**Kế hoạch cho phiên sau, KHÔNG phải lệnh đã chạy trong phiên offline.** Chạy tại console Jetson khi chủ thiết bị có mặt;
không mở SSH hoặc hardware để làm theo tài liệu ngay trong phiên RC. Đọc matrix [PROJECT_STATUS_20261026.md](PROJECT_STATUS_20261026.md) trước.
Mỗi bước ghi NOT_TESTED cho tới khi có evidence mới. Chỉ ghi PHYSICAL_PASS cho phạm vi vật lý thực sự đạt.
Nếu #2 chưa duyệt pin, ghi NOT_WIRED/BLOCKED và tiếp tục phần độc lập phù hợp; không bypass dependency của auto/actuator.

## Hồ sơ chung và các lệnh CHỈ ĐỌC dùng lại

Sau khi bước1 kiểm tra điện đạt, tại Jetson local console:

```sh
cd /home/toan/for_cat
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
EVIDENCE="/home/toan/for_cat/evidence/physical_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$EVIDENCE"
date -Ins > "$EVIDENCE/start_time.txt"
git status --short > "$EVIDENCE/git_status.txt"
git diff --stat > "$EVIDENCE/git_diff_stat.txt"
systemctl --user status for-cat-api for-cat-esp32-bridge for-cat-ai --no-pager > "$EVIDENCE/services.txt"
curl --fail --max-time 5 -sS http://127.0.0.1:8000/api/status > "$EVIDENCE/status_before.json"
curl --fail --max-time 5 -sS http://127.0.0.1:8000/api/v1/esp32/status > "$EVIDENCE/bridge_before.json"
curl --fail --max-time 5 -sS http://127.0.0.1:8000/api/meal-plans > "$EVIDENCE/plans_before.json"
journalctl --user -u for-cat-api.service -u for-cat-esp32-bridge.service -u for-cat-ai.service --since=-10min --no-pager > "$EVIDENCE/journal_before.log"
```

Cho từng bướcN, lưu `stepNN_status.json` bằng GET `/api/status`, `stepNN_bridge.json` bằng GET `/api/v1/esp32/status`,
`stepNN_events.json` bằng GET `/api/v1/esp32/events?limit=100`, ảnh/video có giờ, bảng reference/observed/error và kết luận có người thực hiện.
Snapshot đơn lẻ không chứng minh ổn định: giữ chuỗi mẫu có timestamp/age/timeout, không chỉ chụp một số đẹp.
Cuối phiên lưu safety_after, service journal và `sha256sum` các file evidence. Không mở thêm serial/camera reader cạnh tranh C++ process đang chạy.

## 1. Kiểm tra nguồn/common GND
- **Mục tiêu:** xác nhận nguồn Jetson/ESP32/cảm biến/cơ cấu và đường hồi GND trước khi cấp điện.
- **PASS criteria:** sơ đồ và phép đo đúng nguồn định mức, GND chung đúng thiết kế, không short; servo/pump vẫn tách nguồn/khóa. Echo vào MCU qua bảo vệ mức áp phù hợp; không coi xác nhận topology là phép đo điện áp.
- **FAIL criteria:** nguồn/GND/mức áp chưa xác định, chạm chập, sụt áp/nóng bất thường hoặc cơ cấu tự chạy.
- **Lệnh/log cần lưu:** chưa chạy lệnh thiết bị; ảnh wiring, sơ đồ nguồn, giá trị đồng hồ và người đo. Sau khi đạt mới tạo evidence chung ở trên.
- **Safety note:** cắt nguồn trước sửa dây; không lấy nguồn công suất cơ cấu từ chân GPIO.

## 2. ESP32 enumerate
- **Mục tiêu:** nhận đúng board qua USB, không chọn nhầm tty.
- **PASS criteria:** VID/PID/serial khớp board đã audit (historical1a86:55d3, serial5C85066678), tty ổn định qua quan sát; không suy PSRAM từ tên bán hàng.
- **FAIL criteria:** mất node lặp, identity khác/chưa rõ, brownout/reset loop.
- **Lệnh/log cần lưu:** `lsusb`, `ls -l /dev/serial/by-id/`, `udevadm info --query=property --name=/dev/ttyACM0`, `dmesg --ctime | tail -n 80`; thay tty bằng node enumerate thực tế, lưu output.
- **Safety note:** enumerate không cần flash; không nạp firmware từ staged tree legacy/conflicting pins.

## 3. Jetson/ESP32 connectivity
- **Mục tiêu:** một bridge đọc serial và state tới API.
- **PASS criteria:** đúng identity, telemetry fresh, age hợp lệ, trạng thái link phản ánh mất/kết nối thật; reconnect không tự arm hoặc thực thi intent cũ.
- **FAIL criteria:** stale/bad telemetry, hai serial readers, safety unknown/unsafe, mất link nhưng vẫn hiện số cũ như live.
- **Lệnh/log cần lưu:** bộ GET chung, service/journal, `fuser /dev/ttyACM0` để nhận biết owner; khi được phép thử USB reconnect lưu trước/mất/sau, không mở miniterm cạnh tranh.
- **Safety note:** AUTO và arming vẫn false/output0; nếu không xác nhận được cờ thì dừng bước có cơ cấu.

## 4. OLED
- **Mục tiêu:** xác nhận hiển thị thật đọc được và update theo state.
- **PASS criteria:** panel0x3C hoạt động, không reset, dữ liệu đổi theo cùng telemetry; trạng thái thiếu dữ liệu được thể hiện đúng.
- **FAIL criteria:** trắng/treo/hiện dữ liệu cũ sai, I2C lỗi hoặc reset.
- **Lệnh/log cần lưu:** step04 snapshots/journal, ảnh/video panel và app cùng thời điểm; không quét I2C tùy tiện khi driver đang sở hữu bus.
- **Safety note:** SDA8/SCL9 là cấu hình đã audit; không đổi pin hay điện áp trong lúc có nguồn.

## 5. PIR
- **Mục tiêu:** xác nhận chuyển động/không chuyển động và transition counter.
- **PASS criteria:** sau warm-up theo sensor, đáp ứng có lặp lại với người thao tác và không kẹt giá trị; timestamp fresh.
- **FAIL criteria:** không chuyển, chập chờn liên tục/thiếu telemetry; CONFIGURED một mình không đủ.
- **Lệnh/log cần lưu:** step05 snapshots theo hai trạng thái, video động tác và counter GPIO11.
- **Safety note:** PIR là evidence presence, không phải quyền tự mở servo.

## 6. Button
- **Mục tiêu:** kiểm press/release/hold GPIO21 và request qua arbiter.
- **PASS criteria:** nhấn LOW/thả HIGH, debounce, một request mỗi press, giữ không repeat; request bị xử lý DRY RUN và không chuyển động.
- **FAIL criteria:** bounce tạo nhiều intent, hold repeat, khởi động với nút giữ tự cấp, mismatch request/event.
- **Lệnh/log cần lưu:** step06 bridge/button/raw/debounced/request_count, events và journal; video short/hold/release; đối chiếu request ID.
- **Safety note:** INPUT_PULLUP nối nút về GND, không5V; không nối servo trực tiếp vào nút.

## 7. HC-SR04 #1
- **Mục tiêu:** ranging APPROACH, gần–xa có reference và tỷ lệ timeout đo được.
- **PASS criteria:** distance valid/fresh đáp ứng đúng chiều ở các khoảng cách chuẩn, đạt sai số/vùng làm việc đã định trước thử; ghi tỷ lệ valid/timeout, không dùng một sample để chứng nhận độ tin cậy.
- **FAIL criteria:** toàn timeout, sai chiều/ngoài tolerance, stale vẫn valid hoặc nhiễu/reset.
- **Lệnh/log cần lưu:** step07 chuỗi `approach.distance_cm/valid/health/timeout_count`, thước/reference, ảnh divider TRIG12/ECHO13, raw timeline.
- **Safety note:** kiểm mức áp ECHO thực tế; near threshold chưa được duyệt nên không bật AUTO_CAT.

## 8. HC-SR04 #2
- **Mục tiêu:** chốt vai trò inventory, pin rồi mới kiểm ranging.
- **PASS criteria:** có pin map được chủ thiết bị duyệt, giải quyết RESERVED và kiểm điện, sau đó đo như bước7; calibration full/empty là gate riêng cho %.
- **FAIL criteria:** vẫn NOT_WIRED, chưa approval16/17, xung đột legacyRTC hoặc không nhận echo.
- **Lệnh/log cần lưu:** pin approval/wiring/photo, step08 snapshots nếu firmware thực sự hỗ trợ; thiếu API/driver thì ghi BLOCKED, không tạo số frontend.
- **Safety note:** 16/17 chỉ là đề xuất UI, không phải chỉ dẫn đấu ngay. Không lấy bản staged legacy để flash.

## 9. JSN #1
- **Mục tiêu:** ranging WATER_OPERATIONAL trong vùng làm việc thực tế.
- **PASS criteria:** valid/fresh ở các mực nước/vị trí reference trong khoảng sensor hỗ trợ, repeatable; ghi blind zone/timeout, chưa suy thành pump pass.
- **FAIL criteria:** vùng đo không phủ bể thật, mất echo thường xuyên, sai chiều hoặc sensor bị nước theo cách không phù hợp thiết kế.
- **Lệnh/log cần lưu:** step09 `water_operational` timeline/reference, hình bể và TRIG14/ECHO15, divider/mức áp.
- **Safety note:** pump vẫn tách nguồn/khóa; không suy topology divider thành voltage measurement.

## 10. JSN #2
- **Mục tiêu:** chốt vai trò reservoir, pin và đo độc lập.
- **PASS criteria:** wiring/pin approval, giải quyết RESERVED18/10, đo hợp lệ như bước9; full/empty geometry được lưu riêng.
- **FAIL criteria:** NOT_WIRED/TBD, pin conflict, không có contract support hoặc timeout/sai vùng.
- **Lệnh/log cần lưu:** approval/schema thực, step10 readings nếu có; ghi NOT_WIRED/BLOCKED khi chưa đủ, không 0% giả.
- **Safety note:** đề xuất18/10 chưa áp dụng; không enable reservoir-based pump nếu dữ liệu chưa có.

## 11. HX711 raw
- **Mục tiêu:** xác nhận DOUT4/SCK5, raw signed24 và cơ khí trước fit.
- **PASS criteria:** raw_available/fresh, thêm tải raw đổi có quy luật, bỏ tải trở về vùng nền; không saturation, không dây kéo/rung/gãy cầu.
- **FAIL criteria:** raw missing/saturation, drift lớn hoặc return-zero sai; gram hiển thị dù chưa có authority hợp lệ.
- **Lệnh/log cần lưu:** step11 raw unloaded/loaded/unloaded timeline và age; GET `/api/hx711/status`, `/api/hx711/calibration`; ảnh gá loadcell5kg.
- **Safety note:** raw pass không phải calibrated gram; giữ actuator không chuyển động khi đo.

## 12. HX711 calibration: 0 / 5 / 10 / 20 / 30 / 35 g
- **Mục tiêu:** thu FIT nhiều điểm và kiểm chứng độc lập, không tái dùng training fit làm bằng chứng accuracy.
- **PASS criteria:** người thao tác xác nhận tải thật từng điểm, khay lắp bình thường; mỗi capture30s sau settle5s, ≥25 inliers/span≥25s. Fit đủ0/5/10/20/30/35; VERIFY mới0/5/10/20/30/35/0 đạt: zero±0.1g; nonzero±max(0.1g,1% reference); spread≤0.2g, sigma≤0.05g, drift≤0.1g. Hệ số signed đúng chiều; không nới tolerance để pass.
- **FAIL criteria:** cân đặt sai/nhầm mass, thiếu raw, zero drift, unstable hoặc bất kỳ verify không đạt; giữ NOT_CALIBRATED, không activate.
- **Lệnh/log cần lưu:** CLI dưới đây chỉ chạy từng lệnh sau khi chủ thiết bị đặt đúng tải; lưu JSON, `.raw.json`, checksum và ID. Phiên mới làm model cũ không active: đọc/backup evidence cũ trước, không tự xóa hoặc sửa điểm cũ.

```sh
# Kiểm CLI hiện có và metadata trước; KHÔNG chạy các lệnh này ở phiên offline.
"$PY" jetson/tools/hx711_calibration.py --help
"$PY" jetson/tools/hx711_calibration.py status > "$EVIDENCE/calibration_before.json"
"$PY" jetson/tools/hx711_calibration.py new --evidence-dir "$EVIDENCE/hx711" --load-cell-capacity-g 5000
# Lấy session_id thật từ output, gán SID bằng tay; không dùng ID giả hoặc đo trong loop tự động.
SID='SESSION_ID_VUA_TAO'
"$PY" jetson/tools/hx711_calibration.py capture --session "$SID" --phase fit --mass-g 0
# Sau khi đặt từng reference thật, lặp capture --phase fit --mass-g 5,10,20,30,35 bằng tay.
"$PY" jetson/tools/hx711_calibration.py fit --session "$SID"
# Đặt lại từng tải thật: capture --phase verify --mass-g 0,5,10,20,30,35,0; không dùng fit sample.
"$PY" jetson/tools/hx711_calibration.py validate --session "$SID"
# Chỉ khi validate đạt mới được xét activate; không gọi để vượt lỗi.
"$PY" jetson/tools/hx711_calibration.py activate --session "$SID"
```

- **Safety note:** frontend chỉ READINESS/read metadata; không có nút command calibration. Hệ số host không tự cấp quyền controller/servo. Rough demo±5g không thay formal criteria.

## 13. Persistence calibration
- **Mục tiêu:** chứng minh model sống qua restart sau activation và cân lại vẫn đúng.
- **PASS criteria:** activation hợp lệ, ID/offset/factor giữ đúng; restart ESP32 hoặc Jetson thực sự xảy ra **sau activation**; NEW0/35/0 phase persistence đạt cùng tiêu chí. API process restart đơn thuần không thay gate host/MCU restart.
- **FAIL criteria:** mất hệ số/binding mismatch, restart trước activation, sai số/độ ổn định fail hoặc thiếu evidence restart.
- **Lệnh/log cần lưu:** GET calibration trước/sau, `cat /proc/sys/kernel/random/boot_id` và MCU monotonic trước/sau; capture `--phase persistence --mass-g 0`, rồi35,rồi0 bằng tay; chỉ đủ điều kiện mới `"$PY" jetson/tools/hx711_calibration.py finish --session "$SID" --confirm-physical-tests`. Lưu toàn bộ output/boot evidence/checksum.
- **Safety note:** cơ cấu vẫn khóa trong restart; tránh active plan tới hạn và bất kỳ auto execution. Không xóa DB để “làm sạch” calibration.

## 14. Servo test riêng
- **Mục tiêu:** kiểm cơ khí đóng/mở và trạng thái khi mất nguồn riêng, chưa cấp ăn tự động.
- **PASS criteria:** có đường bench command đã review/được cho phép thực sự, góc giới hạn/tải/nguồn đã chốt; motion/closure đúng, không kẹt/quá dòng, dừng an toàn và không ảnh hưởng HX.
- **FAIL criteria:** hiện không có đường command actuation được phê duyệt → BLOCKED; hoặc tự chuyển động/kẹt/sụt áp/không đóng.
- **Lệnh/log cần lưu:** step14 GET/journal, video/góc/dòng/điện áp, transcript lệnh bench được review **nếu đã tồn tại ở phiên sau**. RC không cung cấp lệnh mở servo; không bịa endpoint.
- **Safety note:** không mở global AUTO/arming để lách safe mode; thử servo riêng không chứng minh35g.

## 15. Closed-loop 35 g
- **Mục tiêu:** đo khối lượng cấp thêm, độc lập với thời gian servo và lượng đang có trong khay.
- **PASS criteria:** bước12–14 đạt và controller actuation path được review; stable_before, chuyển động có bound/stop, stable_after; actual=after−before đo được và đối chứng cân/reference. Định trước tolerance/số lần lặp cho dispensing; chưa chốt tiêu chí thì NOT_TESTED, không mượn ±0.35g calibration làm chứng chỉ dispensing.
- **FAIL criteria:** jam/không tăng/overshoot/timeout/stale, thiếu before/after hoặc coi target là actual; lưu failed attempt và null actual nếu không thể xác minh, không ép số về0.
- **Lệnh/log cần lưu:** step15 snapshots, request/occurrence/arbiter IDs, raw+grams timeline, stable windows, closure/stop reason/video và cân đối chứng. Chỉ dùng command path được review; chưa có thì BLOCKED.
- **Safety note:** giữ người giám sát và khả năng cắt nguồn; target35g không phải bộ hẹn giờ servo. Không “tuning” bằng mở auto không giới hạn.

## 16. AUTO_CAT DRY RUN
- **Mục tiêu:** CAT + near + temporal/stability + cooldown/calibration evidence tạo request qua arbiter, không motion.
- **PASS criteria:** near threshold có reference thực, CAT/DOG/NONE và stale/missing cases được kiểm; CAT đủ điều kiện tạo đúng một intent có ID và blocked dry-run decision; không request khi DOG/NONE/sensor lỗi; execution=false/actual=null.
- **FAIL criteria:** UI tự suy READY, request trùng/repeat, bỏ gate hoặc state chưa expose mà trình bày như có live FSM.
- **Lệnh/log cần lưu:** step16 AI/approach/decisions/events timeline, request ID/cooldown, video khoảng cách; dedicated state thiếu thì ghi UNKNOWN/NOT_AVAILABLE. Không thêm camera/serial reader thứ hai.
- **Safety note:** đây là DRY_RUN_PASS, không phải PHYSICAL_PASS feeding; không enable servo ở bước này.

## 17. AUTO_CAT physical
- **Mục tiêu:** toàn luồng từ evidence thật tới một lần cấp bounded.
- **PASS criteria:** bước15–16 và mọi calibration/geometry/safety dependency đạt, command path được review; từng intent có actual đo được và cooldown chống lặp; DOG/NONE/stale/noisy phải chặn.
- **FAIL criteria:** bất kỳ dependency thiếu, duplicate/ngoài ý muốn hoặc không có khối lượng thật → BLOCKED/NOT_TESTED, không completion giả.
- **Lệnh/log cần lưu:** step17 timeline, actual/stable windows/arbiter receipt/video và safety trước/sau. API hiện không cho phép thì ghi BLOCKED, không sửa contract ngay tại bench để chạy.
- **Safety note:** không dùng AI output trực tiếp mở servo; người giám sát và stop path là điều kiện của phép thử.

## 18. JSN water threshold
- **Mục tiêu:** chuyển distance thành mực nước với geometry thật, chọn hysteresis/min–max hợp lý.
- **PASS criteria:** bể/empty/full/blind zone xác nhận; threshold on/off có khoảng hysteresis, có debounce/temporal confirmation, invalid/stale không yêu cầu pump.
- **FAIL criteria:** chỉ đo một mức, nhầm distance với level, chưa cấu hình hoặc ngưỡng ngoài vùng đo → BLOCKED.
- **Lệnh/log cần lưu:** step18 water distance/valid/age và shadow decisions theo mực nước reference; bảng geometry/ngưỡng đã duyệt. Không ghi %/ngưỡng vào REAL DB bằng fixture.
- **Safety note:** pump vẫn khóa; threshold hợp lệ chưa chứng minh motor/flow.

## 19. Pump controlled test
- **Mục tiêu:** kiểm công suất/driver, bounded ON/OFF và lưu lượng thật riêng.
- **PASS criteria:** driver/nguồn/phần bảo vệ phù hợp, command bench đã review có max-on/stop; flow thực đo được, OFF thật sau stop/timeout/lỗi, không reset hệ thống.
- **FAIL criteria:** command chưa tồn tại → BLOCKED; pump không dừng, chạy khô, tràn/rò/sụt áp hoặc chỉ có flag không có flow proof.
- **Lệnh/log cần lưu:** step19 snapshots/journal, command transcript nếu được phép, video/dòng/điện áp/lưu lượng/thời gian/stop reason; không bịa endpoint pump.
- **Safety note:** GPIO7 là signal không phải nguồn motor; không bật AUTO_WATER để thay phép thử controlled, giữ nước xa điện tử.

## 20. AUTO_WATER
- **Mục tiêu:** cấp nước bounded theo level/threshold và fail-closed khi sensor lỗi.
- **PASS criteria:** bước9/18/19 và geometry nguồn nước cần thiết đã đạt; low tạo request, high dừng, hysteresis tránh rung; max-on/cooldown/invalid/stale/source-empty đều được xử lý có evidence.
- **FAIL criteria:** một dependency chưa đạt, level UNKNOWN, pump lặp/tràn/không dừng hoặc flag dùng thay flow proof → BLOCKED.
- **Lệnh/log cần lưu:** step20 timeline level/threshold/request/actual pump state/stop reason/video và các case fault; final safety_after và hash manifest của phiên.
- **Safety note:** khi kết thúc trả về chế độ khóa theo cấu hình đã duyệt; không để auto chạy unattended từ một lần demo.

## Ghi kết quả

Mỗi bước ghi: người thực hiện, giờ VN+UTC/boot identity, setup/reference, observed, tiêu chí, evidence path+hash,
Software/Runtime/Physical status và hạn chế. Bất kỳ FAIL đều giữ nguyên log/raw; không sửa số đo, không biến “đã đấu” thành PHYSICAL_PASS.
RC hiện tại không cấp sẵn quyền thực hiện các bước14/15/17/19/20; cần review đường command và gate ở phiên có hardware.
