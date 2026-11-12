# UART line framing and owner baseline zero — 10/11/2026

Owner requested current 0.8–1.0 g, then reported OLED about0.6g, become zero. First attempts safely sent no tare because UART data became stale. Observed ESP32 boot banners repeated; cause unknown. Direct4sprobe once received only1NUL/no complete lines. Do not attribute all interruptions solely to parsing.

Bridge readline timeout is100ms; long status JSON can take longer to transmit and was logged/discarded as separate text fragments. Added bounded16KiB SerialLineBuffer: retain fragments across timeout, decode only complete newline-terminated lines, discard overlong line through nextnewline, then resynchronize. AI/command polling continues between fragments. No native firmware change. Preserves current UART41/42, PIR removed, CAT gate, durable SQLite outbox and all previous bridge fixes.

3 buffer tests (fragment/timeout, UTF8+multiple records, overflow/resync),1 PIR-removal and5 UART tests passed. Actual bridge deployed SHA256 `81c591b1237473dc7accb645fbf2da0971ad792bc4034f29e1a9f6915e2a1eed`. Backup `live_before.py` remote. Do not overwrite with older 8db8cd… bridge.

Then current baseline samples0.34,0.35,0.41,0.40,0.33,0.33g qualified as stable. Sent factor-preserving `t`; fresh hx_cal ACK operationrezero/oktrue/savedtrue. New tare **−700986.7333333333**, unchanged grams/count **−0.000945082600219258**. Evidence `../remove_pir_20261110/owner_baseline_zero_1794284028.json`. This save succeeded even though strict subsequent verification assertion failed: ten samples ranged−0.25..+0.05g, outside the script's±0.2g criterion. Later cachedstatus signed−0.02/display0.0, but UART22secstale. Do not claim fully stable live zero or resolved physical resets. No repeated zeroing or forced display clamp applied. No actuator test or firmware flash in this task.

Last cached mode was demo_exitedfalse, but stale data cannot prove current physical/automatic state. Needs further UART/power/reset investigation if interruptions persist. Current state file updated with new tare; old tare in earlier historical records must not be restored.
