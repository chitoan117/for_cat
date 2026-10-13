# Jetson first-day procedure — all physical results pending

1. Photograph exact Jetson board/carrier and markings.
2. Identify Nano variant/revision and RAM size; do not infer it from a seller label.
3. Verify the correct supply against that exact board documentation; no final PSU rating assumed here.
4. Boot with ESP32, sensors, servo and pump disconnected.
5. Record Ubuntu/OS, L4T/JetPack, kernel and architecture (`uname -a`, `/etc/os-release`, `/etc/nv_tegra_release` if present).
6. Record `python3 --version` and `python3 -m pip --version`.
7. From `$HOME/forr_cat`, run `sh scripts/check_jetson_env.sh` (diagnostic only).
8. Do not replace system Python or JetPack. If below 3.10, stop project setup and plan a compatible isolated interpreter/runtime.
9. With a compatible interpreter, `PYTHON_BIN=python3 sh scripts/setup_jetson.sh`, then `. jetson/.venv/bin/activate`.
10. From `jetson/`, run `python -c 'import fastapi, serial, sqlite3; print(fastapi.__version__, serial.VERSION, sqlite3.sqlite_version)'` and `python -m tools.readiness_report --json`.
11. Explicitly install `requirements-test.txt` into this venv and run `python -m pytest tests -q`; record applicable passes/skips/failures, not PC results. Optional codec tests require compatible local OpenCV/Pillow, not a random desktop wheel.
12. Connect USB webcam only; no automatic capture daemon or dataset collection.
13. `python -m tools.list_cameras` (opens none); identify the actual Logitech model and `/dev/video*` node.
14. Manually `python -m tools.benchmark_camera --device /dev/videoX --seconds 5 --width 640 --height 480 --fps 10 --backend V4L2` (substitute actual node). Record actual dimensions/FPS/failures/backend; no image saved.
15. Connect the identified inert ESP32/S3 by USB with servo/pump/sensors disconnected.
16. Discover `/dev/ttyUSB*` or `/dev/ttyACM*`; never assume the path.
17. `python -m tools.test_serial --device ACTUAL_NODE --count 3 --interval 1`; verify physical PING/GET_STATUS IDs and CRC.
18. Unplug/replug, rediscover node and repeat; test OFFLINE/timeout then recovery and passive API readiness/liveness separately.
19. Save commands, outputs, screenshots/photos and errors in the evidence template. Only actual observations clear a gate.

Do not install GPU frameworks, flash/enable actuators, collect a cat dataset or expose the API publicly during first-day bring-up.
