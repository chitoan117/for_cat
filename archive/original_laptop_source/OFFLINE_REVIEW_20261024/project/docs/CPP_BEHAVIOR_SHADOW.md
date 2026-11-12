# C++14 single-cat behavior shadow foundation

## Scope and repository checkpoint

Implemented as a standalone library plus deterministic offline demo/tests under
`jetson/ai/shadow/`. It is **not linked into `cat_dog_trt`**. No behavior model is
trained or executed; the demo supplies explicitly synthetic behavior samples.
There is no camera, TensorRT, UART, actuator, database or HTTP dependency in the
core. This is software foundation validation, not physical/animal validation.

Starting Jetson/mirror checkpoint: `b70a5d4`, four local commits ahead of
`origin/main` (`8511ea0`). Existing untracked `cat_dog_trt.cpp.bak_latency` is
preserved. No branch history was rewritten or pushed.

Audited/reused contracts:

- Python `TrackLedger`: useful TTL/budget concepts, but receives caller IDs and
  does not associate detections. The new native tracker supplies that missing step.
- `vision/geometry.py`: normalized positive-area rectangles and overlap concepts.
- `behavior/temporal.py`: elapsed confirmation, dropout and paired START/END ideas.
  Its OWNER/OTHER identity contracts remain intact; this native stage is single-cat.
- `behavior/fusion.py`: consumption requires validated stable sensor measurements.
  Native events expose absent weight hooks; they do not estimate camera grams.
- `storage/records.py`, repositories/history/event store and REST routes: existing
  typed records, UTC event timestamps and projections remain unchanged. Native
  events are not directly compatible persistence records.
- Existing ROI template and RED/FOOD, BLUE/WATER, BLUE_FLOOR_LINE conventions.

## Files and boundaries

| File | Role |
| --- | --- |
| `jetson/ai/shadow/behavior_shadow.h` | Public plain C++14 contracts |
| `jetson/ai/shadow/behavior_shadow.cpp` | Tracker, geometry, temporal FSM, events |
| `jetson/ai/shadow/shadow_json.cpp` | Strict bounded config reader; event JSONL serialization |
| `jetson/ai/shadow/shadow_demo.cpp` | Synthetic sequences only, stdout JSONL |
| `jetson/ai/shadow/test_behavior_shadow.cpp` | Deterministic, malformed-input and stress tests |
| `jetson/ai/shadow/test_config.synthetic.json` | Invented test coordinates, explicit opt-in |
| `jetson/ai/roi_config.example.json` | Deployment template: null ROIs, fails closed |
| `scripts/test_behavior_shadow.sh` | Scratch-only build, tests, JSON smoke |

`Pipeline` owns one tracker, at most one candidate and one active session. It
returns bounded snapshots and events; it never accumulates an event log. Caller
must consume events and bound its own queues. One owner thread per instance;
concurrent calls to the **same** instance are not supported. Independent instances
have no shared mutable state.

### Input adapter contract

```cpp
behavior_shadow::Pipeline pipeline(config, {"optional-trial-id", "optional-food-id"});
// detections contain original-frame NORMALIZED boxes, not letterboxed network boxes.
// The caller maps only detector COCO class 15 to Object::Cat; class 16 is Dog.
// A future behavior executor supplies a real sample, or leaves it absent.
auto observation = pipeline.update(monotonic_ms, detections, optional_behavior_sample);
for (const auto& event : observation.events) {
    // Internal shadow processing only; JSONL is available via event_json(event).
}
```

The validated detector's `cv::Rect` is in original-image pixels. A future adapter
must normalize x by original width and y by original height, preserve timestamp
provenance, and explicitly validate/clamp detector output before this interface.
No such adapter is installed in the production detector by this change.

`Millis` is nonnegative signed int64 monotonic milliseconds from a single clock
domain. Updates must strictly increase. Rejecting malformed detection/sample
input does not advance the clock or tracker. The API rejects invalid boxes,
nonfinite confidence, future timestamps, invalid enum/track ID, and >1024 detections.
The caller must issue heartbeat updates, including empty detections when absent;
no timer or background thread emits END if the caller stops entirely.

Behavior input is `{label, confidence, timestamp_ms, optional track_id}`.
Accepted labels: EATING, DRINKING, IDLE, UNKNOWN, UNSURE. No input is distinct
from IDLE. Unknown/unsure/low-confidence/stale samples cannot assert consumption.
The timestamp must be within the behavior age budget, newer than the previous
pipeline update, and not earlier than this track's creation. A supplied track ID
must match. Thus one cached sample cannot keep confirming across many updates.
Unbound samples are accepted only for a currently observed, unambiguous single cat.

## Tracker

One eligible CAT: associate with current track if IoU >= configured gate **or**
normalized bbox-centroid distance <= configured gate. This is intentionally
lightweight for one fixed-view cat, not Re-ID or multi-object tracking. IoU handles
small bbox jitter; the bounded centroid gate bridges modest low-IoU motion.

- Track has ID, bbox, created/last_seen/age, consecutive misses, observed flag and
  bounded timestamped bbox history (default32, permitted2..512).
- Missing, far-unmatched or multiple eligible cats do not refresh last_seen.
- Multiple cats are explicitly ambiguous; do not choose a highest-score identity.
- Keep an unmatched old track through TTL; do not immediately reassign a distant cat.
- Expire when `now-last_seen > ttl_ms`, inclusive boundary retained. Reacquisition
  before expiration can preserve ID; acquisition after expiration gets a new ID.
- DOG/OTHER and low-confidence CAT do not create cat tracks.
- IDs are process-instance-local counters; they are not durable animal identities.

## ROI and geometry

Deployment template stays `NOT_CONFIGURED_TEMPLATE_ONLY`, with null ROIs/line.
The reader requires `CONFIGURED` and measured normalized original-frame rectangles.
Synthetic fixture status is `SYNTHETIC_TEST_ONLY` and requires explicit opt-in.
Threshold defaults are uncalibrated proposals, not deployment measurements.

Strict validation rejects missing/unknown/duplicate fields, malformed JSON, numeric
coercions (including bool-to-number), nonfinite numbers, invalid UTF-8, out-of-range
or zero/inverted/underflow-area rectangles, positive food/water ROI overlap, invalid
line endpoints, invalid timing/budgets and reversed entry/exit hysteresis. Touching
ROI edges are allowed, but a bbox spanning both near regions is ambiguous.

Reader limits: 64KiB input, 16 nesting depth, 2048 values, 4096 bytes/string. It
supports JSON objects, strings/escapes/UTF-8, finite numbers, booleans and null;
arrays are not part of this schema and are rejected. No comments/trailing commas.
All tracker/geometry/temporal fields shown in the template are required. Approach
line may be null; non-null uses x1/y1/x2/y2 as endpoints, including horizontal or
reversed endpoints. It is a stored reference, not a homography or a trigger.

An actual Nano probe found OpenCV4.8.0 `FileStorage` rejects JSON null and represents
booleans as integer nodes. No nlohmann header is installed. Consequently the
separate bounded reader preserves null/number/bool distinctions without an added
package or coupling the core to OpenCV.

**RED BOWL = FOOD_ROI. BLUE BOWL = WATER_ROI.** Geometry uses explicitly named
`bbox_bottom_center` plus body-box intersection/body area. Neither is head
localization, nor evidence of actual biting/drinking. Euclidean distances are
normalized image units (x/width, y/height), affected by aspect ratio/perspective,
**not centimetres**. No calibration/homography is inferred from the blue floor line.

Near if bottom-center distance <= entry threshold or body overlap >= threshold.
An active/candidate ROI uses the larger exit threshold to reduce jitter. Near both
is AMBIGUOUS and cannot confirm behavior. Missing detections never reuse old
geometry as fresh evidence.

Motion uses the oldest retained observation within the configured time window and
normalized distance change per elapsed second. Outputs FAR, NEAR_FOOD,
NEAR_WATER, APPROACHING_FOOD, APPROACHING_WATER, LEAVING or AMBIGUOUS. Approach
to the current/nearest target takes precedence over leaving the previous target.
These are logic observations, **not new AI labels**; motion alone emits no session.

## Temporal smoothing and FSM

Defaults (all configurable milliseconds): confirmation1000, dropout800,
minimum active state1000, maximum update gap500, maximum behavior age250.
Confidence default0.7. Defaults require calibration on real annotated footage.

Confirmation uses elapsed time between qualifying observations, not frame votes.
Short unknown/unsure/missing evidence is tolerated up to dropout (inclusive), but
confirmation still requires fresh positive evidence at the current update. Explicit
IDLE or contradictory/wrong-ROI behavior resets a candidate. A candidate is also
reset by evidence timeout, track replacement/expiration or excessive update gap.
Continuous maximum-gap-bounded ticks are required; a sparse pair cannot confirm.

| Current | Condition | Next / event |
| --- | --- | --- |
| NO_CAT | Single cat acquired | OBSERVING |
| OBSERVING | Fresh confident EATING + near FOOD | CONFIRMING_EATING |
| OBSERVING | Fresh confident DRINKING + near WATER | CONFIRMING_DRINKING |
| CONFIRMING_* | Same eligible evidence across confirmation duration | EATING/DRINKING + one START |
| CONFIRMING_* | Short unknown/missing evidence | Keep candidate; no START without positive evidence |
| CONFIRMING_* | IDLE/contradiction, timeout, long update gap or new track | Reset; optionally start a fresh qualifying candidate |
| EATING/DRINKING | Same qualifying evidence | Refresh confidence/last-positive; no duplicate START |
| EATING/DRINKING | Short evidence loss, departure or ambiguity | Hold through dropout/minimum state duration |
| EATING/DRINKING | Evidence expired AND minimum duration met | END, then OBSERVING or new candidate |
| EATING/DRINKING | Excessive update gap or lost/replaced track | END immediately at this update; reset |
| Any inactive state | Track expires | NO_CAT |

EATING at WATER and DRINKING at FOOD are not positive evidence. Opposite behavior
cannot start a second concurrent session. Minimum duration delays an ordinary
evidence-timeout END; track loss and clock gaps override holding a state. They can
end before the minimum. If valid evidence returns while held within the minimum,
the active state may resume; after expiration/minimum it must reconfirm.

START is timestamped at **confirmation**, not retroactively at candidate onset.
For END, logical end is
`min(now, max(start + min_state_ms, last_positive + dropout_ms))`, with saturating
deadline arithmetic. Emission is at current update time, possibly later. This
held-state duration is not continuous ground-truth chewing time. A long silent
caller gap does not inflate the session to the arrival timestamp. End reason
distinguishes EVIDENCE_TIMEOUT, OBSERVATION_GAP, TRACK_LOST. END is emitted once.

## Event contract and future persistence bridge

Native/JSONL event v1 includes event type, shadow flag, monotonic clock domain,
track/session IDs, emitted/start/end/duration, ROI, end reason, geometry-reference
description, confidence count/mean/min/max, optional trial/food IDs, nullable
weight_before/weight_after/consumed_grams. START end/duration are null. START/END
share IDs. Confidence summarizes accepted matching positive samples, including
confirmation evidence; it is not a calibrated session probability.

Metadata IDs are optional printable ASCII, maximum128 bytes each. Empty means
unspecified. Weight hooks remain absent; serializer refuses non-null weight hooks
until a validated integration exists. It also refuses events marked non-shadow.
The pipeline supplies no API to authorize feeding or request a pump.

Future persistence adapter must explicitly map process-local IDs to durable run/
session IDs, establish monotonic-to-UTC anchoring, validate attribution/quality,
translate to existing typed records, and make inserts idempotent. Do not write
synthetic demo events into production history or treat monotonic milliseconds as
UTC. No SQLite/REST migration is required or implemented by this foundation.

## Food-preference measurement hooks

Optional trial/food IDs attach experiment context only. Future reviewed analysis
may measure approach latency, first-bite latency, confirmed consumption duration,
validated grams, return visits and refusal. Neither geometry nor EATING alone
means LIKE/DISLIKE; no preference classifier/scoring is added. Approach/first-bite/
refusal/visit attribution and sensor fusion still need explicit validated adapters.
Variants initially use the same RED ROI across sessions; BLUE remains WATER.
Manually filled bowls do not require a servo event to be analyzed, but stable
validated pre/post HX711 measurements are still required before reporting grams.

## Exact build and offline checks

On Nano, from `/home/toan/for_cat` (script uses a NEW `/tmp` scratch directory):

```sh
sh scripts/test_behavior_shadow.sh
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  SANITIZER=address,undefined sh scripts/test_behavior_shadow.sh
TSAN_OPTIONS=halt_on_error=1 SANITIZER=thread sh scripts/test_behavior_shadow.sh
```

Manual standalone build (no OpenCV/TensorRT link flags):

```sh
test -d /tmp
BUILD=$(mktemp -d /tmp/for-cat-shadow-manual.XXXXXX)
g++ -std=c++14 -O1 -g -Wall -Wextra -Werror -Wconversion -Wshadow -Wpedantic \
  -pthread -fno-omit-frame-pointer jetson/ai/shadow/behavior_shadow.cpp \
  jetson/ai/shadow/shadow_json.cpp jetson/ai/shadow/test_behavior_shadow.cpp \
  -o "$BUILD/test_behavior_shadow"
g++ -std=c++14 -O1 -g -Wall -Wextra -Werror -Wconversion -Wshadow -Wpedantic \
  -pthread -fno-omit-frame-pointer jetson/ai/shadow/behavior_shadow.cpp \
  jetson/ai/shadow/shadow_json.cpp jetson/ai/shadow/shadow_demo.cpp \
  -o "$BUILD/shadow_demo"
"$BUILD/test_behavior_shadow" jetson/ai/shadow/test_config.synthetic.json jetson/ai/roi_config.example.json
"$BUILD/shadow_demo" --synthetic jetson/ai/shadow/test_config.synthetic.json
```

## Executed verification

Actual Nano g++7.5.0, C++14 strict warnings-as-errors:

| Run | Result | Preserved scratch output |
| --- | --- | --- |
| Native | 250,028 checks PASS | `/tmp/for-cat-shadow.6YViPV` |
| ASan + UBSan + leak detection | Same checks PASS, no reports | `/tmp/for-cat-shadow.swR3yN` |
| ThreadSanitizer | Same checks PASS, no reports | `/tmp/for-cat-shadow.6cYj9x` |

Each includes tracker/TTL/history, geometry/motion/hysteresis, elapsed FSM, stale/
mismatched/reused samples, wrong-ROI and contradictory evidence, long silent gaps,
invalid/numeric-budget cases, parser malformed/truncation/2000 seeded mutations,
and 80,000 paired deterministic replay updates across four independent owner
threads. TSan covers independent instances, not a promise of same-instance
concurrent access. Each demo emits four synthetic START/END events, reparsed by
Python stdlib with pairing/duration/null-weight assertions; unconfigured template
is refused. Initial GCC portability warning in test PRNG narrowing was corrected
before the reported successful runs.

Final-source host Zig/Clang strict C++14: **250,028 checks PASS**.
Existing full Python suite: **344 PASS in21.55s** with
`-B -m pytest -q -p no:cacheprovider`, external unique basetemp. No Python source or
contract changes were made. Physical animal accuracy, calibrated ROI quality and
production performance impact are **not tested**; this library is not deployed.

Full SSH evidence JSON (commands, stdout/stderr, exit code and timestamps) and
synthetic event outputs are archived outside Git under
`/home/toan/for_cat/evidence/shadow_foundation_20261017/`.

Protected artifact hashes before/after must remain:

```text
c3651fc3d1331b24a45c6a74b94a883e362fd4ded2412bb8f3ad195f1c443cdc  jetson/ai/cat_dog_trt
48fe40017461d2e4edab33c47b30194b84ba7714e32e6d3d2aa4649f5b7471fb  models/tensorrt/yolov8n_320_fp16.engine
```

Production source, model/bindings, camera pipeline, Python API/storage, ESP32/UART
and safety flags are unchanged. `AI_SHADOW_MODE=true`,
`automatic_feed_authorized=false`, `ACTUATOR_OUTPUTS_ENABLED=0` remain in force.

Additive tooling now exists for original-frame capture, ROI calibration/overlay,
recorded-video detector/tracker/geometry validation and optional isolated live
observation: see `GEOMETRY_CAMERA_VALIDATION.md`. It calls tracker/geometry only;
the existing core/FSM remain unchanged. No real fixed-camera footage was available,
so deployment ROI calibration still needs an actual frame and human review. Keep
the template unconfigured until that evidence exists. Behavior training, production
integration and physical validation remain separate work.
