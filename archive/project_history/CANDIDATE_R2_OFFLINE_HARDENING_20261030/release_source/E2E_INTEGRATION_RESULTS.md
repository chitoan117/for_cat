# Connected offline E2E / SQLite evidence

Một đường actualconnected test (không chỉ cộng unit):

1. `fixtures/transport_script.json` chứa24labelledSIMULATEDsteps; rawwire giữ
   `diag_current_hardware` / `diag_four_ultrasonic`,4IDs/pins/schema và8192framer.
2. Native `tests/stream_bridge.cpp` dùng actualparseTelemetry/LineFramer và hardened
   DiagnosticSession. File/fragments thay Serial; không gọi POSIXserialbridge loop.
3. Pythonwriteradapter ghi nativeJSON vào **temporarySQLite esp32_latest**; kernel
   boot mismatch/restart được inject rõ ràng. Không productionDB.
4. ActualEsp32StateReader/RealHardwareProvider validate/readshape. LabelledReader
   chỉ gắn provenance, synchronousservice adapter thay backgroundclockpoll; AI là
   labelledmockCAT/DOG/NONE/UNKNOWN, không model/TensorRT/camera.
5. CandidateFastAPI ASGI routes/auth/serialization chạy thật. HTTP không bindserver.
6. ActualresponseJSON lưu vào E2Efixture, FlutterMockClient nhận chínhresponse đó;
   widget/controller render thật. Không gọi GPU/physical transport là đã E2E.

24steps gồm partial/truncated, duplicate/frozenuptime, progression, out-of-order,
hostclockbackwards, timeout, reconnectchưa códata, restoredhistorynotlive,
hostbootmismatch và unsafe latch saugood/reconnect. Bad/stale/disconnected không
hiển thị retainedcm/g thànhfresh. Không inferMCUreboot chỉ từ backwardsuptime;
explicitstartup/reconnect cần để nhận epoch mới. Wireprotocol không thêmfield.

Endpoints actual: `/api/v1/status`, `/events`, `/feed/manual`, `/feed/manual/{id}`,
`/sessions/feeding`, feeding/drinking-history và optionalhardware-diagnosticsroutes.
Bridge readonlymode feedmanual503; mockmode nhậnACK=PENDING, finalFEED_STATUS mới
terminal. Wire hiện không manggrams: defaultmeasurementUNKNOWN, không giả35.
SimulationreaderDI chỉ được phép trên explicitMocktransport, không realtransport.

## SQL reliability fixes/tests
Baseline`probe_data.py`: failuretrigger ởeventINSERT để lại ledgerSUCCESS và1typed
record nhưng0successEvent. Fixed: samefailuregiữ ledgerPENDING,0typed,0terminalevent.
Ledger+typed+genericEvent commit cùngtransaction khi SQLiteStore/Repo cùngfile.
In-memory/differentstores không được hứa atomiccross-store. SchemaVersion2 vàtables
giữ nguyên, chỉJSONrecordfieldsadditive; không productionmigration.

Idempotentterminal once, conflictingretry reject, restartPENDINGkhôngresend,
restartfinal giữactualgrams, boundedqueue2req/third503, DBbusy80ms/tempjournal200ms,
2connectionfirst-writer-wins, UTCtimestamps, eventrollback và journalidempotency
đã test. ObservationIDs chỉ idempotent trong256retainedjournalrows, không claim
durableunboundedledger. Drinking thiếuevidence không được materialize.

Counts:22cases ởbackendrun112615;5dataextras ởpython_extras (cùng12prefcases);
nativeScript24snapshots là một phầnconnectedE2Ecase, không cộngthành24pytestcases.
Adapterfaulttests là SIMULATION, không proofrealwire/35gphysicalsuccess.
