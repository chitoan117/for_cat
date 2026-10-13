# ESP32-S3 serial options — implementation unknown until arrival

`esp32/include/serial_port.h` decouples binary UART v1 from the Arduino serial endpoint. Device paths remain supplied by `ESP32_SERIAL_DEVICE` or `tools.test_serial --device`; framing/CRC/IDs remain unchanged at 115200/8N1.

| Option | Compile selection | What must be physically checked |
| --- | --- | --- |
| A USB-to-UART bridge | `FORR_NATIVE_USB=0` (or absent): use explicit UART0 `Serial0` | bridge chip, USB connector routing, reset/DTR behavior; typically COM or ttyUSB but not assumed |
| B Native S3 USB CDC serial/JTAG | S3 surrogate has `FORR_NATIVE_USB=1`, official manifest `ARDUINO_USB_MODE=1`, `ARDUINO_USB_CDC_ON_BOOT=1`; `Serial` is SDK HW CDC alias | actual USB D+/D− connection, enumeration, bootloader mode and runtime COM/node; ttyACM is possible, not guaranteed |

RC2's four builds validate classic UART0 and S3 native CDC compilation only. The M3 pack adds `esp32s3_n16r8_hw_safe_uart` using the same memory options with `FORR_NATIVE_USB=0`, CDC_ON_BOOT=0, HW_SAFE and a once-only monitor banner. Use it for an **identified** CH343G bridge; do not conflate it with the native profile. The external antenna/Type-C labels do not identify routing. Never assign GPIOs/peripherals from the surrogate.

Original/native profiles still avoid custom text. Bridge-first HW_SAFE optionally prints human metadata once at boot; it does not expand binary PING/GET_STATUS replies. Host startup buffering/START scanning ignores boot bytes, and monitors must close before probes. Native CDC may have no readable ROM banner. Require source/image/boot identity evidence for HW_SAFE, then valid correlated frames/CRC/unplug/replug for link readiness. A compiled target does not make `/status` ONLINE.

## Memory configuration evidence
Official manifest's display name remains "DevKitC-1-N8 (8 MB QD, No PSRAM)". Overrides, not that name, select 16 MB flash (`board_upload.flash_size=16MB`), package `default_16MB.csv`, `qio_opi` memory libraries and `BOARD_HAS_PSRAM`. Arduino package board menus and installed qio_opi library support were inspected (`RC2_STARTING_POINT.md`). OPI mode is appropriate for the *R8 compile candidate*; actual 8 MB PSRAM size is discovered at runtime, not manufactured by a compiler flag. No runtime memory test has happened. Confirm capacities and voltages before using this image on the seller board.
