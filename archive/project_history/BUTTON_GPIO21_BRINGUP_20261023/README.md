# GPIO21 manual button diagnostic evidence

New diagnostic revision; do not overwrite the prior sensor release.
Profile: diag_current_hardware. Button INPUT_PULLUP, active LOW, 40 ms debounce,
press-edge diagnostic event only. GPIO6/7 untouched, no PWM or dispensing.
Physical button PASS requires the user's later evidence.

Deployment, when performed, is application-only at 0x10000 after ROM identity
and bootloader/partition match. No erase-all, factory image, NVS or partition write.
See repository docs/MANUAL_BUTTON_BRINGUP.md for the user test procedure.
