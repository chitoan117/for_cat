# Evidence matrix — authority và gap

VERIFIED = artifact/source đã đối chiếu local hoặc kết quả qualified có record.
OWNER_CONFIRMED = USER-provided remote output/assertion, không giả agent SSH đọc.
NOT_VERIFIED = còn thiếu evidence; NO_GO = điều kiện chưa cho bước có tác động.

| Evidence | State | Nguồn / hành động tiếp |
|---|---|---|
| A/B16MB SHA56a04d58… | VERIFIED/carried forward | `web_hardware/accepted_backup_pair.json`; không lượt3 |
| Old app381984/SHA820cdeec… | VERIFIED bytes; remote OWNER_CONFIRMED | local rollback record; remoteMATCH do USER |
| New app400304/SHAa6ad4b3… | VERIFIED bytes; remote OWNER_CONFIRMED | layout.json + USERremoteMATCH |
| Windows3 firmware Verified=True | OWNER_CONFIRMED | USERmessage; không tự đặt tên bản thứ3 chưa được nêu |
| ARM64 native result true/exit0 | OWNER_CONFIRMED | Exact existing result path trong CURRENT_STATUS; collector chỉ đọc file đó |
| Native checks115/17/26/fullbridge | OWNER_CONFIRMED PASS | Không retest |
| SFTP29 / Windows590 | OWNER_CONFIRMED + existing locked evidence | Không rewrite checksums |
| HX static/35g | VERIFIED prior OWNERacceptance | HX711_ACCEPTANCE.json; không cân lại |
| WindowsPython3.14.3/esptool4.8.1 | VERIFIED local metadata | Import version/path thành công; không devicevalidation |
| JetsonPython3.6.9/esptool3.3.3/espefuse.py | OWNER_CONFIRMED | Chưa đọc installed remote source; upstream3.3.3 được review |
| USERBridge unit/exe/by-id/PID3989/soleholder | OWNER_CONFIRMED at prior observation | `readiness.py --collect` refresh PID/USB/holder/units; không dừng service |
| AI/API active | OWNER_CONFIRMED at prior observation | Collector mặc định for-cat-ai/api units theo qualified source; nếu khác tên thì USER chỉ rõ |
| Hardware assembly | OWNER_CONFIRMED complete | Không tự là voltage/power proof |
| Current loaded/running partition | NOT_VERIFIED / NO_GO | Boot capture of actual app/latestboot hoặc existing runtime API esp_ota_get_running_partition; hiện chưa có command đó |
| Security/eFuse/antirollback | NOT_VERIFIED / NO_GO | FutureapprovedROMgetsecurity + summary, board identity/time binding |
| Four ECHOpeak/protection | NOT_VERIFIED / NO_GO | Existing measurements/photos GPIO13/17/15/10<=3.3V |
| Servo/pump/buzzer power isolated | NOT_VERIFIED / NO_GO | Explicit owner physical condition; LOCKED không đo được OFF |
| HX RAM-loss ACK | NOT_VERIFIED / NO_GO | Reset/USB transfer mất tare/cal RAM; backup/app restore không hồi phục |
| ROM recovery/security acceptance | NOT_VERIFIED / NO_GO | BOOT/RESETroute + fuse restrictions + old/newimagepolicy |
| Hardware rollback | NOT_VERIFIED | Không yêu cầu thử restore để làm preflight; phải review recovery feasibility |

## Tool/source findings
- v3.3.3 **có ESP32S3ROM / chipID9**, `get_security_info`, ROMread; không được nói
  unsupportedS3 chỉ vì version cũ. `get_security_info` in raw flags/counter/purposes;
  không đủ để kết luận antirollback hoặc loadedbank.
- Cả3.3.3 và4.8.1 CLI có thể connect/reset/upload RAMstub trước operation. Explicit
  `--chip esp32s3 --no-stub` cho futuresecurity read tránh uploadstub; không làm
  thao tác đó thành passive read/no-reset. ROMcommand vẫn có volatile setup.
- 3.3.3 `espefuse.py summary` **không có positional field filter**; fullJSON có thể
  chứa sensitive data. Lưu private rawfile, chỉ gửi output `security_flags.py`.
  4.8.1 hỗ trợ `summary FIELD...`. Cả2 espefuse không có `--after`; cần normalboot
  handback riêng, không giả là summary tự trở về app.
- Prior3.3.3 ROMread error ở0x200000/stub-tail là observed old failure, không phải
  proof hardcoded2MBsize limit. Không đọc16MB lại. Chưa qualify3.3.3 làmflash executor.
- Windows3.14.3/4.8.1 importPASS, sourcefeaturespresent không chứng minh mọidevice
  operation tương thích runtime; chưa tự nâng/hạ/install package. Nếu3.14 có lỗi
  thư viện, owner chọn separate3.11+4.8.1 env sau review, giữ nguyênenvđãcó.
- Không cài4.8.1 vào systemPython3.6. Jetson3.3.3 đủ để chuẩn bị read-security scope
  bằng reviewedROMsyntax; restricted mode có thể chặn register/eFuse read→NO_GO.

Source references (read-only):
`https://raw.githubusercontent.com/espressif/esptool/v3.3.3/esptool.py`;
`.../v3.3.3/espefuse.py`; `.../v3.3.3/espressif/efuse/base_operations.py`.
Local4.8.1: `.venv-esptool/Lib/site-packages/esptool/{__init__,cmds,targets/esp32s3}.py`,
`espefuse/{__init__,efuse/base_operations}.py`, `efuse_defs/esp32s3.yaml`.
New sensor secure_version0: existing `build_logs/diag_four_ultrasonic_image_info.log:48`.
