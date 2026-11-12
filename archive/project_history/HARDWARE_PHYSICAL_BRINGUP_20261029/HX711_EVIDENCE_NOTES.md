# HX711 — đo tĩnh PHYSICAL PASS, sai số đã được owner chấp nhận

Hồ sơ hiện hành: **`HX711_ACCEPTANCE.json`**. Quyết định owner29/10/2026:
HX711 + loadcell1kg trên ESP32-S3, DOUT4/SCK5, tôinox đã thử phầncứng thật;
không phải chỉ offline/mock. Không yêu cầu tốiưu thêm hoặc lặp5/10/20/35g/38g.

```text
HX711_PHYSICAL_STATIC_TEST=PASS
HX711_STATIC_MEASUREMENT_PHYSICAL_PASS=YES
HX711_35G_REFERENCE_MEASUREMENT=PASS
HX711_MEASUREMENT_ACCURACY_ACCEPTED=YES
HX711_RETEST_REQUIRED=NO
HX711_CALIBRATION_PERSISTENCE=NOT_VERIFIED
HX711_CLOSED_LOOP_DISPENSE_35G=NOT_VERIFIED
```

## Scope đã nghiệm thu

Giao tiếp HX711 thật, tare tôinoxrỗng, phản hồi raw với5/10/20/35g, đo tĩnh35g
và accuracy của bài thử đã thực hiện. Owner xác nhận35g→**34.981g**,
sai sốtuyệtđối **0.019g ≈0.0542857%**, chấp nhận cho mục tiêu khoảng35g.
Không cần0gerror/absoluteaccuracy và không xem đây là blocker tốiưu cân.

Owner latesttrial: empty-0.009g, added_delta34.990g; returnkhoảng-0.077g;
30s109samples first-0.131398/last-0.122004g, endpointdifference0.009394g.
Endpointdifference không phải fullrange/sigma. Reference-1064.4473counts/g và
offsettarekhoảng-698922.87 được lưu là lịch sử, **không thay hoặc áp lại** bằngtool.

## Đối chiếu log gốc và provenance

Đã thựcđọc4archivephysicalobservations tại `HX711_REFERENCE_PORT_20261028/physical`,
verify artifactSHA trongoriginalsummaries, đốichiếumessages.jsonl và30swindow:
**436samples =4×109**. Means cũ5=4.901414,10=9.819718,20=19.682664,
35=34.582390g; originalwindowPASS theo tolerance của chínhsession đó.
Đây làhardwarelogs thật ở RAMsessionoffset-671054.666666667, **khác latesttrial**.
Original recorder froze30s summary trước finalstatus; tail vẫn giữ trongrawlog,
không được tính đếmlặp hoặc bịxóa để làm đẹpdata. Hash vàtailcounts trongJSON.

Chưa tìmthấy exactrawattachment của latest34.981g/offset-698922.87 tronghaiarchive
local đãreview. Latestnumbers được ghi đúng là **OWNER_SUPPLIED_REAL_HARDWARE_RESULTS**,
quyếtđịnhnghiệmthu thuộcowner; không gán nhầm archive34.582g thành34.981g.
Đây là traceabilityfollowup: attach filelog cũ khi có, **không yêu cầu đo lại**.
Cácendpoint-0.131398/-0.122004 cũng xuất hiện ở archivecontinuous cũ, nên không
dùng việc trùng số làm bằngchứng đó là cùng latest30swindow.

## Scope chưa xác minh, không phủ nhận staticPASS

- Persistence sau reboot/flash: NOT_VERIFIED; calibration/tare từngRAM_ONLY.
- CurrentRAMsauROMresets: UNKNOWN, không giả địnhvẫn còn hoặc tựimportpair cũ.
- Servo cấpfood vàHXfeedbackdừng35g: NOT_VERIFIED; staticweight khôngphải
  closed-loopdispense. Servo/pumpproduction vẫnLOCKED.
- Sau đổi image, xácminhcurrentcontext/persistence bằng quytrìnhtíchhợp riêng,
  khôngreplaytoànbộweightseries vàkhôngtốiưu sai sốđãđượcchấpnhận.

Không flash/reset/serialopen hoặc canthiệpbackupA để hoànthiệnhồsơ. Thống kê
existinglog bằng `analyze_hx_log.py` vẫn làfileanalysis, không tựauthorizeactuator.
Genericsoftware `physical_pass=false` của analyzer/backup khôngđược diễn giải
thành “HX711staticphysicalchưaPASS”. Không sửarawlogs/firmwareprotocol/source.
