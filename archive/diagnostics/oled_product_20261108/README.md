# FOR CAT product OLED — deployed2026-11-08

Owner requested a professional OLED interface based on the supplied photo. Owner also confirmed the earlier food-delivery issue is now OK; no dispensing timeout or motion settings were changed in this task.

Only two display source blocks changed: rendering and boot splash. Reversing those substitutions exactly reproduces the normalized original source. Evidence:ui_scope.json. All sensor pins, scale calibration/filtering, AI heartbeat, feeding state machine,35g trigger, servo1350us900ms OPEN/1600us1450ms CLOSE/1500us neutral, scheduled delivery and water logic remain identical.

## Interface

-128x64 monochrome, existing Adafruit classic5x7 font, with a paw mark and FOR CAT brand.
- Separate AI CAT/DOG/FAIL badge uses only the existing fresh AI helper. No manual movement fabricates recognition.
- Large adaptive weight andg unit, signed readings retained. Missing/stale scale shows--.- plus KIEM TRA CAN rather than stale or fabricated zero.
- Plain-language status band, pause/warning marks and measured35g progress bar during feeding. An underdose remains visible as LAN CAP CHUA DU; a UI restyle does not invent a successful meal or verified mechanical closure.
- E1 MEO/E2 THUC AN/D1 CHEN/D2 BINH aligned in a detail page. Home9s/detail3s while idle without a recognition; home remains visible during feeding, CAT/DOG recognition, pause, inspection or calibration.
- Clean FOR CAT / DANG KHOI DONG boot splash. ASCII Vietnamese labels suit installed font.

## Validation and deployment

- Arduino ESP32-S3 core3.3.12 compilePASS:396853 program bytes,35840 globals.
-900 native framebuffer cases using production rendering functions: all phases,AI labels,negative/large/nonfinite values andmillis rollover stay within128x64. Priority and honest missing-scale/underdose states verified. Actual classic glyph bitmap used; test rounded primitives approximate GFX rasterization at corner pixels. QA images are layout renderings, not photographs of the physical device.
- AppSHA25610ab2337087c60caf4f852989b1bc1593aacdc8aad89a6f2a6739546f75c42ba.
- Actual old app matched known deployedf97d42d346bfd7957fec1f38c5e0e9bde17e9802a1b38490d2411edfcf65deab. Full0..0x150000 backup, partition table and active OTA sequence checked before app-only write/verify.
- NVS before/after preboot identical,SHA2564bb936c24cf08da4f1b8182c73aa14b0a3035940bfba47c7b8ebcce879ccac27. Scale tare-693066.4666666667 andg/count-.000945082600219258 retained.
- No feed/open/close command sent during this update. Pre-update idleCLOSED estimate and no inspect lock were captured; same relative marker restored after reboot with unchanged motion profile. This remains a relative estimate without a physical limit switch.
- UART and API confirmed OLED HEALTHY,ESP32 connected,READY,AI ONLINE/NONE,timevalid. API/bridge/AI allactive after restoration. No new supervised physical meal was needed for this display-only change.
- Original source D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino synchronized after old-source hash guard and verifiedflash. New sourceSHA2561d06e03891734dfee5f8be21a6e73c6bdcb999bf8966a15b72166307f129b1c8. Before source backed up underbefore/.

Remote backups/proof:/home/toan/for_cat/evidence/oled_product_20261108. Localflash_result.json,deployment.json,backup_result.json,boot_new.log. Preview:oled_preview.png; full QA:qa_all_states.png.

## Subsequent firmware update

Owner requested power-loss feeding fallback and explicitly requested flashing now, independent power to be added tomorrow. This OLED layout is retained in the newer deployed firmware app554dd2c2251f27245dcdb98f14c5d07932a38e656282deb676b5451bffc0a48d. See ../power_fallback_20261108/README.md for current source, matching Jetson heartbeat bridge, enabled configuration and pending physical outage test. Do not use this older OLED app as the current baseline for future flash guards.
