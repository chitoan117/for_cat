# Thu evidence — input rõ ràng, không auto physicalPASS

TạoNEWsession trong `evidence/` hoặc `recovery_workspace/`; không sửa baseline
templates/backups/manifest. Không đặtoutput vào fileA đangghi. Mỗi record phải có
observer/timezone/boardMAC/USB/COM/firmwareID/SHA/profile vàconfigtest.

## Các loại bằng chứng riêng biệt

1. **A/B completedread:** originalcommand/transcript/childexitcode/timestamp,
   exactsize/SHA, transportROM, noreset/appwritecontinuityreview. Giữ cảfailfiles.
2. **Backupstructure:** two-passreceipt, actualtable/OTA/imageanalysis, running
   partitionevidence, rollbackextractSHA. CácCRC saukhôngđồngnhau: esptoolROMerror,
   OTAmetadataCRC32 vàUARTv1CRC16. Không dùngmộtloại đểsuyloại khácPASS.
3. **Electrical:** sơđồ/giátrịresistor/levelshifter, peakmeasurementmethod/file,
   pin-specificvalues vànguồn/commonGND. CONFIRM/USER_OBSERVEDtext không thaymeter.
4. **Sensorraw:** `serial_raw.bin`, `records.jsonl`, `session.json`; UARTrawbytes
   không cónghĩa đãđoallunfilteredphysicalecho timings. Ghi thước/targetgeometry/
   moduleversion/validrange/3repeat windows, invalid/loss/reflection/crosstalk.
5. **Actuators:** separatebenchimage/hash, power/OFF/polarity/mechanicscheck,
   video/audio/current/flowtrace; ACK/commandedON/PWMOFF không làphysicalfeedback.
6. **Integration:** correctprofile/protocol, counts/freshness/CRCcapturesnếu có,
   bridgebefore/after, APIJSON/events vàappscreenshot; nofeedmutations.

## Completed externalread record

Chỉowner gọisauA/Bended: `record-completed --label A|B --file COMPLETED_FILE
--log READ_TRANSCRIPT --output NEW_RECORD --exit-code 0 --reader-finished
--device-id ACTUAL_MAC --transport ROM`. Đây làfile-only; khôngpollprocess/port.
Đừng điềnexit0 nếuparentwrapper không cho biếtchildreturncode. Logs phải riêng
cho từngread. Không gọi vớiactivepartial, không lấyprogress100% làmcompletion.

## Probe-map template (copy thành NEW JSON rồi điềnactualoffset)

```json
{
  "probes": [
    {
      "file": "PATH_TO_READONLY_COPY_OF_SUCCESSFUL_PROBE",
      "offset": null,
      "bytes": null,
      "read_exit_code": null,
      "offset_source": "OWNER_REVIEWED_COMMAND_LOG"
    }
  ]
}
```

## Running-partition evidence template

```json
{
  "backup_sha256": "ACTUAL_FULL_BACKUP_SHA",
  "evidence_kind": "RUNNING_PARTITION_OBSERVATION",
  "observer": null,
  "log_file": "ACTUAL_BOOT_PARTITION_LOG",
  "running_app_offset": null
}
```

InspectorOTAcandidate không được chép vàofield này để thayactualrunninglog.
`boot-gate` xácminhlocalimageintegrity vàunambiguousloadedoffset, outputreview
cònrequireseFuse/security/electrical/humanreview; nó không cho phépflash tựđộng.

## Sensor worksheet — tạo CSV/Markdown ngoài baseline

| Session/sensor/pins | Module/validrange | Referencecm/condition | Repeat/window | Rawfile+device/hosttime | Actualmin/max/median/validrate | Error/spreadlimits frozenBEFORE | Ownerproposal PASS/FAIL/BLOCKED | Reviewer/evidence |
|---|---|---|---|---|---|---|---|---|
|___|___|___|1/2/3,≥20s|___|___|___|NOT_VERIFIED|___|

PIR ghi warmup/no-motion/motion/no-motion vàmoduleholdtime, rawlegacy soqualified;
không ép ngườidùngđứngyênrồi suyPIRFAIL vìmodulekhôngpháthiệntĩnh. Buzzer ghi OFF,
twoON/gap/current/acoustic; servo_ARM cũngcóthểmove; pump OFFbias/voltage/priming
riêng. OLED dùngprior evidence đã có, không auto retest. HXstaticphysicalPASS đã
accepted trong `HX711_ACCEPTANCE.json`; khôngretest/optimize. CurrentRAMUNKNOWN,
persistence vàclosed-loop riêngNOT_VERIFIED, khôngđánhstaticFAIL vìRAMmất.

`serial_evidence.py` chỉsauphysicalgates vàUSBtrởJetson; mở1port sauđúngscopeguard,
readonlystatus default. HumanTTY+SENDexplicit mới điều khiểnbench. CurrentBridge
inactive phải đượcpreserve; toolkhông tựstartinactivebridge. Signal/failure vẫn
lưu raw vàrestoreoriginalstate; SIGKILL/powerloss cầnownerkiểmthủcông.

VềOpenCode: gửitextsummary+SHA+recordJSON/logtail/filepaths, ảnh/tracekhi cần;
khôngpaste16MBbinary. Luônnêu softwarediagnostic, bridgeacceptedtelemetry và
physicalacceptance thành3cộtkhácnhau. Giữ mọi lỗi vàchờreview trướcnextgate.
