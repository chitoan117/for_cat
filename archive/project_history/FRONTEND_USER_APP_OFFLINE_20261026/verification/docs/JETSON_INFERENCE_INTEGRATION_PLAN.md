# Future jetson-inference/model boundary — NOT JETSON VERIFIED / AI NOT TRAINED

Historical RC2 navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL RC2 wording:** references below to absent crop/detector boundaries are superseded by implemented injectable foundations. Actual models/executors/Jetson validation remain absent. Current conceptual contract/research order: `AI_TASK_ARCHITECTURE.md` / `AI_RESEARCH_EXECUTION_PLAN.md`.

Reference: NVIDIA-associated `dusty-nv/jetson-inference` (https://github.com/dusty-nv/jetson-inference), inspected for detectNet/TensorRT concepts. It is **not** vendored, installed or a hard dependency here. Its example model accuracy/FPS are not forr_cat results. Building it may download models; that is not done automatically by forr_cat.

Future mapping:

Normal USB webcam/OpenCV frame → detectNet or custom cat detector → validated cat bounding box/crop → **custom identity model** OWNER_CAT / OTHER_CAT / UNKNOWN (reject uncertain/no-cat cases) → custom behavior model EATING / DRINKING / OTHER plus calibrated bowl ROI evidence → forr_cat `ObservationPipeline` / `TemporalEngine` → `SessionFusion` → canonical typed SQLite visits → API Event-shaped history projection.

Adapters implement existing `IdentityModel.predict(CameraFrame)` and `BehaviorModel.predict(CameraFrame, Identity)` protocols. Identity returns `Recognition` with real optional confidence/model version; behavior returns `BehaviorObservation` with real confidence and ROI flags. Color layout, resizing/normalization, crop coordinate system, class map, batch/rate/time source and model metadata must be fixed and tested with the trained model. An invalid runtime/crop/prediction raises a model error and produces DEGRADED status—not a fake owner label or feeding command. Crop extraction/detector/model runtime are future work, not implemented merely by this document.

| Future adapter | Boundary and prerequisites | RC2 status |
| --- | --- | --- |
| Python/PyTorch research | externally trained weights, deterministic label map and sample-safe evaluation | Protocol only; no Torch installed |
| ONNX | validated export/preprocessing and available compatible execution provider | Protocol only; no ONNX runtime installed |
| TensorRT / Jetson runtime | **exact Nano board + JetPack/CUDA/TensorRT versions**, supported model ops and measured memory/latency | Protocol only; no TensorRT engine or validation |

Do not assume Orin/JetPack 6 examples apply to the older Jetson Nano. Audit actual Nano OS/Python first; the FastAPI code needs Python 3.10+, while a supported inference runtime may require a different isolated environment. Keep runtime adapters outside safety authority: identity alone must **never** trigger automatic feeding. No hunger, emotion or subjective liking is inferred from a still image.
