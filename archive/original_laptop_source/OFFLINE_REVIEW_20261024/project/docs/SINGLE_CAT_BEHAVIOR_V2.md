# Single-cat Behavior V2 — dataset preparation, not a trained runtime

Current scope is ONE cat. `OWNER_CAT` / `OTHER_CAT` are legacy/future identity
contracts, not Behavior V2 requirements. Production inference stays C++/OpenCV/
TensorRT/CUDA. Python here is OFFLINE tooling on a host with Python >=3.10.

**Current production video workflow:** [BEHAVIOR_V2_VIDEO_WORKFLOW.md](BEHAVIOR_V2_VIDEO_WORKFLOW.md)
adds directory import/provenance, safe reruns, quality flags, human interval annotation
and correction, source-group split and JSON/Markdown readiness. The lower-level
single-video commands below remain supported. No real video is automatically labeled.

## Versioned contracts

- Existing metadata without `schema_version` is v1. Its enums/history are unchanged.
- Extract with `--schema-version 2` to create explicit v2 rows, initially unlabelled
  and `usable=false`. No video-wide behavior is inferred automatically.
- V2 `subject_label`: CAT / NONE / UNKNOWN / UNSURE / SKIP.
- V2 trainable behavior order: **0 EATING / 1 DRINKING / 2 IDLE**.
- `identity_label:null` is retained ONLY as a legacy storage compatibility slot;
  the annotator does not supply an identity and no owner classifier is required.
- EATING: actual eating at the RED food bowl. DRINKING: actual drinking at the
  BLUE water bowl. IDLE: a present cat not consuming, including approach, sniff,
  looking, pausing or passing nearby. Nearness alone is not EATING.
- NONE means no subject and requires NONE behavior; it is preserved but excluded
  from the cat-behavior classifier. UNKNOWN/UNSURE stay review/unusable. They are
  never silently converted to IDLE. `usable=true` requires a confirmed CAT and
  one of the three trainable behaviors.
- `ai/datasets/schema_v2.json` documents the format. `ai.dataset.validate_row`
  enforces the version-specific contract. `--task behavior_v2` explicitly selects
  the new map for release/export/training-plan/evaluation metadata.

## Existing tools reused

No new extractor, deduplicator, or splitter was introduced. These commands reuse
`import_video.py`, `extract_frames.py`, `label_dataset.py`, `split_dataset.py`,
`sampling.py`, `dataset.py`, `releases.py` and `interchange.py`.

From repository root on the OFFLINE host, set paths to an operator-supplied video
and a NEW versioned dataset directory. No external data is downloaded:

```bash
DATA="$PWD/ai/datasets/behavior_v2_pilot_001"
VIDEO="/absolute/path/to/operator_supplied_session_01.mp4"

# First inspect the receipt. Default is dry-run; it does not copy anything.
python -m ai.scripts.import_video "$VIDEO" --session-id cat_s01 --dataset "$DATA"
python -m ai.scripts.import_video "$VIDEO" --session-id cat_s01 --dataset "$DATA" --apply

# Set this to source_video from the actual receipt, not the original video basename.
SOURCE="video-REPLACE_WITH_RECEIPT_HASH.mp4"
python -m ai.scripts.extract_frames "$SOURCE" --session-id cat_s01 --dataset "$DATA" \
  --schema-version 2 --interval-seconds 0.5 --minimum-spacing 0.5 --max-frames 300
python -m ai.scripts.extract_frames "$SOURCE" --session-id cat_s01 --dataset "$DATA" \
  --schema-version 2 --interval-seconds 0.5 --minimum-spacing 0.5 --max-frames 300 --apply
```

Repeat with DIFFERENT session IDs for the other two videos. Three two-minute clips
yield approximately 720 samples before duplicate/quality review, not a guaranteed
usable count. Exact duplicates are skipped; near-duplicates are warnings to review,
not automatic semantic deletions. Review blur, transitions, occlusions and redundant
frames manually. Keep the original videos and source hashes.

Annotate actual sample IDs from `manifest.jsonl` after viewing each frame/context:

```bash
SAMPLE="s-REPLACE_WITH_ACTUAL_SAMPLE_ID"
python -m ai.scripts.label_dataset "$SAMPLE" --dataset "$DATA" --subject CAT --behavior IDLE --apply
# Other samples, after actual review:
# --subject CAT --behavior EATING
# --subject CAT --behavior DRINKING
# --subject NONE --behavior NONE          (preserved, not classifier training)
# --subject UNKNOWN --behavior UNSURE    (preserved, not classifier training)

python -m ai.scripts.split_dataset --dataset "$DATA" --seed 42
python -m ai.scripts.split_dataset --dataset "$DATA" --seed 42 --apply
python -m ai.scripts.dataset_release validate --dataset "$DATA" --task behavior_v2 --near-limit 1000
python -m ai.scripts.dataset_release validate --dataset "$DATA" --task behavior_v2 \
  --stage TRAINING_CANDIDATE --near-limit 1000
python -m ai.scripts.prepare_training --dataset "$DATA" --task behavior_v2
```

`prepare_training` prepares metadata ONLY; it never trains a model. No trainer is
started by this workflow. Dataset writes require explicit `--apply`; output/split
overwrites are refused. Use a new dataset version instead of deleting old work.
Current splitter retains its established approximately 70/15/15 SESSION allocation;
with three sessions it allocates one per split. It does not shuffle individual frames.
Validation also rejects source-video hash aliases spanning splits. A three-session
pilot may lack class/diversity coverage; failed TRAINING_CANDIDATE gates must not be
silenced to obtain a convenient ratio. Video-backed V2 candidates now use the full
budgeted video-readiness scan; legacy/photo-only checks retain their old bounded
policy. Truncated checks remain flagged rather than implying independence.

Classification export/round-trip remains local and keeps source/session provenance:

```bash
python -m ai.scripts.dataset_release export --dataset "$DATA" --task behavior_v2 \
  --output /absolute/new/behavior_v2_export --apply
```

The export has `images/EATING`, `images/DRINKING`, `images/IDLE` and a mandatory
provenance sidecar. Public/Roboflow data is optional supplementary data later,
never a replacement for deployment webcam sessions. Preserve source/session groups,
and reserve real unseen deployment sessions/days for evaluation. Import without
session provenance is rejected rather than random-splitting nearby frames.

## ROI/tracker/temporal: standalone C++ shadow foundation implemented

`CPP_BEHAVIOR_SHADOW.md` documents the implemented C++14 single-cat tracker,
normalized ROI reader/geometry, timestamped behavior interface, time-based FSM,
shadow events and offline tests. Actual Nano native/ASan/UBSan/TSan checks PASS.
It is separate from `cat_dog_trt`; no behavior model or production bridge exists.

`GEOMETRY_CAMERA_VALIDATION.md` now provides isolated original-frame calibration,
visual overlay, recorded-video CAT/tracker/geometry logs/reports and an optional
live command. No behavior model or behavior assertions are needed. Tooling tests
use generated media; actual fixed-camera ROI placement still needs human review.

`jetson/ai/roi_config.example.json` is an UNCONFIGURED template; the current CAT/DOG
executable does not load it or classify behavior. Camera must remain fixed. Fill
measured normalized original-frame coordinates later: RED=FOOD_ROI, BLUE=WATER_ROI,
BLUE FLOOR LINE=approach reference. Do not invent coordinates from textual descriptions.

Prepared future production path: C++ CAT detector -> lightweight IoU/centroid association
(track ID/last seen/TTL/bbox history) -> calibrated ROI/distance evidence -> small
EATING/DRINKING/IDLE classifier -> monotonic-time confirmation/grace windows ->
START/END events. APPROACHING/NEAR_FOOD/NEAR_WATER/LEAVING are geometry/FSM states,
not extra trainable classes. Whole-cat bbox center is not head position; any head
localization must be separately designed/validated. Full homography is not required
for the initial normalized/pixel-distance pilot.

Existing TemporalEngine ideas are reused conceptually by the standalone native
stage; storage needs a later explicit single-cat adapter. Legacy identity enums
are not mass-replaced. Do not plug a
three-class behavior engine into the COCO `1x84x2100` detector binding contract.

HX711 supplies calibrated stable pre/post weight, not camera gram estimation. Target
records: start/end/duration/weight_before/weight_after/consumed_grams. Existing fusion
needs later integration for manually filled bowls. No HX711 firmware was modified.
DRINKING is observation only; pump refill remains water sensor -> ESP32 safety.
Preference experiment metadata is optional and non-trainable. Initially compare
variants across separate sessions at the SAME red FOOD_ROI. BLUE stays WATER.
Simultaneous two-food A/B or position swapping requires a separate future experimental
layout, never a silent WATER_ROI redefinition. Consumption/visit analysis remains future;
no LIKE/DISLIKE model, training, automatic feeding or public download occurs.
