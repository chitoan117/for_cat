# Một gói maintenance APP-only + servo — BẢN NHÁP BLOCKED, CHƯA THỰC THI

## Gói phê duyệt duy nhất cần hoàn thiện

| Mục | Giá trị/phạm vi |
|---|---|
| Image | `D:\for_cat\REAL_HARDWARE_EXECUTION_20261030\INTEGRATED_MANUAL_CANDIDATE\build_safe_txatomic\artifacts\firmware.bin` —415456bytes |
| SHA256 | `77faf09775e55731b08c511ac852273b9839963c081ebe924035f8f9aecaac93` — đã tính lại MATCH |
| Offset | **CHƯA XÁC MINH/CHƯA ĐƯỢC PHÉP GHI**. Metadata app0=0x10000/size0x640000; chỉ dùng0x10000 nếu actual boot/bank review xác nhận. Bank khác/không rõ→dừng; không tự remap |
| Executor đề xuất | Windows `D:\for_cat\.venv-esptool\Scripts\python.exe`, esptool4.8.1 theo policy đã review; runtime trên đúng board/COM và routeUSB còn BLOCKED. Không cài/đổi tool trong lượt này |
| Rollback | `D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029\web_hardware\rollback_original_app_00010000.bin`,381984bytes/SHA `820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826`; cùng verified bank, APP-only, hardware restore chưa được thử |
| Bảo toàn | Không ghi bootloader/table/NVS/otadata, không erase/factory binary. Lưu exact HX coefficients/context ngoài thiết bị trước reset; APP restore không hồi RAM |
| Hành động dự kiến | Staging/hash; cô lập tải; read-maintenance/bank/security; review GO write; APP write/verify; approved normal boot; manual trial cụ thể; close-tools/USB-return/handback. Không auto food/pump/buzzer |
| Rủi ro | Serial open/reset/USB transfer có thể mất RAM; sai bank/security có thể không boot/không recover; ARM có thể chuyển động; PWMoff không chứng minh cơ khí đóng; app1 trong backup erased, không giả automatic fallback |
| Authority | Người duyệt/thời hạn/board/port/boot evidence/approved pulse: **chưa điền**. Tải servo/buzzer và motor leads cần đủ evidence. Không có quyền write/activation hiện tại |

Đây là một hồ sơ với các mốc dừng: **read scope không đồng nghĩa write GO; write GO không tự cấp quyền chuyển động khi pulse chưa được duyệt**. Chỉ khi các gate trong BLOCKERS_TO_FLASH.md có đủ evidence mới trình owner ký gói cuối. Không phê duyệt vô điều kiện một offset chưa biết.

## Trình tự cụ thể, chỉ chuẩn bị

1. **Trước mọi reset/open/unplug:** lưu exact current accepted offset/factor/mounting/context từ log gốc hoặc persisted record đã được xác minh tương thích. Không dùng approximate offset, không `reference CONFIRM`, tare/refit/save hoặc series cân lại. Nếu không có thì dừng tại BLOCKED.
2. Hoàn tất model/power/GND/cutoff/ECHO/recovery và cách điện hai đầu motor. Tải servo/buzzer tắt/cô lập cho read/reset/flash/boot; giữ nguồnESP/USB cho tới khi đã bảo toàn hệ số. Chuẩn bị hai image/manual helper/rollback ở executor và staging mới, đúng hash; không thay dual/Bridge/Web. Actual COM, path staging Jetson và USB-transfer route phải được xác minh, không mặc định đã upload manual image.
3. **Read-maintenance sau approval:** dùng helper cũ đã review. M là directory maintenance thực sự đã staged/verified, WIN là NEW output. Helper refresh owner/unit/exe/USB tại thời điểm stop, không phải chạy lại qualification. Nó chỉ dừng đúng USER Bridge, không AI/API, một Serial tool tại một thời điểm.

```bash
# CHƯA CHẠY. Cần approval read-scope thật và nguồn/calibration đã đạt:
python3 -B "$M/serial_window.py" --execute OWNER_APPROVED_READ_MAINTENANCE --approval "$M/ACTUAL_OWNER_READ_APPROVAL.json" --output "$WIN"
# Terminal thứ hai, lease còn mở:
python3 -B "$M/boot_capture.py" --execute OWNER_APPROVED_BOOT_CAPTURE --lease "$WIN" --seconds 60
```

USER normal boot/EN chỉ sau phê duyệt, không giữ GPIO0 download khi thu bank. Capture không auto reset nhưng open vẫn có thể glitch. Cần loaded/running partition thật; thiếu offset log thì không flash để thêm status.

```bash
# CHƯA CHẠY: approved ROM read, explicit S3/no-stub, không burn/write:
( set -C; python3 -B -m esptool --chip esp32s3 --port "$PORT" --baud 115200 --before default_reset --after no_reset --no-stub get_security_info > "$WIN/security_info.log" 2>&1 )
RC=$?; printf 'SECURITY_EXIT=%s\n' "$RC"
# Phải xác minh efuse_raw.json là NEW trước lệnh này; JSON gốc giữ private:
( set -C; espefuse.py --chip esp32s3 --port "$PORT" --baud 115200 --before no_reset summary --format json --file "$WIN/efuse_raw.json" > "$WIN/efuse_console.log" 2>&1 )
RC=$?; printf 'EFUSE_EXIT=%s\n' "$RC"
python3 -B "$M/security_flags.py" --source "$WIN/efuse_raw.json" --output "$WIN/selected_security.json"
```

Syntax ROM-read trên Jetson3.3.3 không qualify nó làm flash executor. Đóng từng tool trước tool kế; thu normal boot/bank sau ROM để bind boot mới, rồi close-tools/handback. Token read-lease: `NORMAL_APP_BOOT_AND_PORT_TOOLS_CLOSED`. Không viết flash trong lease chỉ READ.

4. **Mốc GO write:** decode security và review cả old/new image; policy hiện chỉ hỗ trợ verified app0/unsigned-unencrypted/unrestricted/secure_version0. Chốt executor/COM/ROM route; nếu chuyển USB sang Windows, phải chấp thuận việc unplug/reset và cập nhật board/boot/bank continuity sau transfer; thiếu capture/route/tool compatibility→dừng. Không lấy bank trước một boot-selection change làm bằng chứng mới.
5. Tạo review thật từ example cũ, thêm candidate gates/image SHA và calibrated-context/pump-isolation evidence. Sinh argv **offline** bằng helper hiện có; không sửa manifest/generator đã khóa:

```powershell
$C='D:\for_cat\REAL_HARDWARE_EXECUTION_20261030\INTEGRATED_MANUAL_CANDIDATE'
# ACTUAL_OWNER_REVIEW.json/NEW_OWNER_APP_PLAN.json là file mới đã được duyệt, chưa có ở đây.
& 'D:\for_cat\.venv\Scripts\python.exe' -B "$C\flash_plan.py" --review 'ACTUAL_OWNER_REVIEW.json' --build-result "$C\build_safe_txatomic\result.json" --output 'NEW_OWNER_APP_PLAN.json'
```

Chỉ khi `write_argv_available=true`, owner soát lại SHA/port/bank rồi thực hiện argv được xuất. Dạng đã review là esptool4.8.1 explicitS3/115200/`--before no_reset --after no_reset --no-stub`, APP `write_flash --no-compress --flash_mode keep --flash_freq keep --flash_size keep VERIFIED_OFFSET EXACT_IMAGE`, rồi `verify_flash` cùng offset/file. **Không có offset thực được cấp ở tài liệu này; không dùng literal0x10000 từ metadata để chạy.** Generator cũng chuẩn bị rollback/verify argv của original app; không tự thực thi. Qual executor/ROM trước write; lỗi không force/fallback.
6. Write-stage handover chỉ sau GO: lưu original USER Bridge state/unit/exe/hash và current holder; dừng đúng `systemctl --user stop for-cat-esp32-bridge.service`, xác minh fuser free trước một tool. Nếu USB đang ở Windows, Bridge phải giữ released; sau flash/verify, đóng tool, approved normal boot và trả đúngUSB về Jetson. Không reset tự động ngoài action list; giữ tải servo tắt cho tới xác minh boot/status.
7. Manual console staged mới, image hash/flash verify và boot `FORCAT_MANUAL_STATION_20261030_V1`, mode `diag_manual_station`, servo DISARMED/pulse0, pump inert, buzzer disabled. Binary hash receipt mới quyết định image identity, không chỉ banner. Khôi phục exact HX coefficients RAM-only nếu cần/đã duyệt; không NVS write. C là actual staging đã xác minh, approval phải scope `OWNER_SUPERVISED_MANUAL_STATION`, đúng SHA, expiry/approver, chỉ allow_servo, exact reviewed4pulses, power/cutoff/mechanics và pump isolation.

```bash
# CHƯA CHẠY: human TTY, Bridge inactive/portfree; helper không stop service:
python3 -B "$C/manual_console.py" --execute OWNER_APPROVED_STATION_CONSOLE --approval "$C/ACTUAL_SERVO_APPROVAL.json" --image "$C/firmware.bin" --out "$C/servo_trial_NEW" --seconds 120
```

Theo SERVO_PHYSICAL_READINESS.md: SESSION/configure giá trị thật; explicit ARM→OPEN trong2s, tự CLOSE/PWMoff. Tối đa một chu kỳ được duyệt trước; video gate trắng/pulse/status/timestamp, không food. Chỉ thử fulltravel khi nằm trong envelope hiện có. Nếu không đủ/không an toàn, dừng, không nới pulse/reset-loop. Khẩn cấp STOP+ngắt tải; STOP/QUIT latch không tự clear.
8. Đóng console/mọi tool, tải an toàn, approved normal app boot, USBidentity trở lại đúngby-id. Chỉ `systemctl --user start for-cat-esp32-bridge.service` nếu nó vốn active; fuser phải đúng sole current PID. AI/API nguyên service/exe/PID; không restart chúng. Current production Bridge có thể vẫn unsupported manual mode: ghi **service restored nhưng telemetry NOT_VERIFIED**, không deploy Bridge/Web mới để che lỗi.
9. Nếu app không boot/identity sai: dừng để review, dùng original APP rollback tại verified bank trong approved ROM/executor scope, verify bytes rồi normal boot/handback. Không erase/full16MB restore, không sửa NVS/otadata/table, không tự loop. Gửi logs/exit codes/boot raw/video/observer; không yêu cầu thử restore trước để lấy PASS.

## Outbox recovery chuẩn bị riêng trong cùng hồ sơ — KHÔNG THỰC THI

Đợt manual không enable automation/feed-link/new Bridge. Nếu phát hiện một outbox live tồn tại: producer/consumer phải quiescent dưới approval (không dừng AI/API), chụp SQLite-consistent snapshot kể cả WAL, xác minh exact DB/schema và các final chưa ingest trước khi sửa. Nếu không bảo đảm exclusive recovery hoặc snapshot thì BLOCKED. Không dùng file-copy của DB đang chạy. SQL dưới đây chỉ là transaction dự kiến trên **APPROVED_OUTBOX_DB**, không áp dụng mù vào canonical events.db:

```sql
BEGIN IMMEDIATE;
CREATE TEMP TABLE recovery_pending AS
 SELECT id FROM cl_requests WHERE state IN ('SENT','PENDING') AND result IS NULL;
INSERT INTO cl_events(request_id,kind,body)
 SELECT id,'UNKNOWN_OUTCOME_NO_RESEND','{"reason":"OWNER_APPROVED_CRASH_RECOVERY_NO_REPLAY"}' FROM recovery_pending;
UPDATE cl_requests SET state='UNKNOWN_OUTCOME' WHERE id IN (SELECT id FROM recovery_pending);
UPDATE cl_transport_tx SET state='UNCERTAIN',error='OWNER_RECOVERY_NO_REPLAY' WHERE state='CLAIMED';
UPDATE cl_transport_tx SET state='BLOCKED',error='OWNER_RECOVERY_STALE_QUEUE' WHERE state='QUEUED';
DROP TABLE recovery_pending;
COMMIT;
```

Client vận hành phải rollback toàn transaction nếu bất kỳ statement nào lỗi. Không xóa `cl_wire_consumed`, không đổiTX_DONE thành success, không tạo history/final/FAILED giả và không tái QUEUED. UNKNOWN được giải quyết sau bằng final/QUERY đã validate đúng request/boot/origin, không bằng gửi lại FEED. Đây là prepared recovery, **chưa được thực thi/không có crash-test mới**; startup normalization hiện chưa tự động đầy đủ.

**BLOCKED — gói chưa đủ bằng chứng để owner phê duyệt thực thi. Không lệnh thiết bị/service/SQL-production nào ở trên đã được chạy.**
