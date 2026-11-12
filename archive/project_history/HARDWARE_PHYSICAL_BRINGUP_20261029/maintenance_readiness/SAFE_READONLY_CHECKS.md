# USER next: metadata/files only — không bảo trì device lúc này

Sau khi review và USER copy **chỉ thư mục maintenance_readiness mới** lên staging,
chạy trong existing Jetson terminal. Không cần SSH bởi agent/mật khẩu lưu trongscript.

```bash
KIT=/home/toan/for_cat/hardware_diag_candidate_20261029
M="$KIT/maintenance_readiness"
python3 -B "$M/readiness.py"
OUT="$M/metadata_$(date +%Y%m%d_%H%M%S)"
python3 -B "$M/readiness.py" --collect READ_ONLY_METADATA --output "$OUT"
```

DefaultPLAN không gọi systemctl. Collect chỉ `show/cat`, boundedjournal, udev/sysfs,
fuser, `/proc/PID/exe`, existing PASS result và identity filecopies; không import
serial/esptool, không chạy tests, không mởtty. New outputdir0700, không overwrite.
Nếu unitAI/API khác defaults, truyền `--ai-unit ACTUAL.service --api-unit ACTUAL.service`.
SaiUSB, holderskhác, thiếuquyền, thiếuunitfile hoặc currentbinary khôngđúng→metadataNO_GO.
Lưu outputdir và gửi `snapshot.json`, `existing_evidence.json`, relevantrawoutputs.
Rawunit/config files có thể có dữ liệu private; review trước khi gửi.

MetadataVERIFIED chỉ là readinesscủahost, **không phải APPflashGO**. Không cần chạy
lại `verify_transfer`, nativebuild hoặc hashA/B. Sensor/rollbackhash tại executor
là identitycheck bảncopy, không phải physicalretest. Existing native result được
đọc tại đúng pathUSERcungcấp, không tìm/random chọn một runPASS khác.

Windows tool metadata (đã kiểm local, USER chỉ cần nếu muốn lưu output của host):
```powershell
& 'D:\for_cat\.venv-esptool\Scripts\python.exe' -B -c "import sys,esptool; print(sys.version); print(esptool.__version__); print(esptool.__file__)"
```

Existing eFuseJSON đã thu trước đây (không mởdevice):
```bash
python3 -B "$M/security_flags.py" --source /ACTUAL/EXISTING/efuse_raw.json --output "$OUT/selected_security.json"
```
OutputNEW, rawkeyblocks không được in. Missingflag không đồng nghĩa0; policycầnreview.

Nếu cần chuyển file quaWindows: dùngSFTP với StrictHostKeyChecking=yes và xác thực
USER; chỉcopyfoldermới, không production overlay/whole-repo. Nếu auth yêu cầu
interactive, USER dùng client của mình; script không đọc/tìm/lưu mật khẩu.

**Dừng sau collect**, gửi evidence. Không dùng execute flags của serial_window hoặc
boot_capture trước khi OWNER phê duyệt maintenance scope riêng.
