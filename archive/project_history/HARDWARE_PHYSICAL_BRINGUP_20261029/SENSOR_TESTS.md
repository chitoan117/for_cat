# Nghiệm thu5sensor — owner thực hiện, không tự PASS

**Chỉ sau G0–G6 trong `PHYSICAL_EXECUTION_CHECKLIST.md`.** BackupA đangđượcowner
báo chạy: không mởCOM8/serial/reset/capture hoặcstartBridge lúc này. Đọcfilelog
tronghướngdẫn là các bước user thực hiện vềsau, không lệnh đểagent chạy ngay.

Firmware `artifacts/diag_four_ultrasonic/firmware.bin` trước, không benchactuator.
Hoàn tất backup/layout/flash review theoFLASH_AND_ROLLBACK. Servo/pump/buzzerpower
được cô lập. Echo4kênh được levelshift/divider phùhợp; lưu schematic/ảnh/giátrị và
đo mứcHIGH thực. DMM đọc trungbình xung không chứng minh peak≤3.3V; dùng cách đo
phùhợp/oscilloscope nếu cần. LệnhCONFIRM không đo được điện áp.

## Một session/owner serial

```sh
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
T=/home/toan/hardware-kit-20261029/tools
"$PY" "$T/serial_evidence.py" --profile sensors --output /home/toan/NEW_sensor_evidence --seconds 180 --interactive --electrical-reviewed
# Mặc địnhPLAN. Sau review thêm --execute --confirm OWNER_SUPERVISED_SERIAL
```

Tool pause đúngbridge trướcopen, lấy115200 một lần, DTR/RTSfalse, tựTXstatusreadonly
mỗi5s; không bậttriggerkhi khởi động. Consolehiện tại không echoRX liên tục ra màn
hình: raw/records.jsonl được ghi realtime, có thể dùng terminalkhác `tail -f` file
evidence (không mở portthứhai). Gõ các lệnh dưới với prefixSEND, quan sát rawfiles.
`OBSERVE ...` ghi nhận hành động/ảnh/đo owner; không đổi flagphysical. `STOP` dừng
ultrasonic, `QUIT` đóngport/restorebridge. Nếu signal/quitsession khiechođangbusy,
firmware vẫn hoàn tất timeoutbounded; lặp `SEND ultra-off CONFIRM` nếu báoBUSY.

## Boot và PIR

1. `SEND status`: KITfirmwareID đúng, mode`diag_current_hardware`, kitprofile
   `diag_four_ultrasonic`, hardware_verifiedfalse, voltage_physically_verifiedfalse.
   Cả4kênhDISABLED, RTCNONE, actuatoroutputs0; không servo/pump/buzzer hoạt động.
2. Đợi ít nhất60s từ reboot. Banđầu `motion_quality=WARMING_UP`, motion_validfalse,
   motion_stablenull. Sau đó GPIO11 ổn định≥100ms mớiVALID/stablebool. `motion` cũ
   là rawlegacy, không dùng nó thay qualifiedfield. Module thực có thể cần lâu hơn
   60s: ghi observedwarmup, không épsoftware choGOOD khi vẫnchattering.
3. Đứng ngoài vùng, ghi baseline; đi qua vùng PIR, ghi thờiđiểm/đènmodule nếu có/
   motionraw và qualified. Đứngyên/rời vùng, chờmoduleholdtime/retrigger thực tế.
   Lưu ít nhất2chu kỳ, khoảng nhiễu và thời gian settle. KhôngAI/CAT/DOGinference,
   khôngPIRfeedrequest. Nếu không đổi, UNKNOWN hoặc chattering thì giữNOT_VERIFIED.

## Siêu âm: test từng kênh trước multiplex

Không chĩa các transducer đối diện nhau. Dùng mặtphẳng đủ lớn, vuông góc, khoảng
cách đo từ đúng mặt transducer, thước/reference và ảnh geometry. Mỗi điểm giữ
ổnđịnh20–30s, log mọi reading, không chọn riêng các sample đẹp.

| Sensor | Lệnh thủ công | Gợi ý điểm bắt đầu |
|---|---|---|
|HC1 TRIG12/ECHO13|`SEND ultra-select hc1 CONFIRM`|40cm→15cm→40cm|
|HC2 TRIG16/ECHO17|`SEND ultra-select hc2 CONFIRM`|40cm→60cm→100cm, theo mounting|
|JSN1 TRIG14/ECHO15|`SEND ultra-select jsn1 CONFIRM`|50/100/150cm, xác nhận datasheetmodule|
|JSN2 TRIG18/ECHO10|`SEND ultra-select jsn2 CONFIRM`|50/100/150cm, xác nhận datasheetmodule|

Giữa kênh gõ `SEND ultra-off CONFIRM`, chờkhôngbusy rồi chọnkênh tiếp.
JSN blindzone thay đổi theo revision; **không dùng20cm làm mốcPASS mặc định**.
Configured1–400cm chỉ bound của driver, không chứng minh module accurate trong
toànrange. Nếu min module lớn hơn50cm thì đổi điểm xa hơn theo datasheet/đo thực.
Không tự gánHC2/JSN2 thành hopper/watergeometry hoặc dùng phầntrăm chưa hiệu chuẩn.

Cho mỗikênh: đưa/nhấc vật cản, đổi góc/phản xạ có kiểm soát; đo đúng sensorID/pins
và giátrị. Mất echo phải thành distance_cmnull, timeouttrue/TIMEOUT với
measurement_stateNO_ECHO; không0cm hợp lệ. Xung trả về ngoài configuredrange
thànhOUT_OF_RANGE/null. Một reading trongrange vẫn chỉVALID_READING_NOT_PHYSICAL_PASS.
Không chập/rút dây khi đang cấp nguồn; mô phỏngkhôngecho bằngdời target an toàn.

HC1 sequence40→15→40 liên hệ FSMsoftware đãPASS: boot-near không tựarm;
release>30cm liên tục2s,3validsamples5–20cm≤1500ms,20–30cmhysteresis. Kit này chỉ
logdistance/health, **không chạyAI/feedingFSMaction**; không suy physicalAUTO_CATPASS
từ việc đọc15cm. Invalid/timeout/<5cm không là detection hợp lệ.

## Multiplex, OLED và button phụ trợ

Sau khi từng channel đượcselect/review trong cùngboot, `SEND ultra-multiplex CONFIRM`.
Mặc định guard80ms, mỗi channel≥500ms, timeout30ms, không simultaneoustrigger.
Ghi40–60s khi multiplex; so với singlechannel để tìm crosstalk/spuriousreflection.
Owner chỉ thay guard60/80/100 bằng `SEND ultra-guard 100 CONFIRM` nếu cần và ghi
config mới; không gọi đó là electrical/acousticPASS khi chưa códata. Dùng scope/
logic analyzer nếu cần chứng minh timingtrigger thật; hostfakes không thay thế.

OLED đãcóownerdisplayevidence trướcđây: giữlink/ảnhđãcó, không tựyêucầutestlại.
ButtonGPIO21activeLOW/pullup nhấn/thả, debounce/count/dryrunblocked ghi log; không
chofood. Đây là observationphụ, không tự cộng vào5sensorPASS. Dừngultra trướcQUIT.

Kết thúc gửi session.json + rawbin + records.jsonl + ảnh/thước/peakvoltage +
USER_OBSERVED. Bridge connection != validtelemetry != physicalsensorPASS.

## Tiêu chí proposal PASS/FAIL/BLOCKED và repeat worksheet

Trước khi đo, owner ghi module/revision, min/max/blindzone, referencegeometry,
allowed_abs_error_cm, allowed_spread_cm, minimum_valid_fraction vàsupply. Không
biếtmodule hoặcchưachọncriterion→BLOCKED_CRITERIA, không tựbịaaccuracy từdriver.
Freezecriteria cho toànsession; thaycriterion sau khi thấydata phải tạoreviewnote,
không xóapointfail. Dùng form trong `PHYSICAL_EVIDENCE_COLLECTION.md`.

| Sensor | Physical input / repetitions | Expected / proposal PASS | FAIL hoặcBLOCKED |
|---|---|---|---|
|HC1 12/13|40→15→40cm,3cycles,≥20s/plateau|ĐúngID, đo trongvalidrange, mọiwindow đạtcriterion, returnphùhợp; không0cm từtimeout|SaiID/bias/spread ngoàiownerlimits; noecho thànhvalid; electricalchưađo→BLOCKED|
|HC2 16/17|3referencepoints phùhợp, mỗi điểm3windows|NhưHC1, khônggánnhầmrole/RTC|Wrongpins/RTCactivity/crosstalk/missingcriterion|
|JSN1 14/15|Ítnhất3points ngoàiactualblindzone,3windows/point|Đúngmodule/range, error/spread/validrate đạtlimits đãchọn|20cm đượccoilàvalidaccuracy mặcdùngoàirange module; chưarõblindzone→BLOCKED|
|JSN2 18/10|NhưJSN1|ĐúngID độc lập và khôngcoupling vớiJSN1|Reading đổi theo sensor khác hoặcwiringchưađo|
|PIR11|Warm-up≥60s/softwaregate vàactualmodule ổnđịnh;3no-motion→motion→no-motioncycles|Qualifiedfieldchỉvalid sauwarmup/settle; ownerwalktimestamps tươngứng, clear theoactualholdtime|Qualifiedmotionởwarmup, noisechattering false-events; thiếuholdtime/reference→BLOCKED|

MỗiECHO13/17/15/10 phải cómeasuredpeak vàprotectionevidence riêng trướctrigger;
không mộtcheckboxCONFIRM đại diện4measurements. Ghi high/low/VCC/thước/scopefile.
Ba window phải độc lập cóthao tác đổi/repositiontarget, không copycùnglog3lần.
RawUARTbyteslưu nguyên; `distance_cm` firmware là filteredreading, không giảlà
rawphysicalpulsewidth. Scope/logic trace riêng nếu cần chứng minh timings thật.

Faultpoints: nhấc/đổi góc target đểloss echo→TIMEOUT/NO_ECHO/null. OUT_OF_RANGE
chỉPASSfault-handling khi thực sự cóecho ngoài configuredbounds; nếu module chỉ
timeout ở vùngxa, ghi NOT_TESTABLE_CURRENT_SETUP, không bịaOUT_OF_RANGEPASS.
Không rút/chập dây đangcấpnguồn hoặc đưaxung5V vàoESP32 để tạo lỗi. Offlineguard
tests không được thay thế accuracy/modulephysicalevidence.

Sau singlechannel, multiplex3repeatedwindows40–60s, so vớireference/singlelimits;
crosstalk/spuriousvalid hoặc sharedtrigger sai→FAIL/STOPreview. Thiếu scope thì
timingguaranteephysical chưaverified, dù firmware schedule vàhosttests đãPASS.
Toolduration5–300s; dùngNEWsession/windowgroup khi cần, giữ mọitransients, gõSTOP
trướcQUIT. FinalcomponentPHYSICAL_PASS chỉ sauhumanreview, không từfirmwareVALID.

HX711static đãđượcchấpnhận, không thuộc5sensorretestởđây. OLED cũngkhôngauto-retest.
