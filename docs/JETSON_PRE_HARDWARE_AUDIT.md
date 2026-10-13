# Jetson audit — starting RC2 state

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT:** missing lifecycle/crop/runtime-boundary claims below describe the starting checkpoint. Current implemented foundations and remaining real-runtime gaps are in `CURRENT_PROJECT_STATE.md`.

Initial Windows rerun: 125 Python tests pass. No Jetson, JetPack, Logitech-on-Jetson, CUDA, TensorRT or physical serial evidence. Milestone M2. ESP32 source and UART v1 will not change in this pass.

Ready host modules: FastAPI paths/idempotent feed ledger (`app/api/routes.py`), bounded events/typed visits (`app/storage/`), UART codecs, pyserial correlation/reopen (`app/serial_link/`), synchronous injected `ObservationPipeline`, temporal/fusion logic and UNKNOWN-returning mock models. Partial: no managed observation lifecycle, model load/close boundary, resolution/inference budget or camera backend selection; `/status` can call camera health and open/read hardware when configured. Model/storage exceptions share a catch path; a write failure can lose an ended visit and shutdown can abort before closing other resources. These are concrete hardening targets.

Hardware-dependent: Linux capture/USB permissions, OpenCV V4L2/GStreamer build and timeout support, actual serial reset/reconnect, SD-card write behavior, Nano RAM/swap and sustainable camera/model latency. AI-dependent: detector/crop, trained identity/behavior, calibrated thresholds/ROIs, real event confidence. No threshold is scientifically validated by synthetic tests.

Compatibility risks: runtime annotations use evaluated `|` unions (Python 3.10), generics require 3.9, tooling uses `Path.is_relative_to`/`unlink(missing_ok=True)`. Installed pinned FastAPI/Starlette/AnyIO/Uvicorn require Python >=3.10; the Nano may arrive with an older JetPack Python. Do not replace system Python or blindly downgrade code. Pydantic's compiled dependency wheels and libc/aarch64 support must be checked in the exact isolated environment.

Performance risks: synchronous capture may block in V4L2 despite OpenCV timeout properties; there is no universal driver-level timeout guarantee. One full RGB frame already consumes width×height×3 bytes, plus decoder/model copies. Avoid queuing stale frames, unbounded latency lists or frame-by-frame DB/log writes. GPU/ONNX/TensorRT adapters are not installed/validated; JetPack versions and model operators/precision/memory/crop normalization must be proven later.

Outcome evidence from this pass is recorded in `JETSON_PRE_HARDWARE_RC.md`; this document preserves the initial audit findings.
