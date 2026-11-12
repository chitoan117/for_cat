# Ba actuator bench riêng — KHÔNG auto-feed

**Preparation only:** không làm các bước này khibackupAđangchạy. Chỉ saubackup
A/B/layout/bank/rollback/electricalgates đượcownerreview. Source/bin khôngrebuild
hoặc đổi trongmilestone hiện tại; pumpcurrent vẫnINERT, khôngchọnpolarity.

Mỗi image riêng, không simultaneousservo/pump/buzzer. Flash doowner sau backup và
nguồn tải cô lập; imageverify hash, firmID/status đúng, defaultDISARMED/OFF.
Serialtool defaultSTATUS-only. HumanTTY + `--interactive --actuator-supervised`
và explicit `SEND` mới gửi commandcó thể kích. Không pipe script tựchạy ARM/ON.
Stop/timeout là command, không là acoustic/closure/current/flow feedback.

## 1. MH-FMD GPIO2,3.3V ACTIVE_LOW

Sourcegeneric cũ cóACTIVE_HIGH nhưng không dùng trongkit. Image`diag_dog_buzzer`
dùng HIGHoff trướcOUTPUT, LOWon; ackchỉ choACTIVE_LOW, khôngAItrigger/receiver.

1. ModuleđúngMH-FMD3.3V, commonGND; ngắtVCC khi flash/reset. Review quan sáttrước
   củaowner về activeLOW, đo/review logicGPIO2 bootHIGH/OFF và bias module trước
   khi cho phépâm thanh. Chưa chắcpolarity thì giữngắtnguồn, không thửHIGHmùquáng.
2. Owner chạycaptureprofilebuzzer ởhumanconsole sau khiđãreviewnguồn:
   `... serial_evidence.py --profile buzzer --output NEW_DIR --seconds 120 --interactive --actuator-supervised --execute --confirm OWNER_SUPERVISED_SERIAL`.
3. `SEND status`: driver_ack0,tests0/3,phase0; khôngtiếng tựđộng.
4. `SEND buzzer-driver ACTIVE_LOW CONFIRM`: khôngphátâm, chỉownerack;
   `OBSERVE <logicmeasurements/photo/priorpolarityreview>`.
5. Khiđãgiámsát: `SEND test CONFIRM`. Mongđợi2ON200ms, gap200ms; owner nghe/ghiâm
   vàquan sát pin/timing nếu cóscope. ACKACCEPTED khôngchứng minh ngheđược.
6. `STOP`/`SEND stop` commandHIGHOFF tức thì; phase0, khôngâm lặp. Đợi≥60s nếu
   thửlại; max3sequences/boot. Không tựreboot đểtránhbudget. Nếu tiếng kéo dài,
   polaritysai hoặcresetbeep: ngắtVCC, giữNOT_VERIFIED, lưuâm thanh/log.

## 2. Servo GPIO6, nguồn5Vngoài — small unloaded bench

Image`diag_servo_bench`. Ngắt pump5V/buzzer, tháofood/load hoặchorn nếuan toàn;
khôngkẹp tay, tránhchặn trục. Nguồnservo riêng đủdòng/commonGND; ESP32pin không cấp
dòngmotor. Có thể brownout dùfirmwaređúng: ownergiámsát nguồn vàresetlog.

1. Boot: PWMoff,DISARMED,configured0. Khôngchạy từAI/button/web. ĐừngARM khi
   cơcấu cònkẹt hoặc chưakiểm vịtrí. ServoARM **có thể chuyểnđộng ngay** vềcandidate
   CLOSE khiattachPWM; khôngcoi ARM là chỉmởquyềnvôhại.
2. CapturehumanTTY profile`servo` với `--interactive --actuator-supervised`.
   `SEND servo status`, ghi nguồn/noPWMatboot và USER_OBSERVED.
3. Chỉ sau review safe pulse, ví dụ unloadedsmallmotion:
   `SEND servo configure 1450 1550 1500 1550 CONFIRM`.
   Đây là startingexample, không phải góccalibration/confirmedclosure.
4. `SEND servo arm YES`, sauđó nếuan toàn/trong2s: `SEND servo open`.
   One testmove/arm, movementhold250ms rồi candidateCLOSE350ms vàPWMoff;
   armexpiry2s, harddeadline3s, max3arms/moves/boot. Ownerquan sát/video cảmovevà
   shutdown, không chỉACK. Không tựkéo góc45°: knownnominal90/45 chưaproof và
   span500us bị initial100us envelope từchối. Không nới envelope trongmilestone.
5. Nếu an toàn muốnreturn: `SEND servo close` hoặc `SEND servo disarm` command
   vềcandidateCLOSEbounded rồiPWMoff. **Nếu kẹt/khẩn:** `STOP`/`SEND servo stop`
   immediatePWMoff, latchedFAULT, khôngauto-rearm; ngắt externalpower khi cần.
   OFFPWM khôngchắcservo ngừngdòng/đónggate; physicalposition vẫnchưaxácminh.
6. SauSTOP cầnownerreview/reboot/reconfigure, khôngauto-retry. Bàn giao video,
   pulse/current/supplynotes, status trước/sau, lỗi/brownout/khôngmoveđều giữlog.

## 3. Pump GPIO7/F5305S5Vngoài — polarity chưa biết

**Không có pumpactivebin trong4artifacts banđầu. Không đưa pumpON vào bước đầu.**
`diag_pump_bench` làINERT_UNKNOWN_POLARITY, PHYSICAL_ENABLE0/OFF_LEVEL-1;
GPIO7 khôngoutput. HighZMCU không bảođảmmoduleOFF; giữloadpowerngắt.

1. NạpINERTnếuownerđãlàm flashreview; `pump status` phảiDISARMED,commanded_on0,
   modeINERT. ARM/ON bịtừchối; không coiINERTPASS làpumpOFFđãđo.
2. Owner review/dotestmodulelogic bằngmeter/scope vàdummyloadan toàn, motorngắt:
   OFFlevel là0hay1? Inputvoltage phùhợpESP32? Boot/reset/highZbias cógiữOFFkhông?
   Khôngsuy từtênF5305S hoặcchọnactiveLOW/HIGH từphầnmềm. Lưuảnhsơđồ/trace/observer.
3. Chỉ sau physicalOFFreview, điền `OWNER_OBSERVATIONS_TEMPLATE.json` thànhfilemới.
   Buildconditional trênWindows bằng `build_windows.py --pump-off-level 0|1
   --observation OWNER_FILE.json`. Khôngevidence/kháclevel→refuse; khônglưuNVS.
   Conditionalbin/hash/layoutreport tách khỏibaselinekit. Flash-preparation cũng
   cần đúng`--profile diag_pump_bench_active_high|active_low --pump-observation FILE`.
4. Activeimage chỉđược ownernạp saubias/OFFmeasure đúngvariant và powerisolated.
   Chạyreadonly`pump status` trước: `GPIO7_off_level` phải khớpmeasurementfile,
   bootDISARMED/OFF. Driver commandOFF trướcOUTPUT vẫn khôngchi phối thời gian
   reset/before_setup. Ownerđo OFF thậtcảcold/reset/USBconnect, khônglấyACKlàmproof.
5. Chuẩn bịwetflow/priming thật, outlet an toàn, nước tránhđiện; không chạykhô.
   `USER_OBSERVED.water_primed=true` và observer thật trước bậtmanualmode. Capture
   `--profile pump_active --pump-observation OWNER_FILE.json --interactive
   --actuator-supervised --execute --confirm OWNER_SUPERVISED_SERIAL`.
   Tool cũng chặnARM/ON cho đến khi readonlystatus báoOFFlevel khớpfileowner.
6. **Lúc này mới** ownergiámsát: `SEND pump arm YES` rồi shortpulsevídụ
   `SEND pump on 100`. Max500ms, min20ms, armexpiry2s,3pulses/boot,
   ≥1scooldown. Quan sátflow/current/noise/automaticOFF thực tế. `STOP`/`SEND pump off`
   hoặc`SEND pump disarm` commandOFF. Nếu khôngOFF, ngắt nguồn5V ngay, giữFAULT/
   NOT_VERIFIED vàevidence. Không testdài hoặc auto-water/AI.

Mọi USER_OBSERVED là lời khai/measurementfile củaowner, chưa được tool biến thành
PHYSICAL_PASS. Formalacceptance cần review bằngchứng và scope: mộtshortbenchresponse
khôngchứng minh food35g/servofullgateclosure/pumpflowcalibration hoặc productionPASS.

## Worksheet vàdừngkhẩn cấp chung

| Scope | Evidence phải có trước | ProposalPASS sauobservations | STOP/BLOCKED |
|---|---|---|---|
|Nguồn/GND|Board3.3Vlogic, external5V córating/currentheadroom, commonGND, photo/polarity|No unintendedmotion/sound atboot; supply khôngbrownout trongbàiđãthử|Khôngrõnguồn/GND/level, reset/glitch/current bấtthường|
|Buzzer|Measured/reviewed3.3V/ACTIVE_LOW, defaultOFF|2shorttones/timing quan sát, OFF/STOP, cooldown/budget đúng|BEEPboot/âmkéodài/polaritysai; ACKkhôngđủ|
|Servo|Unloaded/mechanicalclearance/safepulses, nguồnngoài đãreview|Smallmove/return/timeouts vàSTOP/PWMoff đượclưu video/trace, khôngpumpIO|Kẹt/chạm/ngườitrongcơcấu, overcurrent/reset; mechanicalclosure chưađo vẫnpending|
|Pump|ActualMCU-sidevoltage vàOFFlevel/bias cảboot/reset, observedfile+meter/scope, primedwetpath|Chỉsauconditionalimage riêng vàownerexplicitmanualpulse: flow/start/stop/current đượcquan sát|Khôngbiếtpolarity hoặcOFFbias, thiếuvoltageproof/priming→khôngactive; dryrun/waternearwiring→STOP|

Giữ accessibleexternalpowercut. Khi kẹt/brownout/sound/flow bấtthường: userSTOP nếu
console cònđápứng, ngắt tải antoàn vàgiữFAULT/NOT_VERIFIED; khôngauto-rearm/retry.
PWMoff/GPIOOFFcommand khôngđủchứngminh dòngmotor/flowoff hoặcgateclosure.
Imageactuator khôngthuộctelemetryproductionprofile; không startBridge đểépvalidframes.

HX711staticmeasurement35g=34.981g, error0.019g đãowneraccepted. Khôngtare/refit/
weightserieslại để tốiưu nó. RAMpersistence vàclosed-loopservo35g làtestintegration
riêng vềsau, không được gánPASS từsmallservomove haystaticweighPASS. OLED dùngprior
displayevidence, khôngyêucầubuild/testOLED mới.
