# Explicit capture → annotation → versioned dataset

Capture is an offline CLI, never started by FastAPI. From `jetson/`, using the project venv:

```powershell
..\.venv\Scripts\python.exe -m tools.capture_session --source camera:0 --session-id pilot_owner_001 --identity OWNER_CAT --behavior EATING --duration 60 --interval 1 --lighting daylight --view-angle side --dry-run
..\.venv\Scripts\python.exe -m tools.capture_session --source PATH_TO_SUPPLIED_VIDEO --session-id replay_001 --identity UNKNOWN --behavior UNSURE --duration 60 --max-frames 100 --dry-run
```

Replace explicit sources/context with actual observations. `--apply` records sampled JPEGs; without it there is no camera opening or output directory. `camera:ACTUAL_NODE` is the future Linux device form. Importing the module does not open anything. No webcam was used in this pass; tests use generated video only.

Bounds: 1–1000 stored frames, duration at most3600s, 100000 decoded frames, 8MB/frame and 100MB/session. `--minimum-spacing` combines with `--interval` by taking their maximum. Exact duplicates are skipped; perceptual neighbors produce warnings, not fabricated motion evidence. Ctrl+C requests graceful stop; a separate spawned worker is terminated if a backend does not return within duration+10s. Staging is committed only on a completed worker result. Existing session folders are rejected. Single-writer local use is intended; no concurrent capture into the same session.

Output: `ai/datasets/capture/SESSION/session.json`, `manifest.jsonl`, `processed/*.jpg`. Schema-v1 `ai/session.py::SessionManifest` includes session_id, UTC recorded_at, source type/device, actual resolution/reported FPS if known, requested identity/behavior, food/lighting/distance/angle/occlusion/environment/notes, usable, source hash/type, duration/sampling/count/stop reason. Video source hash is file SHA256; camera hash is the sampled-frame stream SHA256, not proof of the camera's identity or full video content. Replay offsets come from frame index/FPS, not an invented original UTC capture time.

**Targets are collection intent, not ground truth.** Samples start unlabelled and unusable. Human review uses `ANNOTATION_GUIDELINES.md`; label with the existing `ai.scripts.label_dataset` after selecting the sample. Identity UNKNOWN is supported; unsure/unknown data must not be coerced into a clean task class.

From root, consolidate explicit session folders into a **new** dataset folder:

```text
python -m ai.scripts.dataset_release ingest --source SESSION_FOLDER_A SESSION_FOLDER_B --output NEW_DATASET_FOLDER
# Review dry-run; add --apply to write. No existing dataset is overwritten.
python -m ai.scripts.label_dataset SAMPLE_ID --dataset NEW_DATASET_FOLDER --identity OWNER_CAT --behavior EATING --apply
python -m ai.scripts.split_dataset --dataset NEW_DATASET_FOLDER --apply
python -m ai.scripts.dataset_release validate --dataset NEW_DATASET_FOLDER --task identity --stage PILOT_DATASET
python -m ai.scripts.dataset_release release --dataset NEW_DATASET_FOLDER --version pilot_v1 --output RELEASE_FOLDER --apply
```

Rows retain session/source provenance through ingestion. Session splits alone are insufficient when one source video contains multiple sessions: source/hash checks must also pass. Release metadata records version/time/schema, counts, split membership/counts, classes, source hashes, manifest hash and validation report. Revalidate after any annotation/split change; an old release JSON is not a live approval of edited files.
