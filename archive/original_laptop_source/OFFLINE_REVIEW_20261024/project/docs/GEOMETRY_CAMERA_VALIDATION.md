# Fixed-camera ROI calibration and GEOMETRY VALIDATION

This is a **shadow-only** calibration/replay tool, not behavior recognition.
RED BOWL = FOOD_ROI. BLUE BOWL = WATER_ROI. Human review determines bowl identity;
the tool does not infer identity from colors. NEAR_FOOD is not EATING and NEAR_WATER
is not DRINKING. No behavior samples or START/END behavior events are generated.

## Checkpoint and reuse

Starting checkpoint: `b7ac028`, main five commits ahead of origin/main. Existing
tracker, geometry, smoothing/FSM and their tests are unchanged. New tooling calls
`SingleCatTracker` and `observe_geometry` directly, without calling the behavior FSM.

Audited existing camera helpers, `capture_session.py`, `VideoFileCameraProvider`,
`test_detector_regression.cpp`, build scripts and shadow configuration. Dataset
capture helpers require legacy identity/behavior annotations and do not provide
this ROI calibration/native replay path. No second dataset importer or behavior
pipeline was added. Media timestamp handling reuses the existing PTS-then-FPS idea,
with a strict native clock and anchored fallback rather than wall-clock timing.

`geometry_detector.cpp` follows the already-used detector regression pattern:
include the exact production `cat_dog_trt.cpp` in a separate translation unit with
its main renamed. The production main is never called. Reuses its exact letterbox,
BGR->RGB, CHW float /255, postprocess, CAT15/DOG16, confidence0.35, per-class
NMS0.45, CUDA resource cleanup and binding checks. The small inference adapter
adds engine lifecycle/orchestration, not a duplicated preprocessing/decoder.
Live source reuses the sole-reader/latest-slot `latency::Capture` helper.

Production source, binary and engine are never rebuilt or replaced. Runtime
validation checks their audited SHA256 hashes before/after video/live runs and
refuses an unexpected engine/source/binary. No trained behavior executor exists.
Existing decoder limitation remains: it compares CAT/DOG scores, not the global
80-class winner; this tool does not claim complete PERSON/UNKNOWN rejection.

## Build on the Nano

From `/home/toan/for_cat`, with existing OpenCV4.8, CUDA10.2, TensorRT8.2, OpenSSL
development headers/libcrypto and g++7.5 (no new package/download was needed):

```sh
BUILD=$(mktemp -d /tmp/for-cat-geometry-user.XXXXXX)
sh scripts/build_geometry_validation.sh "$BUILD/geometry_validate"
TOOL="$BUILD/geometry_validate"
"$TOOL" self-test
```

Always use a new output filename. Builder refuses overwriting an existing binary.
All code is C++14. Pure helpers, tool, original shadow core and fixture generator
use strict warnings-as-errors; the included frozen production translation unit
keeps its established warning policy (deprecated TensorRT cleanup API suppressed).
Intermediate objects stay in a separate `/tmp/for-cat-geometry-build.*` directory.

The tested final normal binary is currently
`/tmp/for-cat-geometry-release.1FTB2M/geometry_validate`; rebuild after reboot if
scratch is removed. Nothing was installed over `jetson/ai/cat_dog_trt`.

## 1. Capture one ORIGINAL calibration frame

Set VIDEO to an actual accessible fixed-camera recording, not a fixture/example:

```sh
VIDEO='/absolute/path/to/operator_supplied_real.mp4'
RUN=$(mktemp -d /tmp/for-cat-real-geometry.XXXXXX)
"$TOOL" capture --video "$VIDEO" --frame-index 0 --out "$RUN/frame"
```

Outputs `frame/original.png` plus `capture.json` with source reference, frame index,
raw source timestamp, original dimensions and capture UTC. Decode is sequential
through the requested frame, not an inaccurate random keyframe seek. Source media
is read-only. Image is the decoded original frame, never the320x320 network input.

If a real camera is available and is **not in use by production/another process**:

```sh
"$TOOL" capture --camera /dev/video0 --out "$RUN/live_frame"
```

This explicit command opens only the specified node. It has a10-second frame
acquisition deadline, subject to the existing V4L2 read/timeout limitations.
No camera is auto-discovered/opened by calibration, overlay or video commands.

## 2. Mark FOOD and WATER

GUI option (requires working local display or X11/OpenCV HighGUI):

```sh
"$TOOL" calibrate --image "$RUN/frame/original.png" --gui \
  --source-reference "$VIDEO frame_index=0" --out "$RUN/calibration"
```

Select the RED FOOD rectangle, confirm, then the BLUE WATER rectangle. Cancelled/
empty or overlapping selections are rejected. GUI interaction was not physically
validated in this session; the headless option is tested and does not require X11.

Headless option: inspect original.png at its actual resolution and set measured
integer endpoints. **Do not copy coordinates from test fixtures.**

```sh
# Set these from YOUR frame; right/bottom endpoints are exclusive.
# FOOD_PIXELS='x1,y1,x2,y2'
# WATER_PIXELS='x1,y1,x2,y2'
"$TOOL" calibrate --image "$RUN/frame/original.png" \
  --food "${FOOD_PIXELS:?Set measured RED FOOD pixel endpoints}" \
  --water "${WATER_PIXELS:?Set measured BLUE WATER pixel endpoints}" \
  --source-reference "$VIDEO frame_index=0" --out "$RUN/calibration"
```

Tool converts x/width and y/height, validates through the unchanged strict shadow
parser, then writes a NEW directory. Defaults are the existing uncalibrated safe
proposals, not optimized or asserted physical thresholds. Input image is untouched.

## 3. Review overlay and provenance

Calibration output:

- `roi.candidate.json`: existing config schema2, status CONFIGURED, RED/FOOD and
  BLUE/WATER normalized original-frame boxes; all existing threshold fields.
- `calibration.json`: separate schema1 provenance with source width/height, UTC,
  image/reference/hash, normalized ROIs, config hash, config/schema versions,
  explicit colors, threshold origin and optional base-config hash.
- `overlay.png`: original-size image with colored labeled ROIs, optional approach
  line and explicit GEOMETRY ONLY notice. Bottom-center reference is added when
  a tracked cat exists during replay; calibration does not invent a cat point.
- `REVIEW.md`: human visual review reminder.

Sidecar keeps candidate JSON compatible with the existing parser, which rejects
unknown keys. `review_status` does not mean a human has already reviewed the overlay.
The user must visually confirm FOOD encloses the red food bowl and WATER encloses
the blue water bowl. No automatic semantic/physical validation is claimed.

Verify another frame from the SAME unchanged camera/view/resolution:

```sh
"$TOOL" overlay --image "$RUN/frame/original.png" \
  --calibration "$RUN/calibration" --out "$RUN/verified_overlay"
"$TOOL" check-config --config "$RUN/calibration/roi.candidate.json"
```

Outputs `overlay.png` and `verification.json`. Input dimensions must match exactly;
even an aspect-preserving resolution change requires explicit review/recalibration.
Config hash must match its sidecar. Editing a hash-bound candidate in place is
refused; create a new candidate instead. Preserve the original calibration frame.

**If the physical camera position, crop, zoom, orientation or bowl positions change
materially, review and recalibrate.** Matching dimensions alone cannot detect camera
movement. Do not reuse a calibration merely because the video is still640x480.

## 4. Validate one real recorded MP4

```sh
"$TOOL" video --video "$VIDEO" --calibration "$RUN/calibration" \
  --detector trt --out "$RUN/video_validation"
```

Sequential decode -> exact CAT/DOG detector -> normalized ORIGINAL-frame boxes ->
single-cat tracker -> geometry -> bounded review images/JSONL/report. No behavior
model, actuator command or production database write. TensorRT reads the existing
engine; its IO/bindings and hash must match the audited detector contract.

Defaults: every decoded frame, maximum18,000 processed frames. Explicit limits:

```sh
"$TOOL" video --video "$VIDEO" --calibration "$RUN/calibration" \
  --detector trt --every 2 --max-frames 6000 --out "$RUN/video_sampled"
```

`--every` samples source frame indices. Sparse sampling may intentionally break
track continuity/trend windows; do not hide this by silently expanding TTL.
`--gui` optionally displays the same overlay; q ends the run. No rendered full
video is produced by default.

ROI/manual fallback when inference is unavailable or deliberately excluded:

```sh
"$TOOL" video --video "$VIDEO" --calibration "$RUN/calibration" \
  --detector none --out "$RUN/roi_only"
```

This decodes/verifies dimensions/config but has no cat detections or fabricated
cat distances. For explicitly supplied human-reviewed original-pixel boxes:

```sh
"$TOOL" video --video "$VIDEO" --calibration "$RUN/calibration" \
  --detections /absolute/path/to/manual_boxes.csv --out "$RUN/manual_geometry"
```

CSV is numeric, one detection per row, exact header:
`frame_index,class_id,confidence,x1,y1,x2,y2`. Index is zero-based decoded frame;
class15=CAT,16=DOG; endpoints are exclusive original pixels. Repeated frame indices
allow multiple boxes. Unlisted frames have no supplied detections. CSV is hashed
and mode is recorded as manual, not model evidence. There is no behavior label.

## 5. Interpret logs, metrics and evidence

Each `frames.jsonl` row includes source frame/timestamp, raw PTS, raw CAT count,
tracker-eligible count, tracked confidence/ID/bbox, observed/geometry-valid flags,
FOOD/WATER bottom-center distances and body-overlap fractions, reference point,
geometry state and normalized detections. Missing geometry values are null, not0.
A retained missed track bbox is explicitly marked unobserved. Behavior input is
always null and behavior_events is always empty.

Geometry states retain core naming: FAR, NEAR_FOOD, NEAR_WATER, APPROACHING_FOOD,
APPROACHING_WATER, LEAVING, AMBIGUOUS. With no observed cat, FAR is accompanied by
geometry_valid=false; it is not evidence of a cat physically far away.

- NEAR uses bbox_bottom_center distance OR sufficient body overlap.
- Hysteresis holds the previously near ROI using the exit distance, resetting on
  track change or loss of near context. This is geometry-only context, not FSM state.
- APPROACHING/LEAVING use normalized distance trend over retained timestamped boxes.
  The core's shared min_motion_per_second gate applies to both directions; no
  unvalidated separate leaving algorithm was added. Approach to the current/nearest
  target can take precedence over leaving another target.
- Multiple eligible cats or a body near both ROIs is ambiguous.
- Whole-body geometry is **not head position**, feeding, drinking, grams or preference.

`report.json` / `report.md` are explicitly **GEOMETRY VALIDATION**, with:

- Decoded/processed frames, sampling and termination/partial-scope reason.
- Raw CAT detections versus tracker-eligible detections (default0.5 gate, distinct
  from unchanged detector0.35 threshold).
- Observed-track fraction/longest observed run, ID changes, temporary-miss frames,
  miss episodes, reacquisitions, expirations and ambiguity.
- Estimated near FOOD/WATER time and geometry-state transition counts.
- FOOD/WATER minimum, median and nearest-rank p95 normalized distances, observed
  geometry only. Empty distributions are null.
- Source/manual/config and protected-production hashes, timing policy, evidence index.

Recorded timing prefers increasing rounded media PTS. If missing/duplicate/backward,
it locks to FPS-based increments anchored at the last good frame/timestamp and
reports fallback count. Invalid FPS is rejected if fallback is needed. FPS fallback
is approximate for VFR media; review before interpreting durations. Never uses
inference wall-clock speed for recorded motion.

Near time is a left-held sampled observation interval, assigned only when the
previous cat was observed and delta <= max_observation_gap_ms. No missing interval
or final tail is extrapolated. These are geometry proximity estimates, not actual
consumption durations. Early decode vs EOF cannot always be distinguished by OpenCV;
suspected truncation is flagged using advertised frame count, report retained and
exit status2. Explicit frame/time limits are partial scope, not whole-video PASS.

At most nine JPEGs, with frame/timestamp in the evidence index:
`first_cat`, `nearest_food`, `nearest_water`, `approaching_food`, `approaching_water`,
`leaving`, `ambiguous`, `track_lost` (first observation loss), `reacquired`.
Nearest snapshots replace only the tool's own current-run snapshot. Missing cases
are omitted, not invented. Existing output directories are always refused.
`INCOMPLETE.txt` remains if an exception interrupts an unfinished artifact set.

## 6. Threshold calibration policy

Each report preserves `config.used.json`, `calibration.used.json` and
`threshold_review.md`. No auto-optimization. Review across multiple sessions/days:

| Parameter | Meaning |
| --- | --- |
| geometry.near_distance / exit_distance | Normalized entry/exit hysteresis |
| geometry.min_body_overlap | Intersection / cat-body bbox area, not ROI IoU |
| geometry.min_motion_per_second / motion_window_ms | Shared approach/leaving trend |
| tracker.min_iou / max_centroid_distance | Association gates |
| tracker.min_confidence / ttl_ms | Eligibility and expiry |
| temporal.max_observation_gap_ms | Maximum held interval used for near-time metrics |

Record **BEFORE / candidate value / reason / AFTER** with manually reviewed
false-near/missed-near/track-break evidence. A candidate is not adopted merely
because one video looks better. To test a proposed threshold change, create a copy
of roi.candidate.json as a base JSON, edit explicit fields, then rerun calibrate
with `--base-config /path/to/threshold-base.json` and the same measured FOOD/WATER
pixel endpoints into a NEW directory. Threshold origin/base hash is retained.
Re-run at least distinct held-out sessions before adoption. No threshold change
was justified or adopted by the generated fixtures in this task.

## 7. Optional isolated live observation

Only on an available camera, after stopping any competing capture process:

```sh
"$TOOL" live --camera /dev/video0 --calibration "$RUN/calibration" \
  --detector trt --seconds 15 --max-frames 450 --out "$RUN/live_geometry"
```

Optional `--gui`. Live timing uses monotonic capture-received timestamps, not sensor
exposure time. Existing latest-slot capture may drop old frames; metrics describe
processed observations, not every sensor exposure. No ESP32/UART/servo/pump/feed
interface exists. Same-instance concurrency is not supported.

**Status:** code path provided, **NOT RUN ON A REAL CAMERA** in this task: no
`/dev/video0` existed at audit. GUI selection was not validated over X11.

## Executed validation and scope

```sh
sh scripts/test_geometry_validation.sh
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  SANITIZER=address,undefined sh scripts/test_geometry_validation.sh
TSAN_OPTIONS=halt_on_error=1 SANITIZER=thread sh scripts/test_geometry_validation.sh
```

- New pure native: **13 named cases,40,044 assertions**, including40,000 conversion
  stress iterations across four independent owner threads. PASS on Nano and host.
- CLI workflow: **17 named stdlib unittest cases PASS** on Nano, generated50-frame
  MP4/manual rectangles only. Python assertion count is not separately instrumented.
- Detector self-test: **21 assertions**, grouped into two suites inside one CLI case;
  exact production preprocessing/decoder across640x480,1280x720,480x640,641x479,
  <=1pixel round-trip tolerance for legacy integer truncation; class gates and NMS.
- ASan/UBSan: pure native and all17 CLI cases PASS, no reports. Leak detection is
  enabled for pure native; CLI/vendor-linked process leak scanning is disabled.
  Initial all-process leak-scan run exceeded300-second SSH timeout and is not a PASS.
- TSan:13 native cases/four-owner stress PASS. CUDA/OpenCV workflows and live camera
  are outside TSan scope; no shared-instance thread-safety claim.
- Real TensorRT engine / NEW adapter:5 generated MP4 frames processed, no behavior
  events. This is GPU integration smoke, not real animal or real-camera evidence.
- Existing exact engine/photo regression rerun: CAT0.927363, DOG0.879974, person
  photo NONE; six existing synthetic decoder/preprocess cases PASS.
- Existing shadow regression rerun:250,028 checks /80,000 paired replay iterations
  PASS, with four synthetic events correctly paired. No foundation rewrite.
- Full existing Python suite:344 PASS in26.96s. New script Ruff PASS.

No real MP4 found in audited Nano staging/media folders or `D:\for_cat\ai\datasets`.
No user footage was imported, labeled or claimed validated. No external download,
behavior training, production-history write, firmware or actuator change.

Full evidence, representative synthetic run and input fixtures (outside Git):
`/home/toan/for_cat/evidence/geometry_validation_20261017/`.
Normal initial tests: `/tmp/for-cat-geometry-tests.1uW07R`; final-source ASan/UBSan:
`/tmp/for-cat-geometry-tests.IwX49f`; TSan: `/tmp/for-cat-geometry-tests.P4IN9H`.

Protected hashes before/after:

```text
c3651fc3d1331b24a45c6a74b94a883e362fd4ded2412bb8f3ad195f1c443cdc  cat_dog_trt binary
48fe40017461d2e4edab33c47b30194b84ba7714e32e6d3d2aa4649f5b7471fb  engine
9b01288e4b6e450217d3029c2d0b4a3aecafb9dc0e2f87e17289d3e83f5b6366  cat_dog_trt.cpp
```

Next single task: stage **one actual fixed-camera MP4** (or its original frame),
mark/review the real RED/BLUE ROIs and run this tool. Until then, real ROI placement,
tracking accuracy and physical proximity quality remain unvalidated.
