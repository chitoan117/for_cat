# Phase 2: manual hardware validation

Run commands on the **real Jetson Nano** or **Windows development PC** as labeled. Replace `YOUR_USER`, `YOUR_JETSON_IP`, `/dev/videoX`, `/dev/ttyUSBX`, and `COMx` with paths/identifiers you actually discover. Keep the servo and pump **disconnected** throughout. Do not collect a cat dataset, train AI, enable feeding, or integrate the frontend. A failed or skipped check remains **NOT VERIFIED**.

1. **Copy/open forr_cat on Jetson (PC PowerShell, then Jetson shell).** From the PC, verify the source and transfer a source-only archive; do not copy the Windows virtual environment, PlatformIO builds, generated databases or datasets. Replace the SSH name/IP; skip the transfer if source is already present on Jetson:
   ```powershell
   $Project = 'D:\forr_cat'  # change only if you deliberately placed the project elsewhere
   Test-Path -LiteralPath $Project
   tar.exe -czf "$env:TEMP\forr_cat-src.tar.gz" --exclude=.tools-venv --exclude=.tools-zig --exclude=.venv --exclude=.pio --exclude=__pycache__ --exclude=.pytest_cache --exclude='*.db' --exclude='ai/datasets/raw/*' --exclude='ai/datasets/processed/*' --exclude='ai/datasets/manifest.jsonl' --exclude='ai/datasets/splits.json' --exclude='ai/datasets/sources.jsonl' -C $Project .
   scp "$env:TEMP\forr_cat-src.tar.gz" "YOUR_USER@YOUR_JETSON_IP:~/forr_cat-src.tar.gz"
   ```
   ```sh
   mkdir -p "$HOME/forr_cat"
   tar -xzf "$HOME/forr_cat-src.tar.gz" -C "$HOME/forr_cat"
   cd "$HOME/forr_cat"
   ls jetson/requirements.txt esp32/platformio.ini
   ```
2. **Check Jetson OS / Python (Jetson).** Save the actual output for step 25:
   ```sh
   uname -a
   cat /etc/os-release
   python3 --version
   pip3 --version
   test -r /proc/device-tree/model && cat /proc/device-tree/model
   test -r /etc/nv_tegra_release && cat /etc/nv_tegra_release
   command -v nvcc >/dev/null && nvcc --version
   command -v dpkg-query >/dev/null && dpkg-query -W nvidia-jetpack
   ```
   A missing optional command/file is not a successful hardware check. The project needs Python **3.10+**; if the Jetson has an older interpreter, do **not** replace system Python. Locate a compatible isolated interpreter or stop and report the version.
3. **Create Python environment if needed (Jetson).** Use an installed Python 3.10+ interpreter; substitute its executable for `python3` below if necessary. If `venv` is unavailable, stop and report the error rather than changing system Python:
   ```sh
   cd "$HOME/forr_cat/jetson"
   python3 -m venv .venv
   . .venv/bin/activate
   python --version
   ```
4. **Install only required project dependencies (Jetson).** Do not install AI frameworks. OpenCV is optional for mock-only operation; before the webcam test, confirm a Jetson-compatible `cv2` and `numpy` are importable in this *same* environment. If absent, pause webcam validation and report the failure rather than blindly installing a desktop wheel:
   ```sh
   python -m pip install -r requirements.txt
   python -c 'import cv2, numpy; print(cv2.__version__, numpy.__version__)'
   ```
   If the system already provides a compatible OpenCV but the isolated venv cannot see it, investigate a separate venv with `--system-site-packages` before proceeding; do not assume that it will work.
5. **Run Python tests on Jetson.** Record total/passed/failed; PC results do not count:
   ```sh
   python -m pytest tests -q
   ```
6. **Connect Logitech USB webcam (Jetson).** Plug it into the Jetson's USB port; keep other hardware disconnected.
7. **Detect `/dev/video*` (Jetson).** Choose the actual capture-capable node; if `v4l2-ctl` is already installed, inspect its listing:
   ```sh
   ls -l /dev/video* 2>/dev/null || echo 'No video devices found'
   lsusb
   command -v v4l2-ctl >/dev/null && v4l2-ctl --list-devices
   export CAMERA_DEVICE=/dev/videoX
   ```
8. **Run `tools/test_webcam.py` (Jetson, from `jetson/`).** The supported module invocation is:
   ```sh
   python -m tools.test_webcam --device "$CAMERA_DEVICE" --seconds 5
   ```
   This reads for at most 5 seconds and may save **one** inspection frame under an OS temporary `forr-cat-hardware-test-*` directory; it is not training data.
9. **Record resolution/FPS/read failures.** Copy the command's `resolution`, `approximate_fps`, `frames`, `failures`, `test_frame`, and selected device path into step 25. If it cannot open/read, record the error instead of inventing measurements.
10. **Build ESP32 firmware on development PC (PC PowerShell).** First check that the connected board matches the configured `esp32dev` target. Isolated PlatformIO is available in `.tools-venv` on the current PC; if the file is missing on your PC, stop and report the toolchain status:
    ```powershell
    Set-Location -LiteralPath (Join-Path $Project 'esp32')
    $Pio = Join-Path $Project '.tools-venv\Scripts\pio.exe'
    & $Pio --version
    & $Pio run -e esp32dev_hw_safe
    ```
    Record actual board, build environment, RAM, flash, warnings, and errors.
11. **Flash ESP32 (PC).** Only after a successful build, identify the actual programming port and substitute it for `COMx`:
    ```powershell
    python -m serial.tools.list_ports -v
    $ESP32_PORT = 'COMx'
    & $Pio run -e esp32dev_hw_safe -t upload --upload-port $ESP32_PORT
    ```
    Record upload success/failure; a build alone does not prove the board responds.
12. **Keep servo and pump DISCONNECTED.** Physically verify both are disconnected before and after flashing and before connecting the board to Jetson. Do not attach feeding actuators in this phase.
13. **Connect ESP32 to Jetson by USB.** Use USB for power/programming and serial; do not wire UART GPIO pins for this first test.
14. **Detect `/dev/ttyUSB*` or `/dev/ttyACM*` (Jetson).** Identify the actual device; replace the example before running tests:
    ```sh
    ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo 'No USB serial devices found'
    export ESP32_SERIAL_DEVICE=/dev/ttyUSBX
    ```
15. **Run `tools/test_serial.py` (Jetson, from `jetson/`).** Three low-rate pairs, then one optional bad-CRC PING; no FEED_REQUEST is sent:
    ```sh
    python -m tools.test_serial --device "$ESP32_SERIAL_DEVICE" --count 3 --interval 1 --malformed
    ```
16. **Test PING.** In the output of step 15, verify `PING ... reply=ACK`, matching `id`/`reply_id`, and `payload=01` on repeated requests. Record a bad-CRC `NACK` with `reason=01` only if it actually appeared.
17. **Test GET_STATUS.** In the same output, verify `GET_STATUS ... reply=SYSTEM_STATUS`, matching IDs, `payload=01`, on repeated requests. This is protocol responsiveness, **not** sensor health or feeding success.
18. **Unplug ESP32 (Jetson).** Leave the webcam connected; do not plug in actuators.
19. **Confirm OFFLINE detection (Jetson).** The utility should report unavailable/timeout or device disappearance; record its actual output (a nonzero exit is expected while disconnected):
    ```sh
    ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo 'No USB serial devices found'
    python -m tools.test_serial --device "$ESP32_SERIAL_DEVICE" --count 1 --interval 1
    ```
20. **Reconnect ESP32.** Inspect the serial device list again because its path may change:
    ```sh
    ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo 'No USB serial devices found'
    export ESP32_SERIAL_DEVICE=/dev/ttyUSBX
    ```
21. **Confirm recovery (Jetson).** Substitute the newly observed path in step 20; require valid PING and GET_STATUS responses again:
    ```sh
    python -m tools.test_serial --device "$ESP32_SERIAL_DEVICE" --count 2 --interval 1
    ```
22. **Start FastAPI with real hardware configuration (Jetson, still in `jetson/` with venv active).** Do not call `/feed/manual`; SERIAL mode blocks it locally anyway. Leave this terminal running:
    ```sh
    export CAMERA_PROVIDER=USB
    export ESP32_TRANSPORT=SERIAL
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    ```
23. **Verify `/api/v1/health` (Jetson, second terminal).** Process health alone does not validate hardware:
    ```sh
    curl http://127.0.0.1:8000/api/v1/health
    ```
24. **Verify `/api/v1/status` (Jetson, second terminal).** Record actual `camera`, `esp32`, `esp32_online`, and `sensors`. Expect sensors `NOT_CONNECTED`; only working real devices may be reported ONLINE. For API-level disconnect/reconnect evidence, repeat the command while unplugged and after replugging (update the configured path/restart the API if the device name changes):
    ```sh
    curl http://127.0.0.1:8000/api/v1/status
    ```
25. **Record actual results.** Edit `docs/PHASE2_HARDWARE_VALIDATION.md` on the Jetson or transfer measured outputs to the development PC. Fill each NOT VERIFIED entry only from observed commands (including failures, device paths, versions, test counts, webcam metrics, build/upload output, serial request IDs and API responses). Phase 2 stays **NOT COMPLETE** until both physical paths pass: webcam → Jetson → readable OpenCV frame; Jetson → USB serial → ESP32 → valid response → Jetson, with servo and pump disconnected.
