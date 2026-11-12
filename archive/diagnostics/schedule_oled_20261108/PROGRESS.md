# Schedule/OLED continuation — 2026-11-08

## Installed

- Jetson bridge updated from `edd211f68634c85f30ca86cecfadfa73f0ba53523082e326913a49aebb9b7604` to `cdc7aef5a535f53b1d9e304ec55aba237ebdcda7dd979bb33699080c3fac7fba`.
- Fixed startup normalization consuming pending scheduled requests before any MCU acknowledgement. New restart tests reproduced failure before patch, then passed.
- Added verified system clock gate. This boot was initially at 2026-11-06 16:34, triggered a16:35 owner slot, then NTP jumped to2026-11-08 11:56. Gate now waits for actual `timedatectl status` synchronization each new boot. It retains confirmed time offline and over bridge restarts within the same boot, provided wall and monotonic time remain continuous. Clock jumps invalidate trust until reconfirmed. API receives true/false time validity; UART scheduled delivery checks again.
-14 bridge/clock tests passed locally and on Jetson. SQLite and bridge source backed up in `/home/toan/for_cat/evidence/schedule_oled_20261108` before install. No owner plans changed.
- Existing worker slot migration and firmware unchanged, already deployed Nov6. No firmware reflash needed Nov8.
- Synced `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino` to deployed source, after guarding old source hash and backing up to `before/esp32.ino`. New source SHA256 `9e80c627543040aee6282753c564df5bf7bc7d53d435b24f0391caa2fb962b89`; binary app hash remains `f97d42d346bfd7957fec1f38c5e0e9bde17e9802a1b38490d2411edfcf65deab`.

## Hardware observations and live test pending

- Initially HX711 unavailable and all ultrasonics timeout. User confirmed hardware fully connected; subsequently HX711/E1/E2/D2 recovered. D1 still timeout. User deferred water/pump commissioning previously.
- Camera absent from USB enumeration and no `/dev/video*`; AI service waits normally, OLED says FAIL. Real CAT/DOG OLED confirmation remains pending camera reconnection.
-20-second scale trace12:04:51–12:05:10 showed near zero (-.23..+.09g), READY, tare=-695205.8666666667, factor=-.000945082600219258.
- User confirmed empty bowl/correctly closed gate/food available and beside machine. First attempt to create test schedule aborted before POST because scale had become~-4.45g. **No test schedule created.**
- Agent then tared after owner empty-bowl confirmation, but failed to reject a subsequently changed negative load. Pre-tare observed -25.33..-25.40g; tare changed to -668340.6, then load jumped+25g during observation. This tare is not accepted as valid zero. Agent acknowledged and asked fresh confirmation: place EMPTY bowl on scale, hands off, leave in place about2minutes. Must correct zero with bowl in place before any test feed. Factor unchanged.
- `tare_empty_bowl.py` now checks load expected near0 or22..28g (known shifted zero after bowl replacement), stability, preserves factor and verifies post-tare15samples. **Do not run until fresh owner confirmation of empty bowl staying in place.**
- Once confirmed, run updated tare script then `live_schedule_test.py` immediately in sequence to minimize delay. Test creates unique temporary future35g plan viaAPI; monitors worker/UART ACK/terminal result; finally soft-deletes its own test plan even on errors, with SQLite fallback. Existing owner plan unchanged. This is a real actuator test; owner has already authorized after physical preparation. Do not fabricate success or final35g accuracy from ACK alone.
- Last read-only servo query: estimate UNKNOWN after restart, inspect_lock=0,moving=0,900/1450ms,1350/1600us. Once latest owner closed-gate confirmation is valid, test script sends inspect_ok to record CLOSED estimate (no movement).

SSH remains `toan@server-jetson.local` with key `C:/Users/chito/.ssh/opencode_jetson`, HostKeyAlias192.168.123.13. Actual current LAN IP from logs192.168.123.14; use127.0.0.1 for remote API. All3 services active and enabled.

## Live test completed12:13 — update supersedes pending notes above

- Owner freshly confirmed EMPTY bowl kept in place. Retare succeeded: tare_counts=-695392.9333333333, grams_per_count unchanged -0.000945082600219258.15 after-tare samples-.05..+.26g; kept stable throughout test. Invalid prior shifted-zero was corrected.
- Test plan `schedule_proof_20261108_4e788f80`, due2026-11-08T12:13:00+07:00, request `schedule_fce28e158ccc300319730235261fbe396cf6c02b3393a650`.
- Worker committed12:13:00.223, bridge sent exactly one feed_once, MCU ACK ACCEPTED, logged GPIO6 open1350us900ms, waited25s; scale increased only~.13g. At12:13:26 timed reverse1600us1450ms, then neutral at12:13:27. MCU result FAILED measured_at_close_g=.126; this is an honest failed dispense, not successful35g.
- Test plan soft-deleted in finally; owner plan list verified unchanged. Full local report `schedule_proof_20261108_4e788f80.json`. Do not rerun this plan or ID.
- Owner observed **Servo does not turn**. Thus schedule path now proven through MCU command; real PWM electrical output, servo supply and physical wiring still need diagnosis. Source PWM LEDC returns no error, usesGPIO6 consistent with PCB;50Hz14-bit,1350/1600/1500us. No other pin6 owner in running loop found. Log is not electrical measurement.
- Asked owner to measure supply at servo red(+)/brown-or-black(GND) connector and confirm correct SERVO PCB port. Awaiting voltage reply; no further actuator commands sent.
- Last physical gate confirmation preceded this test; user reports no movement, but do not fake alignment if later physical state is uncertain. No new flashed code since Nov6, no mechanism tuning changes Nov8.
- After successful test cleanup, SSH connectivity was lost: server-jetson.local no longer resolves,192.168.123.14:22 and Tailscale100.109.77.47:22 both timed out. Cause not established; may be external power/network change. Do not repeat the feed test while disconnected. Last two attempted copies of final tare evidence failed; full successful test JSON is already local and includes correct final tare values. Need recover SSH and receive servo supply voltage before continuing hardware diagnosis.

## Owner resolved disconnected servo wire; follow-up underway12:20

- Owner reports servo is now OK; its wire had not been connected. Voltage measurement no longer needed unless a new symptom appears.
- SSH recovered via server-jetson.local; new Jetson boot_id cc537b3e-403a-47c6-b731-569cc4ffa50f. All3 services auto-started, current bridge/worker hashes unchanged. NTP confirmed this boot12:17:40.
- Logs show owner manual feed12:19:18 baseline.41g, close on+36.38g then neutral12:19:21. Another manual12:19:34 added essentially0g then4s fallback close. Do not interpret manual35g event as proven scheduled35g.
- Initial read had36.8g in bowl; asked owner to remove food, place empty bowl, align gate CLOSED and stay beside machine. Waiting on this new required physical confirmation before repeat scheduled test. Latest weight after owner manipulation~-2.47g; terminal stateCAT FAULT* from last manual timeout. Do not tare without fresh empty-bowl confirmation.
- Updated test helper first allows idle terminal states, then records operator-confirmed CLOSED via inspect_ok and waits forREADY before creating future test plan. Production firmware unchanged. Tare helper allows only idle terminal states, stable load within+/-10g around known bowl zero; rejects removed bowl~-25g and food~35g. Once fresh confirmation arrives, run tare helper then live_schedule_test.py sequentially; still one new unique temporary slot, delete finally.
- Camera still absent /dev/video*; AI OLED real CAT/DOG not yet physically verified. Prior final tare evidence successfully downloaded after SSH recovered.

## Retest after fresh empty-bowl confirmation12:24–12:25

- Owner confirmed empty bowl, CLOSED gate, ready. Tare helper ran immediately; before-2.13..-2.22g stable, after-.01..+.09g stable. New valid tare_counts=-693066.4666666667; conversion factor unchanged.
- Temporary test `schedule_proof_20261108_3c24405e` was created due12:26. However owner had independently replaced the old Friday plan with enabled Sunday plan `plan_50281fb2793d369478eb012b42db0169`, revision2, namecat,12:25.
- Owner's12:25 slot automatically ran while test script was waiting. Script detected unexpected nonidle stage and immediately soft-deleted only its12:26 test plan. Owner plan list unchanged by script. No agent12:26 feed occurred.
- Owner's12:25 worker occurrence created05:25:00.855Z, one UARTfeed_once at05:25:00.964Z, MCU ACCEPTED05:25:01.146Z, opened900ms, waited25seconds without mass gain, full1450ms close, FAILED result05:25:28.365Z, measured delta-.046g. Full proof `owner_schedule_1225.json` saved remote and downloaded locally. Thus real scheduler-to-MCU protocol works; physical serving still not verified.
- Asked owner whether servo physically moved at12:25 and whether food fell; also where camera is currently connected (Jetson has no video device). Awaiting those facts. Do not add another feed while waiting. Existing owner plan12:25 remains enabled Sunday as owner set it.
- Temporary test report and latest tare evidence downloaded. SSH.local had one transient name failure then recovered immediately. No service/firmware changes this turn.

## Owner explicitly requested12:35,35g — executed

- Owner clarified “cài35” means12:35 today,35g. Agent PUT existing ownerplan `plan_50281fb2793d369478eb012b42db0169`, expected_revision2, nowrevision3,time12:35,target35. Preserved namecat,enabledtrue,Sunday[6]. This is the owner's plan, not a disposable agenttest; do not delete or disable it without instruction. Update backup/proof `schedule_1235_update.json`.
- Monitor proof `schedule_1235_result.json` downloaded locally. At12:35:01 worker committed new slot after same-day12:25, sent exactlyone `feed_once schedule_45fb92fffd7b83f99b70ff1a2ae0f6b250ece55ec28c2989`, MCU ACCEPTED. Confirms same-day retiming bug is fixed on real system.
- Baseline-.65g; mass increased~15g by12:35:11,~18.9g by12:35:27.25s weight timeout fired,1450ms close, terminalFAILED at12:35:28.700,delta18.942g. Final measured scale~19.07g. **Did not deliver verified35g; never report as success.** No changes to firmware/timeout yet. Asked owner whether actual flow was slow, jammed/empty, or manually adding test weight. Awaiting answer before changing timeout or motion.
- Camera plugged into Jetson; actual /dev/video0 enumerated12:31:30 USB4a54:5233. Existing AI launcher automatically recovered, detectorpid7078/tappid7079 ownedcamera. All130monitorrows were freshONLINE,NONE,currentboot,storage_errors0. Thus AI is running normally; OLEDFAIL correctly reflects noCAT/DOG.
- Asked owner to put real cat/dog or their image in camera view and confirm physicalOLED CAT/DOG, keeping bowl withfood in place so bridge empty-bowl gate prevents extraCAT feeding. No fake ai_cat/dog commands sent. Passive watch script prepared; first launch had transient mDNSfailure, retry pending/result noted next.
- Passive watch successfully launched on retry, device IP192.168.123.14 confirmed. Camera physically disappeared at12:37:35 (kernelUSBdisconnect1-3.1); detector exited12:37:36 with camera read failure, tap markedUNKNOWN/DISCONNECTED, OLEDFAIL. AI service remainsactive waiting for camera, API/bridge active. No software crash or missing-label defect established; awaiting replug/owner OLED confirmation. No firmware modifications or further feed commands after12:35.

## Superseded by owner follow-up: OLED restyle completed12:58

Owner confirmed detection is now correct and requested a professional OLED redesign. Owner answered previous food-flow question “đã oke rồi nha”; do not keep asking that resolved question or change dispensing behavior without a new request.

OLED-only redesign completed and flashed. Current appSHA25610ab2337087c60caf4f852989b1bc1593aacdc8aad89a6f2a6739546f75c42ba, sourceSHA2561d06e03891734dfee5f8be21a6e73c6bdcb999bf8966a15b72166307f129b1c8. Source at D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino synchronized. See ../oled_product_20261108/README.md for design,scope,backups and tests. Do not compare future flashing to the olderf97d42 firmware as current; it is now a backup. Scale NVS and backend schedule changes preserved. API/bridge/AIactive,OLEDHEALTHY,READY,AI ONLINE/NONE confirmed12:59:57. No feed or motion test command sent in OLED task. User-visible preview in ../oled_product_20261108/oled_preview.png.
