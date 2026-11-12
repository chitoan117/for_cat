# Current collection protocol — sensor integration first, 2026-10-21

Current priority is physical HX711/servo/approach/water validation, then load-cell
trend fusion. No new EATING NN or video quota is required before testing sensors.
For supervised evidence, preserve synchronized raw weight/distance/species/track,
calibration/boot/time/validity, commands and video when available. Known-mass
add/remove/noise-only trials verify scale first; cat+negative meaningful trend is
behavioral evidence, not tiny oscillations. Annotate spills/contact/refill/tare.

Use final FOOD_ROI and WATER_ROI positions, not color rules; stainless bowls can
share color. Keep the final camera fixed and document layout changes. Video of
sniff/stand/pause/leave near both bowls helps validate false positives. One cat
is sufficient for this personal system; other-cat identity is future scope.

Existing real Windows corpus:22MP4/3,063frames; pilot165assistant-authorizedlabels
and an exploratory CPUbaseline are already produced outsideGit. Do not assert
datasetabsent globally or fake HUMAN_REVIEWED. Keep future validation by day/visit,
not random neighboring frames; retain previous source hashes and history.

## Legacy optional visual Behavior V2 collection workflow

Current scope: ONE cat; labels EATING / DRINKING / IDLE. RED bowl=FOOD;
BLUE bowl=WATER; BLUE floor line=approach reference. Fixed camera, multiple
sessions/days/lighting conditions. Keep session/video groups together across splits.
Approximately 2 FPS (`--interval-seconds 0.5 --minimum-spacing 0.5`), followed by
blur/redundancy/annotation review. No automatic whole-video behavior label.
User now reports many real MP4 eating videos on Windows. Do not assume whole clips
are EATING: annotate reviewed intervals and transitions. No actual video is imported
unless the operator stages/provides it. Batch/interval/report commands and separate
Windows/HOST/Jetson instructions: [BEHAVIOR_V2_VIDEO_WORKFLOW.md](BEHAVIOR_V2_VIDEO_WORKFLOW.md).
NONE is no subject; UNKNOWN/UNSURE stay unconfirmed, never forced into IDLE.
V2 requires no OWNER_CAT/OTHER_CAT labels. See the exact commands and versioned
contract in [SINGLE_CAT_BEHAVIOR_V2.md](SINGLE_CAT_BEHAVIOR_V2.md).
Public data is optional supplementary data later, not a substitute for deployment
webcam sessions. No public dataset is downloaded or behavior model trained here.

Food variants/preference_trial_id/trial_order/session-pair fields are EXPERIMENT
METADATA, not behavior classes. Initially use the same RED food ROI across sessions.
BLUE water ROI remains water. Future simultaneous A/B needs its own experimental
mode/configuration; it cannot silently replace WATER_ROI. No LIKE/DISLIKE labels.

## Legacy/future v1 collection reference — not the current identity requirement

Collect only when a real webcam, consent/handling conditions and storage are ready. Use one anonymous `session_id` per **recording session**, not per frame. Preserve source session ID, camera/device, lighting, distance, view angle, occlusion, source offset and (only if known) actual UTC timestamp. Keep raw recordings private and out of source control. No model performance target or required dataset size is claimed.

**Identity sessions:** OWNER_CAT, OTHER_CAT, OTHER_OBJECT. Capture ordinary non-cat objects and empty/uncertain cases rather than forcing false cat labels; use SKIP/UNUSABLE as appropriate. **Behavior sessions:** EATING, DRINKING, NEAR_FOOD, NEAR_WATER, LEAVING, OTHER; use UNSURE/SKIP if the action is not observable. Do not infer behavior from a single still or label an unseen action as certain.

Use the intended bowl/camera placement consistently for comparable observations, then deliberately vary lighting (morning/day/evening), distances, view angles and partial occlusion across **different sessions**. Record environmental changes and food type when relevant. Make a small supervised pilot of short clips first to check framing, focus, labels, privacy, metadata and file corruption before planning broader collection. Extract at a considered interval: thousands of nearly identical adjacent frames add little independent evidence.

Workflow: record → `python -m ai.scripts.import_video FILE --session-id anonymous_id` (dry-run) → explicit `--apply` → bounded `extract_frames` → resumable `label_dataset` → `validate_dataset`/`dataset_report` → `split_dataset`. Never silently overwrite originals or manifests. **Split by session** (or stronger grouping if sessions overlap), never randomly split nearby frames from the same video across train/validation/test. Keep the test sessions untouched during training and early stopping. Near-duplicate warnings are prompts for human review, not proof of independence.
