# Windows build → Jetson ROM/no-stub deploy

Current user-observed chip is S3/16MB/PSRAM NOT DETECTED. Windows pinned PlatformIO works; linux_aarch64 resolution failed on Jetson. Do not force its package/toolchain or replace system Python/GPU stack. Build only no-PSRAM real safe/diagnostic environments; legacy N16R8/SIM/surrogate are not deploy targets.

## Build and identify artifacts (Windows, root)

Currentfirstscan:ONLYOLEDI2Cafterpoweroff/module3.3Vreview,SDA8/SCL9/commonGND/pull-ups3.3V;builddiag_i2c/transfer/no-stubflash/empiricalACKcandidate0x3C. **RTC hardware changed from planned DS3231 to available DS1302 during M4 physical bring-up.** RTCusesCLK16/DAT17/CE18,notI2C/no0x68expectation;build`diag_rtc`samecheckedworkflowafterseparatewiringreview. `DS1302_BRINGUP.md` / `FINAL_OPENCODE_HANDOFF.md`; noactuatoroutput orhardwarePASS.

```powershell
& .\scripts\build_esp32_windows.ps1 -EnvName diag_i2c
# Equivalent compile only:
& .\.tools-venv\Scripts\pio.exe run --project-dir esp32 -e diag_i2c
```

Builder refuses failure/unsupported environment and creates a new timestamped `.deploy/diag_i2c_*` folder; no flash. `deploy_manifest.json` records hash/size for bootloader.bin,partitions.bin,boot_app0.bin,firmware.bin,firmware.factory.bin. boot_app0 is supplied from the installed Arduino framework tools/partitions path, not assumed to already exist in the build folder. Factory offsets are0x0/0x8000/0xe000/0x10000 as the actual merge log; use its combined image for first full install.

Names for current board: esp32s3_16mb_no_psram_hw_safe_uart (binary v1), diag_i2c/rtc/hx711/food_sensor/water_sensor/oled_button_buzzer (ASCII only). The measured-board guard contains no BOARD_HAS_PSRAM; shared SDK capability defines are not hardware use. The source/header/flags changed since the physically reported397312B image; a newly built image has a different hash/size. Do not substitute the old observation as evidence for this build.

## Transfer explicitly

On Jetson create a reviewed new firmware directory, e.g. `mkdir -p "$HOME/for_cat_firmware"`. From Windows use the builder's printed path:

```powershell
scp -r ".deploy/ACTUAL_TIMESTAMPED_BUNDLE" USER@ACTUAL_JETSON_IP:~/for_cat_firmware/
```

USER/IP/bundle names are placeholders, not detected identifiers. Transfer source updates (`jetson/bringup`, dependency-free `ai/sampling.py`, `ai/label_schema.py`/`ai/__init__.py`, shell wrapper) as reviewed source, not Windows venv/cache. Keep bundle immutable; compare its actual hash on recipient with `sha256sum firmware.factory.bin` and manifest. Do not share keys/passwords.

## Jetson flash plan — system Python3.6, esptool3.3.3

From actual project root after transfer, substitute actual bundle path and SHA256:

```sh
sh scripts/flash_esp32_from_jetson.sh --profile diag_i2c --port /dev/ttyACM0 --image "$HOME/for_cat_firmware/ACTUAL_BUNDLE/firmware.factory.bin" --sha256 ACTUAL_FACTORY_SHA256
```

This is DRY_RUN: validates file/type/header/hash/profile/bounds and prints commands, opens no serial port. Before applying: actual node exists/dialout permissions, close miniterm/probes, servo/pump disconnected and factory covered range reviewed. **Factory writes erase covered sectors including NVS and gaps**, not just executable bytes; backup/review calibration/safety state if any. No erase-all.

```sh
sh scripts/flash_esp32_from_jetson.sh --profile diag_i2c --port /dev/ttyACM0 --image "$HOME/for_cat_firmware/ACTUAL_BUNDLE/firmware.factory.bin" --sha256 ACTUAL_FACTORY_SHA256 --apply --allow-factory-overwrite
```

Actual command sequence: system `python3 -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 115200 --no-stub flash_id`, then `write_flash 0x0 FILE`, then `verify_flash 0x0 FILE`. ROM preflight must report16MB; otherwise abort before write. Stub is never requested; physical stub corruption was reported. CLI output redacts MAC; preserve actual nonpersonal output and bundle hash. This helper was not flashed on Jetson by the agent.

## Subsequent sensor-mode updates without wiping NVS

Once the known matching16MB/default_16MB bootloader/partition layout has been installed and reviewed, build the next environment and transfer **firmware.bin plus manifest**. Use its application hash:

```sh
sh scripts/flash_esp32_from_jetson.sh --profile diag_rtc --port /dev/ttyACM0 --image "$HOME/for_cat_firmware/ACTUAL_RTC_BUNDLE/firmware.bin" --sha256 ACTUAL_APP_SHA256 --application-only
# After confirming matching bootloader/partition layout, add --apply.
```

Application-only writes/verifies0x10000 and preserves earlier NVS sectors. Do not use this offset on an unknown/custom partition layout or a factory image. The helper distinguishes exact filenames; it does not infer layout from a chip ID. New image does not auto-resume feeds.

## Verify/stop/recover

- `--verify-only --apply` reads/verifies existing image with no write; factory overwrite consent is not needed. ROM command failure remains failure, not assumed PASS; do not fall back automatically to stub.
- Monitor ASCII diagnostics: `python3 -m serial.tools.miniterm /dev/ttyACM0 115200` (Ctrl+] closes). Opening/reset may restart board. Banner must say correct mode, actuator=0/servo=0/pump=0, candidate pins, PSRAM not used; these software banners are not measured chip facts.
- Binary M3 HW_SAFE: close monitor, run `python3 -m bringup.serial_probe`; ASCII diag image does not respond binary PING/GET_STATUS. Switch image intentionally.
- STOP on wrong chip/flash/hash/partition, mode/SIM/output mismatch, missing/unstable node, serial corruption, unexpected GPIO activity or voltage issue. Preserve full actual failure output. Check data cable/node/clients/power and identified BOOT/RESET button procedure; no random GPIO bridging/erase-all/PSRAM flag to “fix” it.
