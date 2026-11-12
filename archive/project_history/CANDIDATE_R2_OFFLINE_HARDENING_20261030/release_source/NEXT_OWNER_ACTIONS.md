# Next owner actions — laptop now, devices later

## LaptopWindows now
1. ReviewBUGS_FIXED/SAFETY_AUDIT và actualbaseline/fixedlogs. Quy tắc hiện hành
   aim35g, final30–40inclusive; don't reinterpret historicalR2±0.2results.
2. ReviewCHANGESET/diff/newsource manifest/sealresult. Use trustedcopyof
   `tools/safe_release.py` ngoài archive để verify ZIP bằng digest doWindowsseal
   bàn giao. Không chạy module từuntrustedZIP trước verification.
3. Optionalextract vàoNEWlocalreviewdir với`--archive PATH --extract-to NEW_PATH
   --expected-sha256 TRUSTED_DIGEST`. Không overwrite candidateR1/R2.

Relevantrepeatcommands (only when changed; runners keep NEW evidence):
```powershell
$p='D:\for_cat\.venv\Scripts\python.exe'
$c='D:\for_cat\CANDIDATE_R2_OFFLINE_HARDENING_20261030'
& $p -B "$c\tools\safe_release.py"
& $p -B "$c\run_safety.py" --label NEW_UNIQUE_LABEL
& $p -B "$c\run_backend.py"
& $p -B "$c\run_flutter.py" 'ACTUAL_BACKEND_EVIDENCE_DIRECTORY'
```
Nativecore/behavior/extras/release runners refuse existinglabels; original logs
remain evidence. Copyworkspace intoNEWrevision if major sourcechanges, not old
PASSfolders. Don't rerun frozenqualifiedR2suite merely to refreshdates.

## Khi có lại Jetson (NOT NOW)
Ownerreview/source transfer vàoNEWroot riêng, SHA/strictarchivecheck; noSSH/upload
byagent. NativehelperPLANfirst, sau reviewmới:
```bash
H=/home/toan/for_cat/R2_offline_hardening_20261030
python3 -B "$H/tools/native_hardening.py"
OUT="$H/hardening_arm64_$(date +%Y%m%d_%H%M%S)"
python3 -B "$H/tools/native_hardening.py" --execute BUILD_AND_FILE_REPLAY_ONLY --expected-sha256 TRUSTED_SOURCE_MANIFEST_SHA256 --out "$OUT"
RC=$?
printf 'SCRIPT_EXIT_CODE=%s\nOUTPUT_DIR=%s\n' "$RC" "$OUT"
```
Đây là build/filetestscope, không deploy. Returnresult/compilelogs/version/hash;
không bỏWerror. R1PASS/R2locked giữ nguyên; backend/UI targetdeps vàGPU vẫnscope riêng.

## ESP32 / physical stage sau approvalriêng
Completeactualbank/security/eFuse/ECHO13/17/15/10/loadisolation/RAM-loss/recovery
evidence theo maintenance_readiness. Không tự readSerial, reset hoặc stopBridge
để lấpgate lúcchỉ cólaptop. Không thêmWATER_ROI hoặc coiOWNER_CATverified khi thiếu
enrolleddata/model. Closed-loophardware30–40acceptance vàinertia/mechanism cần
testcógiámsát vềsau; staticHXđãPASS khôngcânlại. **APPFLASHNO_GO** hiện tại.
