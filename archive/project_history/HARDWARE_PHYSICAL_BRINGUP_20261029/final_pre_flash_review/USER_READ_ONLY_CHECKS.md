# USER — read-only evidence collection, Bridge giữ nguyên

Chạy từng nhóm trong terminal USER đã đăng nhập Jetson, gửi output để review.
Đây là lệnh đọc file/journal/sysfs/process metadata, không mở `/dev/ttyACM0` làm
data stream. Không chạy native build/replay/verify_transfer lại; ARM64 PASS giữ nguyên.
Không có lệnh stop/start/restart, reset, stty, serial monitor hoặc esptool device I/O.

## A. Xác định đúng scope/unit, PID và USB owner

```bash
UNIT=for-cat-esp32-bridge.service
date -Is
cat /proc/sys/kernel/random/boot_id
systemctl --user show "$UNIT" -p LoadState -p ActiveState -p SubState -p MainPID -p ExecStart -p FragmentPath -p DropInPaths -p ControlGroup -p Restart -p UnitFileState -p NeedDaemonReload
systemctl show "$UNIT" -p LoadState -p ActiveState -p SubState -p MainPID -p ExecStart -p FragmentPath -p DropInPaths -p ControlGroup -p Restart -p UnitFileState -p NeedDaemonReload
udevadm info --query=property --name=/dev/ttyACM0
readlink -f /sys/class/tty/ttyACM0/device
ls -l /dev/ttyACM0
fuser -v /dev/ttyACM0
printf 'FUSER_EXIT_CODE=%s\n' "$?"
```

Hai lệnh `show` giúp phân biệt user/system scope; `not-found` không là service
đang chạy. Nếu cả hai loaded/active, cần map holders/cgroups rõ ràng, không đoán.
`fuser -v` chỉ inspect holders, không dùng `-k`. Exit1 hoặc thiếu PID khi có
permission errors không chứng minh port free. Bridge giữ port là state được mong
đợi hiện tại; không yêu cầu giải phóng port trong phiên review.

Sau khi đã chọn **đúng** scope từ output trên, đọc journal tương ứng (chỉ một):

```bash
# USER scope:
journalctl --user -u "$UNIT" -b --no-pager -o short-iso -n 800
```

```bash
# SYSTEM scope, nếu đó mới là unit thực:
journalctl -u "$UNIT" -b --no-pager -o short-iso -n 800
```

Journal là current Jetson boot, không tự chứng minh latest ESP32 boot. Nếu MCU
đã reboot sau boot lines hoặc Bridge không lưu raw lines, hãy báo UNKNOWN.

Đối chiếu actual executable của PID vừa quan sát bằng đoạn sau; thay số PID thật:

```bash
PID=REPLACE_WITH_OBSERVED_NUMERIC_PID
case "$PID" in ''|*[!0-9]*|0) printf 'Set the actual nonzero PID first\n';; *)
  ps -p "$PID" -o pid=,ppid=,user=,lstart=,comm=
  readlink "/proc/$PID/exe"
  sha256sum "/proc/$PID/exe"
esac
```

Nếu MainPID là launcher, đối chiếu thêm holder PID từ fuser với cgroup; không
suy launcher/interpreter hash là hash của Bridge binary. Permission denied thì
ghi nhận thiếu visibility, không đổi quyền hoặc kill process để lấy output.

## B. Đọc existing ARM64 PASS result — không rerun

```bash
KIT=/home/toan/for_cat/hardware_diag_candidate_20261029
python3 -B - "$KIT" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])/'web_hardware'
found=False
for p in sorted(root.glob('native_arm64_gcc75_r1*/result.json')):
    if p.is_symlink() or not p.is_file():
        continue
    found=True
    v=json.loads(p.read_text())
    keys=('kit_revision','ARM64_NATIVE_TEST_PASS','whole_posix_bridge_compile',
          'host','machine','compiler','dependency_versions','fixture_sha256',
          'food_roi_groups','food_roi_checks','session_stdout','replay_cases',
          'source_sha256','protocol_header_sha256','binary_sha256',
          'serial_opened','camera_opened','services_changed','physical_pass')
    print(str(p))
    print(json.dumps({k:v.get(k) for k in keys},indent=2))
if not found:
    print('No result under this glob; provide the actual existing PASS result path. Do not rerun.')
PY
```

Giữ nguyên run FAIL đầu và run PASS mới; đính kèm đúng PASS result USER vừa nghiệm
thu. Metadata không có timestamp trong JSON thì lấy context owner/run-directory,
không tự tạo ngày giờ giả. Source header R1 đã biết:
`food_roi.h=f07f3ceba1d1668ebeb72ec3aaa4993015338e1d26403c57b9ddd759edfb62aa`.

## C. Tìm file security/boot evidence đã có, không đọc eFuse qua thiết bị

Chỉ inventory thư mục evidence đã biết, không quét root hoặc toàn repository:

```bash
EVID=/home/toan/for_cat/evidence/esp32_backup_20261029
if [ -d "$EVID" ]; then
  find "$EVID" -maxdepth 2 -type f \( -iname '*efuse*' -o -iname '*security*' -o -iname '*boot*' -o -iname '*.log' -o -iname '*.txt' \) -print
else
  printf 'Existing evidence directory not found; provide actual existing log path\n'
fi
```

Chọn một **file text đã tồn tại** và thay `LOG` trước khi chạy đoạn lọc sau:

```bash
LOG=REPLACE_WITH_ACTUAL_EXISTING_TEXT_LOG
python3 -B - "$LOG" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
if p.is_symlink() or not p.is_file() or p.stat().st_size>2*1024*1024:
    raise SystemExit('Need a regular existing text log <=2MiB; no device read performed')
pattern=re.compile(r'Loaded app from partition at offset|RUNNING_PARTITION_OFFSET|'
    r'SECURE_BOOT_EN|secure boot|flash encryption|SPI_BOOT_CRYPT_CNT|SECURE_VERSION|'
    r'DIS_DOWNLOAD_MODE|ENABLE_SECURITY_DOWNLOAD|DIS_DOWNLOAD_MANUAL_ENCRYPT|'
    r'DIS_USB_SERIAL_JTAG_DOWNLOAD_MODE|Chip is|Chip type|MAC:',re.I)
matches=0
for n,line in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
    if pattern.search(line):
        matches+=1
        print('{}:{}: {}'.format(p,n,line))
print('MATCHED_LINES={}; text matches are evidence candidates, not automatic gate PASS'.format(matches))
PY
```

Gửi flags và context board/time của report, không key material. Đoạn lọc không
xác định report có còn hiện hành hay không và không chứng minh thiếu dòng = flag0.
Nếu chỉ có `entry 0x403...` hoặc không có decoded eFuse report thì gate vẫn thiếu.
Không chạy `espefuse summary` / `esptool get_security_info` khi Bridge đang dùng port.

## D. Xác định tool version — chỉ import metadata

Trên Jetson, nếu USER dự định flash tại host này:

```bash
python3 -B - <<'PY'
import sys,importlib.util
print('PYTHON='+sys.version)
spec=importlib.util.find_spec('esptool')
print('ESPTOOL_MODULE='+str(spec.origin if spec else None))
if spec:
    import esptool
    print('ESPTOOL_VERSION='+str(getattr(esptool,'__version__','UNKNOWN')))
PY
```

Nếu executor được chốt là Windows Python3.11 đã dùng trước đây, USER đọc version:

```powershell
py -3.11 -B -c "import sys, esptool; print(sys.version); print(esptool.__version__); print(esptool.__file__)"
```

Các lệnh trên không truyền port/operation, không nâng/cài package. Missing module
là evidence thiếu tool trên host đó; không đổi system Python3.6 để vượt lỗi.

## E. Recovery files trên executor host

Nếu executor là Jetson, đoạn sau chỉ đọc file copy trong staging, không đọc flash.
Đây là kiểm danh tính **file sẽ dùng tại executor**, không chạy lại firmware tests
hoặc đọc backup lượt3. Thiếu file thì báo MISSING và giữ nguyên PASS của bản Windows.

```bash
python3 -B - "$KIT" <<'PY'
import hashlib,sys
from pathlib import Path
root=Path(sys.argv[1])
files=(
 ('artifacts/diag_four_ultrasonic/firmware.bin',400304,'a6ad4b3f6e21c1cfb0714f41f518ca90a75f031705a7bae5a2bb4fa99ebb4b56'),
 ('web_hardware/rollback_original_app_00010000.bin',381984,'820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826'))
for rel,size,expected in files:
    p=root/rel
    if p.is_symlink() or not p.is_file():
        print(rel+' MISSING_OR_NOT_REGULAR_FILE')
        continue
    actual=hashlib.sha256(p.read_bytes()).hexdigest()
    print('{} bytes={} sha256={} {}'.format(rel,p.stat().st_size,actual,
        'MATCH' if p.stat().st_size==size and actual==expected else 'MISMATCH'))
PY
```

Nếu executor là Windows, chỉ cần xác nhận vẫn truy cập được các file đã qualified
ở `D:\for_cat\ESP32_FULL_BACKUP_20261029` và kit; không cần hash lại A/B đã PASS.
Chốt executor/port/recovery route trong câu trả lời, không tự chuyển USB lúc này.

## F. Trả evidence / dừng

Gửi output A, existing PASS result B, existing board-bound boot/security evidence C,
chosen executor/tool D và recovery availability E. Bổ sung existing ECHO13/17/15/10
peak/protection evidence, xác nhận load-power isolation cho maintenance window và
RAM calibration-loss acknowledgement. Việc lắp đặt hoàn tất đã được ghi nhận.

Nếu không có boot/eFuse evidence đã lưu, báo rõ KHÔNG CÓ; giữ NO-GO và dừng để USER
quyết định scope thu thập bổ sung sau. Không bật sensor/servo/pump để lấp evidence,
không build/retest hoặc chạy write command trong phiên review.
