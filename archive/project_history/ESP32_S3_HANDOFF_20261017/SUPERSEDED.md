# Superseded by the sensor station V2 bundle

Use `D:\for_cat\ESP32_S3_HANDOFF_20261018_V2` for subsequent source/build/deployment.
The V2 offline integration tests exposed and fixed a real calibration-state bug
in this earlier image: changing level geometry after HX711 calibration/tare could
restore stale in-memory scale calibration. This old directory is retained as an
immutable historical test/build record; prefer the V2 deploy image and manifest.
No image was flashed during either software-preparation phase.

Verified current bundle on Jetson:
`/home/toan/for_cat/evidence/esp32_firmware_loop_v2.y29YQe/handoff_v2/deploy`.
