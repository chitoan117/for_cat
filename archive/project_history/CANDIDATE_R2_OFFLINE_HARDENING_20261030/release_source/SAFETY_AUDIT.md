# Controller safety audit — serialized owner contract

Đọc đầy đủ actualR2 `dispense_bench.h`, không chỉ tests. Baselinehash
`ce1ae5404be0c1be0ff600b39ab656bb372f6ba5963bb0f9a96d0acc185814e6`.
SourceR2 không bị sửa. Deterministic baselineprobes lưu trước fix/userpolicyupdate.

| State | Hardening invariant |
|---|---|
| DISARMED | Config hợp lệ và fresh/calibrated/healthy observation trướcARM |
| ARMED | Close-only; budget/5sexpiry; start phải cùng calibrationgeneration |
| WAIT_BASELINE |4freshdistinctordered samples; stablewindow;10s/60stimeouts; chưa mởpulse |
| MEASURE | Latest qualifiedraw upperguard + stableguard; no stale/conflicting sample; không dừng vì chỉ đạt30 |
| OPEN | Boundedpulse; latest≥35 đóngđểsettle; >40fault; invalidsensor/calibration/time abort |
| CLOSING | Closeholddeadline không bịcallback kéo dài; faultlatch before external effects |
| SETTLE | PWMoff/settlewindow trước finalmeasure; không thêmpulse khi aim đã đạt |
| COMPLETE | Aim đã chạm35, settledmass30–40, sensor/cal/time vàjournal thànhcông; không mass-onlySUCCESS |
| FAULT_CLOSING | Latchedreason/epoch; latecalls không resurrectstart/COMPLETE; compensatingclose sau cancelledopen |
| FAULT | Khôngpulse; pendinginspection; rebootpending không tự arm |

## Bugs tái hiện
Baselineunfresh36 mởpulse; backwards4timestamps thànhCOMPLETE; journalabortcallback
bị COMPLETE/WAIT_BASELINE ghiđè; lateopencallback trở lạiOPEN; changedcalibration
arm→start được nhận. `baseline_safety/{probes,tests}.log` vàresult ghi actualoutcomes.
Fix: orderedobservation/clock tracker, requirefresh choARM/start/pulse, conflicting
samestamp reject, generation/effectguard, faultstate trước virtualcall, pendingID
reservation và re-markinspection sau cancellation trongjournalclear.

## Owner policy35±5
Settingscho phép tolerance5, projectfixtures dùngaim35/tol5. Controller seek35,
không lấylowerband30 làm cutoff. Khi latestqualifiedmass đạt35 thì ngưngpulse và
đóng/settle. Final30–40 chỉ là một điều kiện; flagsfault/calibration/generation/
timeouts/journal vẫn bắt buộc. Persistent30 trướcaim không COMPLETE (no-progress
fault); targettouch35→settled30 có thể hợp lệ. >40 không mởpulse, TARGET_OVERSHOOT
hoặc hardmaxFAULT. 40inclusive không thêmpulse. 38/40 giữ actualgram, không sửa35.

Float: no arbitraryepsilon widenband. Nativefloat32nextafter40 up bịreject, nextafter30
down bịreject; APIdouble edges cũngtest. Quantization/loss trước khi sample vào
float32 không thể phục hồi bằng code; không tuyên bố resolutionhardware thực.

## Limits / không phóng đại
- Guards giải quyết synchronousreentrantcallbacks, **không phải mutex**. Adapters
  phải single-owner/serialized, boolfailure/no-throw; trueconcurrentISR/thread access
  chưa hỗ trợ hoặc qualify. Không gọi đây là formalexhaustiveraceproof.
- Pendingmarker restoration khi cancellation là best-effort; NVS/powerloss durability
  cần physicalvalidation. Outputofffailure không chứng minh cơ khí đã đóng.
- COMPLETE là settledterminal của transaction tại thờiđiểm đó; không bảo đảm bát
  không đổi về sau. Lateinertialfood saufinal, sensornoise/contact và settling thực
  chưa nghiệmthu; cần separatehealth/anomaly/physicalpolicy, không sửa history cho đẹp.
- Reasonordinals/wirecommands giữ nguyên; privatecontrollerlayout đổi, rebuildall,
  không linkR2binary với hardeningheaders. Không build/flash embeddedimage trongphase này.
