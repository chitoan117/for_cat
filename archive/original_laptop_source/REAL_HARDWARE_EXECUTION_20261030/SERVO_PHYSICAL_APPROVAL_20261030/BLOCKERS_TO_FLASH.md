# BLOCKED — bằng chứng còn thiếu, không tự chuyển thành PASS

Nguồn đối chiếu: `HARDWARE_PHYSICAL_BRINGUP_20261029/final_pre_flash_review/GO_NO_GO.json`, `maintenance_readiness/*`, `HX711_ACCEPTANCE.json`; receipt/build manual và bàn giao `POSIX_BIND_DUAL_20261030`. Các gate lịch sử được cập nhật bằng xác nhận mới về nguồn5V–10A/hai dây motor, không sửa hồ sơ khóa.

| Gate | Còn thiếu / kiểm tra cụ thể | Vì sao chặn |
|---|---|---|
| Running partition + board/boot binding | Log actual normal boot/loaded-app offset gắn đúng board/boot hiện hành; thu trong maintenance đã duyệt nếu chưa có log gốc | OTA metadata app0/0x10000 không chứng minh app đang chạy; không cấp write offset từ giá trị mặc định |
| Security/eFuse/antirollback | Bản decode board-bound secure boot, encryption, download restrictions, secure-version counter và compatibility old/new image | Image mới secure_version0; không biết policy thì chưa biết có boot/rollback/ROM recovery được không. Chỉ read-ROM sau approval, không burn/force/stub fallback |
| Bảo toàn HX calibration | Log gốc/record chứa **exact offset và counts-per-gram**, đúng mounting/context, hoặc chứng cứ NVS hiện có tương thích `m4-calibration/sensors-v2` | Acceptance ghi factor-1064.4473 nhưng offset chỉ **xấp xỉ-698922.87**, raw attachment mới nhất chưa được tìm thấy trong review trước. Không lấy số xấp xỉ để restore. Backup/APP rollback không phục hồi RAM |
| Servo model/power/GND/cutoff | Nhãn/model servo, ảnh đườngV+/GND/GPIO6/ngắt tải; số đo DC ở đầu cấp servo với servo chưa nối tải và đúng reference sau khi sơ đồ/model được review |5V–10A là rating nguồn, không xác minh điện áp/rating servo hay đường GND/ngắt tải. Không chọn pulse/góc trước model/cơ cấu; không dùng ohmmeter trên mạch đang cấp điện |
| Cô lập tải cho reset/flash | Owner xác nhận/ảnh điểm ngắt **riêng tải servo** và điều kiện buzzer không tự hoạt động; không ngắt nguồn ESP/USB trước bảo toàn hệ số | Software DISABLED/PWMoff không đảm bảo trạng thái trước setup/reset; không làm mất RAM bằng tắt nguồn chung để chụp ảnh |
| ECHO13/17/15/10 | Sơ đồ/ảnh từng divider/level-shifter có trị số; bằng chứng HIGH peak tại phía MCU tương thích≤3.3V. Đo xung trong scope điện áp được duyệt nếu chưa có | Không được đưa5V ECHO trực tiếp vào ESP32-S3; DMM trung bình không xác minh peak. Các kênh boot-disabled không miễn điều kiện điện |
| Motor pump đã tháo | **Đã nhận xác nhận tháo hai dây**, chỉ còn ảnh hai đầu được bọc/cố định, không thể chạmOUTPUT/V+/GND | Không yêu cầu tháo lại/chọn polarity. Cách ly motor không chứng minh đầu dây trần không gây chạm. OFF_LEVEL không chặn servo khi cách ly đạt |
| Recovery/executor/USB route | BOOT/EN tiếp cận được, đúng USB identity; chọn host/interpreter/version/port thực tế và qual ROM/write-verify path trong approved scope | Rollback bytes PASS không chứng minh hardware restore. Windows4.8.1 mới import/source-reviewed; COM thực/USB transfer/runtime chưa qualified. Không mặc định COM8 hoặc chọn Jetson3.3.3 làm flash executor |
| Scope/handback/approval | Người duyệt, thời hạn, current unit/exe/sole-holder trước thao tác, boot/close-tools/USB return, action list và pulse được duyệt | Current PID phải lấy tại handover, không killPID lịch sử4067/3989. Không dùng read-only lease làm quyền flash; chưa có approval mới |

**Ưu tiên lấy tiếp một bộ ảnh servo model–V+/GND–ngắt tải và ảnh cách điện hai đầu motor đã tháo.** Không yêu cầu cân lại, training AI, ARM64, backup lần3 hoặc kích sensor/tải để lấy ảnh. Log exact calibration cần có **trước cả lần mở Serial/reset có thể làm mất RAM**; nếu không bảo toàn được thì dừng, không mở port chỉ để hy vọng lưu kịp.

## Rủi ro outbox riêng — source audit, không chạy lại test

-`POSIX_BIND_DUAL_20261030/bridge/feed_outbox.h`: row QUEUED→CLAIMED được commit trước gửi; `cl_wire_consumed` commit ID trước `writeOnce`; sau return mới cập nhật TX_DONE/UNCERTAIN/BLOCKED. Selector chỉ lấy QUEUED, không tự reclaim CLAIMED/UNCERTAIN; không xóa/reuse consumed ID.
-Existing partial-write fixture được đọc **immutable/read-only**, không test lại: request1=`UNKNOWN_OUTCOME`, queue4=`UNCERTAIN`, consumedID1 còn nguyên. Đây là bằng chứng partial-return path, **không phải crash-injection trước-write**.
-Nếu backend còn sống, timeout/error→disconnect→UNKNOWN; nếu cả hai chết đúng cửa sổ consume-ID/trước-write, source chưa tự chuẩn hóa hết các row cũ lúc startup: request có thể còn SENT/PENDING và row CLAIMED. **Không được gọi đó là FAILED/NOT_SENT hoặc COMPLETE chỉ từ trạng thái queue.**
-Trước resume automatic consumer: producer và Bridge quiescent, chụp snapshot DB, quarantine QUEUED→BLOCKED/CLAIMED→UNCERTAIN, chuyển request chưa-final sang UNKNOWN_OUTCOME bằng transaction được duyệt; giữ consumed/raw RX. Chỉ final đã validate/QUERY đối chiếu mới giải quyết outcome. SQL chuẩn bị ở plan; **chưa thực thi/chưa chứng minh crash-recovery bằng test mới**.
-Đây là **BLOCKED cho resume automatic outbox**, không buộc viết framework mới để thử servo ASCII: đợt manual không deploy/enable automation/feed-link/new Bridge, không gửi FEED. Nếu phát hiện outbox live đang hoạt động, phải quiesce/reconcile có approval trước maintenance; không dừng AI/API để thay thế bước này.

**Kết luận tổng thể: BLOCKED, chưa READY_FOR_OWNER_APPROVAL. Không flash/reset/chiếm Serial/stop service/kích tải.**
