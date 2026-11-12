# Release/source readiness — not deployment approval

BaseGCC75_R2 remainslocked, manifest3c9d7ffe… / ZIP64931aa7…; R1and590kit unchanged.
This is **R2_OFFLINE_HARDENING_PM5**, not R3. Newprivatecontrollerlayout/state and
sessionrestart semantics require rebuildingallunits; don't mixR2binaries/headers.
Wiremode/profile/schema/8192bound/pins/commands unchanged. API mass/freshnessfields
are additions; client profileguardrequiresnew±5package, legacystrictclients needreview.

## Packaging implemented/tested
`tools/safe_release.py`: defaultPLAN, boundedread-onlyverify and explicitNEWdir
extract. Validateall immutablearchivebytes **before creating destination**. External
digest mandatoryforarchive/extract. Exactmember/file set, SHA/CRC, duplicateJSON,
traversal/absolute/ADS/DOSdevices/casealiases, Unixsymlink/dir/encryption, file/total/
memberbudget và existingdir refused. Windowsfilesystem symlink/junction checks are
implemented; tests cover ZIPsymlinkmetadata, not privilegedjunctioncreation.

41unique release/tooling tests PASS:35initial,2native-default/outputguards,4new
console/superscriptDOSnames. Lasttargeted20 includes16repeatnamecases; do not sum
35+2+20. R2extra-filebaselinePASS preserved. Positiveactualsealedsource archive is
also roundtripped bysealtool; no code from testedmaliciousarchives executes.

Limits8MiBcompressed/1MiBperfile/16MiBexpanded/256payloadfiles. No binaries/objects/
firmware/database/backups; partialextractfailure retained inNEWdir, never overwrite.
InputsWindows paths only inprovenancemetadata, not nativebuild dependencies.
Flutterclosure nowrelative, source-snapshotpinned. Backend requires modernPython/
FastAPI/Pydantic; not imported by Python3.6nativeowner runner.

## ARM64 future readiness
`tools/native_hardening.py` defaultPLAN. Future explicitBUILD_AND_FILE_REPLAY_ONLY
requires actualLinuxARM64/GCC7.5.0, trustedmanifestdigest, existingpkg-configjson-c/
sqlite3, NEWdirectchild`hardening_arm64_*`. SequentialO1/strictwarnings, noinstall.
Buildnewfiletests +wholePOSIXBridge; executefake/filetests and BridgedefaultPLAN /
negativeDOGwarning only. NoLiveSerial/camera/services/actuator. Sourceintegrity before/
after, compiler/deplogs/binarySHA/result kept. StaticPython3.6grammar checked onWindows,
**ARM64runtime/GCC7.5 not verified**. No field promoted by WindowsPASS.

Currentblockers: R2andhardeningARM64NOT_RUN, targetruntime/ABI, realowneridentity,
physicalsettling/accuracy/calibration/powerloss/recovery; allpre-flashbank/eFuse/
ECHO/power/RAMmaintenancegates unchanged. APPFLASHNO_GO regardless softwarePASS.
