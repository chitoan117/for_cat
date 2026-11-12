# Real-video Behavior V2 workflow

Offline dataset tooling, Python >=3.10. Production inference remains the validated
C++14 binary. Do not install host OpenCV wheels or replace system Python on Nano.
No behavior training, external download, AI ground-truth labeling or actuation is run.

## Layout (same structure on Windows host or an ignored Jetson staging root)

```text
behavior_v2_real/
  incoming/<unique_upload>/              # original staged copies, never deleted by tools
  raw/video-<hash-prefix>.mp4            # independent copied bytes, not links to originals
  sources.jsonl                         # session ID, full SHA256, original names/aliases,
                                        # import UTC, media properties, experiment metadata
  processed/s-<stable-source-frame-id>.jpg
  manifest.jsonl                        # v2 labels/nulls, source offsets, frame index,
                                        # sample sequence, timing basis, image SHA, quality flags
  extractions/<session-id>.json          # settings, decode/duplicate/limit counters
  annotations/<session-id>.json          # operator-reviewed interval recipe
  annotations/history/<revision>/       # immutable preimage + correction receipt
  splits.json
  split_history/<revision>.json
  reports/<run>/readiness.json
  reports/<run>/readiness.md
```

`ai/datasets/behavior_v2_*/` is ignored by Git. A host dataset outside the repository
is also recommended. Never commit videos, processed frames, models or engines.
Session IDs depend on FULL source SHA (collision checks included), not filename/order.
Identical videos, even renamed or with a different extension, reuse the same source
session; aliases are retained. Same basename/different content gets a different ID.

## 1. WINDOWS POWERSHELL — source checkout and staging

The latest validated commits may exist only on the Jetson. Clone its repository to
a NEW host directory instead of overwriting an older Windows snapshot:

```powershell
git clone ssh://toan@server-jetson.local/home/toan/for_cat "D:\for_cat_host"
Set-Location -LiteralPath "D:\for_cat_host"
# Use an existing Python >=3.10 environment, or explicitly prepare a HOST-only venv:
py -3 -c "import sys; assert sys.version_info >= (3,10), sys.version"
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt opencv-python
$Py = (Resolve-Path .\.venv\Scripts\python.exe).Path

$Videos = "D:\Cat Videos"   # CHANGE to the real source folder, spaces/Unicode allowed
$Dataset = "D:\for_cat_data\behavior_v2_real"
$Upload = (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + ([guid]::NewGuid().ToString('N').Substring(0,8))
$Incoming = Join-Path $Dataset "incoming\$Upload"
New-Item -ItemType Directory -Force -Path (Split-Path $Incoming) | Out-Null
if (Test-Path -LiteralPath $Incoming) { throw "Staging destination exists" }
Copy-Item -LiteralPath $Videos -Destination $Incoming -Recurse
```

This COPIES; it does not move/delete originals. Keep the dataset/staging root ASCII
where practical: OpenCV Windows can fail on Unicode video paths. Import uses Python
filesystem APIs for Unicode source filenames, then probes/decodes the anonymized
ASCII raw copy. Original Unicode names remain in the UTF-8 metadata. JSON files with
a Windows UTF-8 BOM are accepted.

### Optional Windows -> Jetson archival staging (not modern processing on Python3.6)

```powershell
$Jetson = "toan@server-jetson.local"
$RemoteStage = "/home/toan/for_cat/ai/datasets/behavior_v2_real/incoming/$Upload"
ssh $Jetson "test -d /home/toan/for_cat/ai/datasets; test ! -e '$RemoteStage' && mkdir -p '$RemoteStage'"
if ($LASTEXITCODE -ne 0) { throw "Remote staging not created; do not overwrite" }
scp -r "$Incoming" "${Jetson}:$RemoteStage/"
```

Use a unique upload directory; do not flatten folders with colliding filenames.
DHCP fallback: run `hostname -I` on Jetson/MobaXterm/console, identify the current
address, then set `$Jetson="toan@CURRENT_ADDRESS"`. No static LAN IP is embedded in code.
Raw files may be staged at `/home/toan/for_cat/ai/datasets/behavior_v2_real/incoming/`.
Run the following processing commands on the HOST with Python >=3.10, using its local
copies. Do not run the modern modules with Nano's system Python3.6.

## 2. HOST PYTHON >=3.10 — one-command preparation or separate steps

PowerShell, from the updated repository root with `$Py/$Incoming/$Dataset` above:

```powershell
# Dry-run: source hashes/metadata plan; no import, extraction or labels are written.
& $Py -m ai.scripts.prepare_behavior_v2 prepare --videos-dir "$Incoming" --dataset-root "$Dataset"

# Apply copies/imports and extracts 2 FPS. It NEVER labels or silently resplits.
& $Py -m ai.scripts.prepare_behavior_v2 prepare --videos-dir "$Incoming" --dataset-root "$Dataset" --apply

# Or separate steps; both are safe to rerun:
& $Py -m ai.scripts.prepare_behavior_v2 import --videos-dir "$Incoming" --dataset-root "$Dataset" --apply
& $Py -m ai.scripts.prepare_behavior_v2 extract --dataset-root "$Dataset" --apply
& $Py -m ai.scripts.prepare_behavior_v2 sessions --dataset-root "$Dataset"
```

`prepare/report` exit 2 with valid JSON `NOT_READY` until gates pass; that is not a
fabricated import failure. Extraction errors are reported per session, retaining
other completed sessions and source files. `--max-frames 10000` is the default bound.
Existing single-source `import_video.py` and `extract_frames.py` remain available;
the orchestration calls these same modules, not another extractor/deduplicator.

Every new frame is `subject_label:null`, `behavior_label:null`, `usable:false`.
No filename, directory name or video-level intent becomes a behavior label.
Resume verifies stored image hashes and preserves annotations byte-for-byte.
Changing the sampling/encoding policy cannot silently replace an annotated dataset;
use a new version if the tool reports a policy/content conflict.

## 3. Efficient human interval annotation

Copy a real session ID from the `sessions` output:

```powershell
$Session = "v-REPLACE_WITH_REAL_SESSION_ID"
$Intervals = Join-Path $Dataset "annotations\$Session.json"
& $Py -m ai.scripts.prepare_behavior_v2 template --dataset-root "$Dataset" --session-id "$Session" --output "$Intervals" --apply
notepad "$Intervals"
```

The template has the real source hash but empty intervals and
`annotation_source:HUMAN_REVIEW_REQUIRED`; it cannot be applied as truth.
After WATCHING the original video, fill intervals and explicitly change the marker
to `HUMAN_REVIEWED`. Example ONLY, not annotations for any real recording:

```json
{
  "schema_version": 2,
  "session_id": "REPLACE_WITH_TEMPLATE_VALUE",
  "source_hash": "RETAIN_THE_TEMPLATE_SOURCE_HASH",
  "annotation_source": "HUMAN_REVIEWED",
  "reviewer": "operator",
  "intervals": [
    {"start":"00:00.0", "end":"00:08.5", "label":"IDLE"},
    {"start":"00:08.5", "end":"00:34.0", "label":"EATING"},
    {"start":"00:34.0", "end":"00:40.0", "label":"IDLE"}
  ]
}
```

Intervals are half-open `[start,end)`, non-overlapping. Gaps stay UNANNOTATED.
Allowed: EATING/DRINKING/IDLE/NONE/UNKNOWN/UNSURE. Trainable behaviors imply a
confirmed CAT; NONE/UNKNOWN/UNSURE are unusable classifier observations, never IDLE.
Default 0.25-second transition padding marks uncertainty as UNSURE; explicit
UNKNOWN/UNSURE intervals are preserved. Use `--boundary-label UNKNOWN` or
`--boundary-seconds 0` after reviewing boundaries. Consecutive equal labels do not
create an artificial transition.

```powershell
& $Py -m ai.scripts.prepare_behavior_v2 annotate --dataset-root "$Dataset" --intervals "$Intervals"
& $Py -m ai.scripts.prepare_behavior_v2 annotate --dataset-root "$Dataset" --intervals "$Intervals" --apply
# Explicit correction AFTER editing/reviewing the recipe:
& $Py -m ai.scripts.prepare_behavior_v2 annotate --dataset-root "$Dataset" --intervals "$Intervals" --replace --apply
```

`--replace` replaces the WHOLE session annotation: gaps become unannotated instead
of leaving stale labels. A preimage manifest and recipe receipt are saved BEFORE
atomic commit in `annotations/history`. Reapplying identical annotations is a no-op.
Single-frame CLI corrections can use `label_dataset SAMPLE --subject CAT --behavior
IDLE --replace --apply`; no manual mass-edit is required. No AI prelabels are accepted.

## 4. Source-session split and readiness

```powershell
& $Py -m ai.scripts.prepare_behavior_v2 split --dataset-root "$Dataset"
& $Py -m ai.scripts.prepare_behavior_v2 split --dataset-root "$Dataset" --apply
# Only if a deliberate revised split is needed after adding sessions:
# ... split --dataset-root "$Dataset" --refresh --apply
& $Py -m ai.scripts.prepare_behavior_v2 report --dataset-root "$Dataset" --apply
```

Report JSON names its new `report_files.json/markdown` paths. To choose a NEW output:

```powershell
$Report = Join-Path $Dataset "reports\review_$Upload"
& $Py -m ai.scripts.prepare_behavior_v2 report --dataset-root "$Dataset" --output-dir "$Report"
Get-Content -LiteralPath (Join-Path $Report 'readiness.md') -Encoding UTF8
```

70/15/15 is by GROUP, not frame. Source aliases and optional experiment pair groups
stay together. Fewer than three independent groups returns NOT_READY without writing
a misleading split. Existing splits are unchanged on rerun; a changed split needs
explicit `--refresh` and saves the previous split. Sessions do not cross folds.

READY_FOR_PILOT_TRAINING requires >=3 independent groups, nonempty folds, all three
trainable labels in every fold, >=10 usable samples per class by default, complete
source/image/provenance checks, no structural session/source/hash leakage and a
complete near-check. Eating-only footage remains NOT_READY. Technical readiness
does not certify ground truth/accuracy or start training.

Blur is a Laplacian-variance heuristic at a bounded scale, normally a FLAG, not
automatic removal. Exact duplicates are skipped and counted; near matches are
warnings, not proof. Suspicious cross-fold near matches block readiness pending
review. Inspect original recordings; for genuinely independent but similar videos:

```powershell
$Near = Join-Path $Dataset 'annotations\near_review.json'
& $Py -m ai.scripts.prepare_behavior_v2 near-review-template --dataset-root "$Dataset" --output "$Near" --apply
notepad "$Near"
# Only after review: set review_source=HUMAN_REVIEWED_SOURCE_SESSIONS and meaningful notes.
& $Py -m ai.scripts.prepare_behavior_v2 report --dataset-root "$Dataset" --near-review "$Near" --apply
```

The review is bound to the current manifest hash and complete source-pair scope.
It cannot override confirmed leakage or an incomplete near-check. Correct labels
invalidate stale reviews. Do not discard legitimate footage just to silence a dHash.

Resource limits are explicit: 20 GB/source, 10,000 retained samples/video, 100,000
decoded frames/video, 200 MB manifest, 20 MB source catalog; near comparisons have
a configurable bounded budget (`--near-comparison-limit`, max 20,000,000). Identical
dHash signatures are aggregated to avoid quadratic work on static scenes. Limit or
premature decode flags mean NOT_READY, not silent completeness. Do not split one
long recording into falsely independent train/test sessions to bypass a limit.

Source timestamps prefer decoder POS_MSEC; FPS/index fallback is recorded and warned.
Source duration from average FPS/frame count and retained-sampling-cell label durations
are ESTIMATES, not wall-clock capture UTC or total eating/consumption measurements.
Spot-check VFR or fallback timing before labeling. Originals are never deleted.
The cooperative writer lock prevents concurrent tool updates; inspect PID before
handling a stale lock after a killed process. Never remove a live writer's lock.
Atomic metadata/preimages protect process interruptions; hardware power-loss recovery
is not independently validated. Local NTFS/ext4 hard-link support is required to
publish verified raw COPIES atomically; originals are not hard-linked into the dataset.

## 5. Food-preference metadata, never labels

Optional `--session-metadata metadata.json` on INITIAL import/prepare:

```json
{
  "defaults": {"food_bowl_position":"RED_FOOD_ROI"},
  "videos": {
    "an A.mp4": {"preference_trial_id":"trial_01", "food_variant":"square_kibble", "trial_order":1, "session_pair_or_group":"pair_01", "notes":"same red food ROI"},
    "an B.mp4": {"preference_trial_id":"trial_02", "food_variant":"bone_kibble", "trial_order":2, "session_pair_or_group":"pair_01"}
  }
}
```

Keys are exact relative filenames from the incoming root. Unmatched keys are
reported. Session context is retained in source receipts, frames and per-session
report metadata; conflicting reruns cannot silently redefine it. Pair/group values
join related sessions in one fold: do not give every unrelated clip the same group.

**RED = FOOD_ROI; BLUE = WATER_ROI always in normal Behavior V2.** Compare food
variants across sessions using the SAME red FOOD_ROI initially. No LIKE/DISLIKE
classes. Future preference analysis uses approach/first-bite latency, duration,
validated grams, return visits/refusal. A future simultaneous A/B two-food layout
must have a SEPARATE experimental mode/ROI configuration; it must not redefine
the blue water bowl. Current metadata rejects BLUE/WATER as a food-bowl position.

## Linux HOST >=3.10 equivalent / JETSON distinction

```bash
python3 -m ai.scripts.prepare_behavior_v2 prepare --videos-dir /path/to/real/videos --dataset-root /path/to/behavior_v2_real --apply
python3 -m ai.scripts.prepare_behavior_v2 sessions --dataset-root /path/to/behavior_v2_real
```

On JETSON/MobaXterm use SSH, `hostname -I`, staging/copy and the validated C++
runtime only unless a compatible offline host environment is explicitly supplied.
No changes to C++ production, engine, ESP32/UART/safety or system packages are needed.

Existing `dataset_release validate --task behavior_v2 --stage TRAINING_CANDIDATE`
and `prepare_training --task behavior_v2` now delegate video-backed datasets to
these full video-readiness gates instead of silently checking only the first 1000
near fingerprints. They accept the explicit `--near-review` document too. Legacy
v1/photo-only contracts remain supported. `prepare_training` still produces a
future plan ONLY and cannot train a model.
