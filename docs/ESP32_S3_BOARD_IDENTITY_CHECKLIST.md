# Board identity checklist — all physical checks pending

- [ ] Board front/back photographs and seller order/listing saved (listing is not physical proof).
- [ ] Exact module marking transcribed: ESP32-S3-WROOM-1 or 1U, suffix/revision, not inferred from a family name.
- [ ] N16R8 marking confirmed on the actual module; 16 MB flash/8 MB PSRAM remain capacity tests, not just listing text.
- [ ] Antenna type identified: module PCB antenna vs external-antenna variant; connector and suitable antenna recorded if present.
- [ ] Both Type-C connectors photographed/labeled and routing checked against actual schematic/continuity evidence.
- [ ] CH343G chip marking photographed and Windows USB hardware IDs/driver/COM recorded.
- [ ] Board/carrier revision and 44-pin header labels recorded; silkscreen checked rather than copied from another board.
- [ ] Seller/carrier pinout archived and cross-checked against the exact Espressif module datasheet and S3 GPIO restrictions.
- [ ] Flash/PSRAM, USB/JTAG, boot-strap and input/output reservations checked.
- [ ] Power path/regulator/USB backfeed constraints reviewed; no peripheral attached yet.

Official module/devkit documentation is a reference, **not proof that the seller board equals DevKitC-1**. The repository's target remains a compile surrogate with memory overrides. Do not assign candidate/final GPIOs until relevant identity/routing/voltage items are checked; use `GPIO_FINALIZATION_WORKSHEET.md` after the M3 gate.
