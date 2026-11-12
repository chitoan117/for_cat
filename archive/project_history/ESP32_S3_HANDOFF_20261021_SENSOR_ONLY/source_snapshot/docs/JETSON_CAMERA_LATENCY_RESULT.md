# Real Jetson camera latency validation

Baseline repository: `8511ea09fb5d61e588dbcaed5d18d829c459b001`.
Agent executed on `server-jetson` (aarch64), OpenCV 4.8.0, TensorRT 8.2 API,
the existing FP16 COCO engine, and the actual USB webcam. No actuator operation.

## Provenance before modification

- Source SHA256: `9f6e97bee11f7cfe558850400c4c5ba16cd56fb3dc6472b1ab38b5e35d8d6583`.
- Existing binary SHA256: `dc7f66677c016d5e823d55e29655a0f029a7a011372751e3afe64b9e3c548439`.
- Rebuilding the original source with the documented flags produced the SAME binary hash.
- Existing binary mtime: `2026-10-11 17:09:45.554473332 +0700`; this is a filesystem timestamp, not a new build claim.
- Engine SHA256, unchanged: `48fe40017461d2e4edab33c47b30194b84ba7714e32e6d3d2aa4649f5b7471fb`.
- Candidate source SHA256: `9b01288e4b6e450217d3029c2d0b4a3aecafb9dc0e2f87e17289d3e83f5b6366`.
- Validated candidate executable SHA256: `c3651fc3d1331b24a45c6a74b94a883e362fd4ded2412bb8f3ad195f1c443cdc`.
- Working tree initially had no tracked changes; existing `cat_dog_trt.cpp.bak_latency` was preserved.

## Method and measurements

The original program was compiled separately and run headless for 30 wall seconds.
It reported approximately 30 FPS after startup, but its timer omitted display/JPEG.
The detailed BEFORE below uses `--capture-mode sequential`: original synchronous
capture and original four-driver-buffer policy, with the same instrumentation and
five warm-up frames as AFTER. AFTER uses one application slot and two driver buffers.
All six final comparisons collected at least 30 measured seconds after warm-up.

Camera readback: V4L2, MJPG, **640x480 @30 reported FPS**. Real engine bindings:
INPUT FP32 `1x3x320x320`; OUTPUT FP32 `1x84x2100`; unvectorized linear storage.
Internal FP16 does not imply FP16 input/output allocation.

| Mode | Capture | Full-loop FPS | App age mean / p95 ms | V4L2 timestamp age mean / p95 ms | TRT ms | Display ms | Replaced frames |
|---|---|---:|---:|---:|---:|---:|---:|
| Headless, no snapshot | sequential | 29.942 | 21.109 / 25.541 | 67.436 / 140.186 | 17.075 | 0 | 0 |
| Headless, no snapshot | latest | 29.996 | 22.508 / 25.576 | 62.532 / 65.619 | 18.459 | 0 | 29 |
| Headless + snapshot | sequential | 30.043 | 21.563 / 23.539 | 64.113 / 70.704 | 17.220 | 0 | 0 |
| Headless + snapshot | latest | 30.021 | 21.706 / 25.724 | 61.301 / 65.112 | 17.117 | 0 | 40 |
| Moba/X X11 forwarding | sequential | 18.144 | 47.991 / 50.096 | 254.662 / 284.965 | 21.830 | 22.128 | 0 |
| Moba/X X11 forwarding | latest | 20.077 | 65.567 / 82.573 | 105.464 / 122.188 | 21.730 | 22.814 | 542 |

Snapshots cost 7.730 / 7.594 ms per write in sequential/latest respectively,
about once per second. Counts include warm-up; FPS/mean/p95 exclude five warm-up frames.
Full raw stage measurements also record PRE/H2D/TRT/D2H/ENQUEUE/SYNC/POST/READ,
snapshot amortized cost, queue age, captured/processed/measured/sequence and shutdown.
All final runs had zero read failures and valid increasing driver timestamps for
every measured frame. Normal shutdown took roughly 8-18 ms in the final runs.

### Why both ages are necessary

`FRAME_AGE_ms` starts AFTER OpenCV read returns; it cannot see frames already queued
in the kernel. The sequential baseline therefore under-reports camera backlog.
`DRIVER_AGE_ms` uses OpenCV V4L2 `CAP_PROP_POS_MSEC` only when its increasing timestamp
is consistent with the host monotonic clock (nonnegative, below the sanity bound).
It includes the driver-buffer residence omitted by app age. Neither metric proves
sensor exposure-to-photon latency; human/glass-to-glass observations were not measured.

X11 buffer age fell **254.662 -> 105.464 ms**, p95 **284.965 -> 122.188 ms**,
while the TRT CUDA-event stream span remained approximately 21.8 ms. This span
can include host launch/scheduling gaps; it is not trtexec's isolated kernel GPU
compute metric. CPU enqueue/sync are logged separately. X11 display calls still cost
about 23 ms/frame. Capture must stay independent of this slower display path.
App age alone increased in X11 because it now includes time in the application
slot that the sequential driver's post-read timestamp hid. Do not claim that the
app-only metric improved in every mode.

### Single-buffer regression and measured correction

The first candidate successfully requested ONE V4L2 buffer, but delivered **14.991 FPS**
with approximately **66.691 ms/read**, versus the sequential 29.953 FPS baseline.
The validated default tries the requested one-buffer setting, then selects TWO
driver buffers to avoid observed capture starvation. `--camera-buffers 1|2|4`
allows reproduction. There is still exactly ONE bounded application frame slot.
This adjustment was based on target measurements, not an assumed unsupported property.

## Regression and lifecycle checks

- 27 native checks and 20,000-publication concurrency stress PASS on host and Nano.
- The same native tests PASS with ThreadSanitizer and ASan/UBSan on Nano.
- Actual V4L2/OpenCV4.8 ownership probe retained one Mat while reading 60 fresh
  Mats: retained bytes stayed identical and its storage address was not reused.
- Real TensorRT engine binding/format guards PASS before buffer allocation/inference.
- Original constants, letterbox, preprocessing and postprocessing preserved byte-for-byte
  (prefix normalized SHA256 `1b8602dba1bbf604fe5754ce92d774e828aa0e5435c3dd8f9b2fff8409c683e2`).
- Six synthetic decoder/preprocess unit cases PASS, explicitly not physical evidence.
- Reused THREE images already in the local project, not a downloaded dataset:
  real-engine offline CAT 0.927363; DOG 0.879974; person photograph NONE, all PASS.
- Live empty/no-animal view returned NONE; snapshot visually reviewed.
- Live physical CAT/DOG/PERSON presentation: **NOT_TESTED_PHYSICALLY**.
- SIGTERM while running: normal exit and shutdown 15.077 ms in the dedicated test.
- `destroy()` deprecation warnings retained for the working TensorRT 8.2 API.
- Current decoder still compares CAT/DOG scores only; it does not enforce the global
  winner across all 80 COCO classes. A person score higher than a pet score is not
  guaranteed to suppress the pet score. No claim of full PERSON/UNKNOWN blocking.

Raw logs and captures belong under ignored `evidence/jetson/` and the original
`/tmp/for-cat-baseline.eZbZUH/` staging directory. Model/image bytes are not committed.
Production replacement requires the preserved binary backup, unchanged engine hash,
and a fresh smoke run; Git operations never include model/dataset/backup files.

## Installed result

After those checks, the candidate was installed atomically on the actual Jetson.
Backup `jetson/ai/cat_dog_trt.backup_pre_latency` retains the original `dc7f...` hash.
Installed binary is the validated `c3651fc3...` hash above; engine hash unchanged.
Post-install smoke: 30.107 FPS, no read failures, driver age mean/p95 63.771/65.543 ms,
normal shutdown 15.446 ms. Raw evidence is preserved in ignored
`evidence/jetson/latency_eZbZUH/`. No assertion of live physical animal testing was added.
