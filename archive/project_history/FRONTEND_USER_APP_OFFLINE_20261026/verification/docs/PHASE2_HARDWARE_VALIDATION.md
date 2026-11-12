# Phase 2 hardware validation record

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT baseline:** no physical milestone was passed. Current host results/architecture are `PRE_HARDWARE_FINAL_BASELINE.md` / `REFERENCE_ARCHITECTURE.md`; this record preserves earlier counts and observations.

**Status (historical Phase 2 checkpoint):** software integration and inert firmware compiled on a Windows PC; no Jetson/Logitech webcam, ESP32 flash, USB link or on-device API tests had been performed. A different **PC** camera was later tested; see `PRE_HARDWARE_RC1.md`. Never treat PC frames or mock responses as Jetson/Logitech hardware evidence. The original host-test count below is historical; servo and pump must remain disconnected.

## VERIFIED (host software only)

| Item | Result |
| --- | --- |
| Development PC | Windows 11; Python 3.14.3 |
| Jetson Python compatibility change | `enum.StrEnum` replaced by portable `class Name(str, Enum)` in recognition, behavior and feed-state models; practical minimum Python 3.10 due to `|` type annotations, Pydantic 2 and current dependencies |
| Host tests | `python -m pytest tests -q` from `jetson/`: 38 passed, 0 failed on the Windows PC |
| Inert ESP32 PC build (later pre-hardware checkpoint) | PlatformIO Core 6.2.0 isolated in `.tools-venv`; `esp32dev_sim` and `esp32dev_hw_safe` compiled for configured `esp32dev`, **not flashed** |
| Python dependencies | `jetson/requirements.txt` adds only pyserial for real serial; OpenCV remains optional and must be installed in a Jetson-compatible form only if not already available |
| Device API | `/api/v1/status` reports camera and ESP32 mode/state and sensors NOT_CONNECTED; `/api/v1/health` is process-only; no real hardware validated by host mocks |

## NOT VERIFIED (fill only after executing on real hardware)

| Required observation | Recorded result |
| --- | --- |
| Jetson Nano model | NOT VERIFIED |
| `uname -a` / `/etc/os-release` / JetPack / CUDA | NOT VERIFIED |
| Jetson `python3 --version` / `pip3 --version` | NOT VERIFIED |
| Full Python tests in isolated Jetson environment (total/passed/failed) | NOT RUN |
| Logitech webcam model and `/dev/video*` device path | NOT VERIFIED |
| Jetson Logitech OpenCV resolution / FPS / failed reads / one test frame | NOT VERIFIED |
| ESP32 actual board model | NOT VERIFIED |
| ESP32 on-device flash/build-target confirmation / runtime | NOT VERIFIED; PC compile does not confirm actual board |
| ESP32 USB serial device path / baud | NOT VERIFIED / configured 115200, not measured |
| Real PING / ACK with correlated ID and CRC | NOT VERIFIED |
| Real GET_STATUS / SYSTEM_STATUS | NOT VERIFIED |
| Physical disconnect and reconnect behavior / timeout | NOT VERIFIED |
| Malformed-frame NACK on physical device | NOT VERIFIED |
| Jetson local FastAPI health and status with real devices | NOT VERIFIED |

## On the real Jetson Nano (do not substitute PC output)

Record output of `uname -a`, `cat /etc/os-release`, `python3 --version`, `pip3 --version`. If available: `nvcc --version`, `cat /etc/nv_tegra_release`, `cat /proc/device-tree/model`, `dpkg-query -W nvidia-jetpack`. Do **not** upgrade system Python blindly. If Python is below 3.10, first assess an available isolated compatible interpreter and dependency wheels; compatibility has not been established for Python 3.6–3.9. With a compatible installed interpreter, from `jetson/` run `python3 -m venv .venv`, `. .venv/bin/activate`, `python -m pip install -r requirements.txt`, and `python -m pytest tests -q`. OpenCV is optional for mock-only operation; check `python -c 'import cv2; print(cv2.__version__)'` in the **same** environment before USB mode. If unavailable, arrange a Jetson-compatible OpenCV package before testing the webcam, without adding a heavy AI framework.

Inspect `ls -l /dev/video*` and optionally `v4l2-ctl --list-devices` and `v4l2-ctl --device /dev/videoX --all` **only if v4l2-ctl is already installed**. Replace X with the observed path. From `jetson/`, run `python -m tools.test_webcam --device /dev/videoX --seconds 5`. It opens, reads for a bounded period, reports dimensions, approximate FPS and failures, saves at most one JPEG in an OS temporary `forr-cat-hardware-test-*` directory for manual inspection, then closes. That JPEG is not a training dataset.

Set `CAMERA_PROVIDER=USB` and `CAMERA_DEVICE=<observed path>` only after device discovery. Defaults are MOCK. Start with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`; request `curl http://127.0.0.1:8000/api/v1/health` and `curl http://127.0.0.1:8000/api/v1/status`. LAN binding to `0.0.0.0` is optional and untested here.

## ESP32 build and physical serial link

Compile the inert firmware on the designated machine with isolated PlatformIO (`.tools-venv/Scripts/pio.exe` on the current PC): from `esp32/`, run `pio run -e esp32dev_hw_safe`. Record compiler output, RAM, flash, warnings and errors. Confirm actual board identity before flashing; no actuator may be connected. PC compilation has succeeded; no physical board has been identified or flashed.

With the **powered/programmed ESP32** attached by USB to the Jetson, inspect `ls -l /dev/ttyUSB* /dev/ttyACM*` (one or both may not exist) and `dmesg`/`lsusb` if permitted. From `jetson/`, use `python -m tools.test_serial --device <observed path> --count 3 --interval 1 --malformed`. It sends only PING and GET_STATUS plus one opt-in bad-CRC PING, checks response IDs/codes, and sends **no feed request**. To observe physical unplug and replug, run the utility while connected, unplug, repeat while disconnected, reconnect, and repeat; document each result. Leave request rates low. The transport closes on link failure and attempts reopening on a later request.

Set `ESP32_TRANSPORT=SERIAL` and `ESP32_SERIAL_DEVICE=<observed path>` for API status polling. SERIAL mode blocks `/feed/manual` locally; ESP32 firmware also remains inert. `/status` must show ONLINE only for a valid GET_STATUS response, OFFLINE after disappearance or timeout, and recover when reconnected. The camera requires a readable frame to report ONLINE. Sensors remain NOT_CONNECTED.

**Phase 2 completion gate:** a real Logitech webcam must yield OpenCV frames on the Jetson **and** a real ESP32 must return verified serial PING/GET_STATUS responses on the Jetson, with servo and pump disconnected. That gate is not met by the host tests in this record.
