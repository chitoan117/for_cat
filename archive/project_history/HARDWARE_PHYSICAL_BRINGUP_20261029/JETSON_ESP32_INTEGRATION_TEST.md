# ESP32 ↔ Jetson ↔ App — kế hoạch sau physical acceptance

**Chưa thực hiện.** Board hiệnWindowsđọcA, Bridgeinactive. KhôngstartBridge/AI/API,
khôngcopydeploy/flash hoặc mởcamera thứhai trong milestonechuẩn bị.

## 1. Profile/protocol contract trước khi cắm lại

Sauacceptedbackup/electrical/sensors, ownerreview currentimageID/SHA/mode/profile.
Kit`diag_four_ultrasonic` công bốmode`diag_current_hardware` quaASCII/JSON;
M4MODE7/QUAD1/RTCremoved, khôngnormalbinaryfeedingfirmware. Giữappactuators0.
Không dùngdiag_current_hardwarelegacy cóRTC16/17/18 khi đangđấuHC2/JSN2.

Cóhaiwirecontracts riêng:
- KitstationASCII/JSON: schemavalidation/age/values, khôngper-recordCRC16/ACKfeed.
  `ultra-select ... CONFIRM` chỉacquisitionack, khôngelectricalproof.
- FrozenUARTv1binary: A55A,version1,idLE32,command,lenLE16≤256,payload,
  CRC16CCITT-FALSE(0x1021/initFFFF) từversionđếnpayload. ACKcmd6/NACK7;
  ACKreceipt khôngfinalFEED_SUCCESS. KitMODE7 không dùngbinarynormalmain.

Không gửi FEED_REQUEST hoặc binarycommandvàoASCIIimage để “testCRC”. Với binary
captuređãcó từđúngfirmware/phiênđượcphépriêng, `physical_acceptance.py uart-audit
EXISTING_RAW_FILE` chỉofflinecheckCRC/duplicates/ACK vàgiữfeed_success_inferredfalse.
Zero binaryframes củaASCIIcapture phảiNOT_APPLICABLE_ASCII/UNKNOWN, khôngCRC_PASS.

## 2. ReadonlyUART → bridge

Owner saugate mới đưaUSBvềJetson, xácđịnh `/dev/ttyACM0`/by-id/MAC/driver đúngCH343.
Capture1port với bridgeoriginalinactiveđượcgiữnguyên. FirmwareID/profile/status
phảikhớp; all4sensorID/pins/range/timeout/invalid, PIRwarm-upqualified, rawHXcalstate,
locks được so vớiacceptedphysicallogs. Không parserwiden đểacceptmọimode.
Nếu vẫnHX711_REFERENCE thìacceptedframes0 làblockerđúng, không phảiPASSseriallink.

Chỉowner saucaptuređóngport mới explicitauthorize bridge-start theo đúngscope đã
inventory. Agent khôngrestartservice. Kiểm ba số: portconnected, validtelemetry
count tăng vàfresh usable; connected-but-zero phảiBLOCKED. Invalid/timeouts không
được thành0cm hoặcHEALTHY, MCUreboot phảidiscard old state/approach. Không2serialowners.

CRC/ACK/finalstate chỉreviewtheo đúngprofile: ACK, requestPENDING, dryrunblocked,
terminalstatus vàactualmeasurement giữriêng. Không gửi actuator để épterminalSUCCESS.
Hardware feedcompletion chưa thểnghiệmthu trongmilestone này; mọiphysicalPASSgiữpending.

## 3. Jetson AI C++/TensorRT và camera

Trướcđó phải cócontrolleddeployment/ARM64/engineABIacceptance riêng; RCv2 vẫn
staging-only, không deploy từdocumentnày. Readonlyreviewservices/source/buildhash,
enginepath/hash, existingcameraowner vàcachedAIstate. Không chạy detector thử thứhai.
Mộtcapture/inference; framedstdout→soleStateTapwriter; producer_epoch/frameID/
capturetime/freshness/REALnonSIM. NONE làvalidnoobject, UNKNOWN làkhôngđủevidence.
Crash/restart phảiOFFLINE/STALE/CONNECTING rồi freshsame-frame mớiLIVE; khôngoldCATfeed.
OptionalROI chưareview thìFULL_FRAME, không bật để làm đẹpđộchínhxác.

## 4. FastAPI → app read-only acceptance

ChỉGET cácendpoint đãdeployđúngprofile/auth: `/api/status`, `/api/v1/status`,
`/api/v1/health`, `/api/v1/events`, camera/status/MJPEG. So từngphysicaltrace với
`ultrasonic.HC_SR04_1/2,JSN_SR04T_1/2`, aliasesapproach/wateroperational, PIR vàHX.
No simulatedfallback; stale/disconnectẩnoldvalues; schema/provenance khôngrõ→BLOCKED.

Knownremaininggaps phải được nêu, không sửaproduction trongkit:
- QualifiedPIRwarm-up/debounce từfirmware chưa được chứngminh end-to-end qua
  bridge/API/UI; nếuUI chỉrawlegacymotion/CONFIGURED thì khôngcoiqualifiedPASS.
- HX711staticphysicalmeasurement/accuracy đãowneraccepted (`HX711_ACCEPTANCE.json`),
  không cầnretest5/10/20/35g hoặcoptimize0.019g. Persistence vàclosed-loopservo35g
  NOT_VERIFIED làintegrationfollowups riêng, không phủnhậnstaticPASS.
- `bowl_mass.py` gross/baseline/fooddelta chưawiredliveAPI/feedruntime; current
  `weight.grams` chỉhostcalibrationview cóauthoritygate. Khôngtrừchén2lần hoặc
  gọi target35g làactualdispensed. Sauflash kiểmcurrentcalcontext riêng, không
  autoimportpair hoặc lặptoànbộinitialweightseries vìRAM_ONLY đãmất.
- Current stagedbridge source vàactualrunningbridge chưađốichiếutrênNano; zero
  validframes không chữa bằng permissiveparser hoặc bậtREALproviders.

Appscreenshot phảiđốichiếuthờiđiểm/ID/sensorstate, không chỉsốđẹp. Manualreceived/
PENDING/ACK khôngrenderSUCCESS; dryrunactualgramsnull. GiữVIEW_CAMERA khácFEED_MANUAL,
sameoriginHTTPS/lease/viewercleanup, khôngsecret/Funnel. KhôngPOSTfeedđểkiểm quyền;
contractpermissiontests đãPASSoffline, realoperator authreadtests riêng.

## 5. Điều kiện dừng

Sai profile/CRC/schema, acceptedframes0, sourceSIMpresentedREAL, oldmetadataLIVE,
mis-mappedpins, false0cm, rawPIRđượccoilàqualified, calibrationunknownđượccoilà
physicalvalid, actuatorarmed hoặcduplicateexecution → STOP/BLOCKED, giữlogs.
Không actuatorunlock/realfeed/autopump cho đến gatephầncứng+cơkhí+mass/flow và
controlledproductionauthorization riêng; milestone này chỉ chuẩn bị execution.
