# Backup acceptance — chỉ SAU khi A đã kết thúc

**CURRENTUPDATE:** A/B đãcompleted, mỗi16777216bytes vàdirectSHA
56a04d58…6d9a8e16 matchingPASS. Ownerterminalmarkersđãchấpnhận, khôngthirdread/
oldLASTEXITCODE. `web_hardware/accepted_backup_pair.json` và
`web_hardware/backup_and_contract_review.json` làprimarycurrentevidence.
Các mụcHold/exitlogbên dưới làhistorical/generalguard cho readchưaxácminh, không
làyêucầulấy lại dữliệu củaA/B đãcomplete. Runtimebank/electrical/physicalrestore
vẫnNOT_VERIFIED; noAPPflashauthorization tựđộng.

## A. Hold và kết thúcA

- [ ] Không canthiệp PID17448/10604, không COM8/USBreset/monitor, không Bridge start.
- [ ] Terminal trảprompt; ghi nguyêncompletion/error và actualchildesptool exitcode.
- [ ] Chưa có FULL_BACKUP_READ_PASS hoặcexitkhôngrõ→BLOCKED, khôngstat/hashactivefile.
- [ ] Parent/child làcùngmộtjob; không khởi động “bản thứhai” đểtăngtốc.
- [ ] `--no-stub` hiện tại làROMread. Không thaytransport hoặcoptions khiđangchạy.

`physical_acceptance.py` làFILE-ONLY, khôngthựchiệnserial/subprocess, khôngtìmPID/
openCOM/readFlash. `record-completed` kiểmowner-finished+knownexit0 **trước**
đụngfile. `.partial` chỉ làtên: saukhiđãfinish fileđúngsize/hash vẫn cóthểrecord
readonly, không cầnrename hay overwrite để đượcaccept.

## B. AcceptA rồi mới lập B

- [ ] Actualfile16777216bytes, stableSHA (size/mtime không đổi trong lúc hash).
- [ ] Logriêng của lượtA cótool4.8.1/S3/MAC vàfullreadcompletion; khôngtrộnloglỗi cũ.
- [ ] Exitcode0 thực củaesptool, không dùngonlyprogress100%/PSprompt/parent0 khôngrõ.
- [ ] GhiNEWrecordA, không ghi vàoactivebackupdir/file, không sửaoriginalA.
- [ ] LưudeviceMAC, COM8/CH343, ROM/--no-stub, originalargv, started/completedtime.

Sau khiAđạt, `plan-b` mới inREAD-onlyargv choNEWBoutput. Plan giữROM/--no-stub,
115200/explicitS3/16MB, before/afterno_reset; khôngexecute. OwnerreviewROM/power/
USB trước khi tựlàmB. Không dùng STUB/chunktool cũmộtcách tựđộng vìA làROMfullread.
Không đổiPythonhệthốngJetson; Windows3.11/esptool4.8.1đãcó thì khôngcài/buildupgrade.

SauB: exit0/fullsize/stableSHA/MAC/logriêng; không dùng cùngfile/hardlink hoặc
cùnglog làmhai lượt. NếuA/B khácnhau thìBLOCKED vàgiữcảhai. CóthểNVS/appđãghi
giữareset hoặcreadkhôngổn định; khôngbỏ vùngkhác, chọnlượtđẹp hoặcpadbytes.
ROMcontinuity/noapplicationwrites phảiownerreview. Two-passreceipt chỉ chứng
minhlocalconsistency của cácfileevidence, không physicalsensorPASS hoặcbootproof.

## C. Công cụ offline và input contracts

SauG0/G1, dùng `tools/physical_acceptance.py --help` đểxemargs; cácaction:

| Action | Input / output | Không làm gì |
|---|---|---|
|`record-completed`|labelA/B, completedfile/log, knownexit0, reader-finished, MAC, ROM → NEWrecordJSON|Khôngđọcfile nếuchưaownerfinished|
|`plan-b`|completedrecordA, NEWBfile, Pythonpath/COM → argvplan|Khôngexecuteread/reset|
|`compare`|completedrecordA/B +ownerROMreview → NEWtwo-passreceipt|Khôngghéppad/overwrite|
|`compare-probes`|fullbackup/receipt +explicitprobe-map → rangeSHAcompare|Khôngsuyaddress từtênpart_00|
|`inspect`|acceptedfullfile/receipt → table/app/OTAanalysis|Khôngđọcboard/efuse hoặc chọnbootbank|
|`boot-gate`|actualrunningpartitionlog+observer+backupSHA → reviewrecord|KhôngchuyểnOTA/boot/reset|
|`uart-audit`|existingrawbinaryfile → frame/CRC/dedup/ACKaudit|KhôngTX hoặcFEED_SUCCESS|

Completedlog có `FULL_BACKUP_READ_PASS` hoặc dòng `Read 16777216 bytes at0x0` và
identity; partial/errorlog bịtừchối. Nếustdoutchưađượcsave, ownercopycurrentread
transcript sau khiended thànhNEWfile, ghi rõ manualtranscript provenance.

## D. So sánhJetsonprobes vớiWindowsbackup

Readonlycopy từngprobe vàlog sangNEWfolder sau khiA/Bcomplete; khôngoverwrite
`/home/toan/for_cat/evidence/esp32_backup_20261029`. Manifestprobe phải ghi:
`file`, `offset` nguyên từcommandlog, `bytes`, `read_exit_code=0`,
`offset_source=OWNER_REVIEWED_COMMAND_LOG`. Cótemplate ởevidencecollection.
Tool soSHA toànrangevớifullbackup, không sửa cảhai. Kiểm vùng0..1MB,1..2MB,
0x200000,0xFC0000 theo đúng lengthđãđọcthànhcông; không dùngCRC-failedfile.
Mismatch→BLOCKED_REVIEW; không mixold/newdata. NVS cóthểđổi nếuappchạy giữa các
snapshot; đó lànguyênnhân cầnreview, không lýdo tựbỏkhácbiệt đểapproveflash.

## E. Layout/bootloader/OTA và activebank

Inspector tìmactualsectorMD5-valid partitiontable; khônggiảđịnh0x8000/newlayout.
BootloaderS3ROMoffset0 và appregions đượckiểm segmentbounds/XORchecksum/appendedSHA
localbytes. Signing/encryption/eFuse/bootloaderconfiguration chưađượcxácminh bởi
hashparser. Invalid/khôngrõ/multiple-tablecandidates→BLOCKED; khôngforceflash.

OTAcopies đọc theoactualdata/ota partition (hai4KBsectors), reportota_seq/state/
storedCRC/computedCRC và candidate theo sequence. CRC32little seed0xffffffff
đối chiếu ESP-IDF5.5.5 otatoolsource; không chạyscriptotatool thật vìnó có thể mở
port. Invalid/aborted/new/pending/undefined đều cầnreview. Candidate khônglàactive
runningbank: bootloaderfallback/rollback/security cóthểchọnkhác.

Gateactualbank cầnactualbootloader loadedpartition hoặc RUNNING_PARTITION_OFFSET
log/observer boundSHAfullbackup. ROMvirtualentry/loadRAMaddress khôngđủ. Đãthêm
`--running-partition-review` choflashplan; receipt+integeroffset đoán khôngcònđủ.
Nếuoldfirmware/log khôngxuấtactualoffset, giữBLOCKED; khôngnạpimagekhác đểtìmhiểu
bank trước khibackup/rollbackđượcreview.

HX711staticmeasurement đãphysicalPASS/owneraccepted, không đổi thànhpending vì
RAMcalibration mất. Phần chưaverified làpersistence vàclosed-loop35g; không dùng
backupacceptance đểđòi lại bộquảcân hoặc giảm thêm0.019gerror.

## F. Rollback/APP-only — chưa được phép lúc này

- [ ] A/Breceipt/fullSHA, oldprobecomparisons vàuniqueactualtable đượcreview.
- [ ] Actualrunningbank, validlocalapp/bootimage vàsecureboot/encryption context rõ.
- [ ] Tablecompatiblevớinewimage; firmwareMỚIsha a6ad…ebb4b56.
- [ ] Originalactiveapppartition extract vàoNEWfile/hash, rollbackverifyplan rõ;
      full16MBbackups vàlogs lưuởnơian toàn. RAMtare khôngnằmtrongflashbackup.
- [ ] Actual4ECHOvoltage/powerisolation/commonGND cóevidence; serviceownership kếhoạch.
- [ ] Owner cùngChatGPTreview rồi mới cấpAPP-only command. Generator làplanonly.

Nofullflash/eraseNVS/boot_app0/partitionrewrite. Nếulayoutbankkháchoặc rollback
chưa rõ→BLOCKED. Không khôi phụcBridge hiệninactivehoặcthực hiệnROMread khác bâygiờ.

SourceCRC reference: https://github.com/espressif/esp-idf/blob/v5.5.5/components/app_update/otatool.py
