# Jetson-side pre-hardware hardening report — milestone M2

Historical navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **HISTORICAL / NOT CURRENT:** the163-test/four-build checkpoint and synthetic overhead benchmark below are preserved, not the current baseline or Nano FPS. See `PRE_HARDWARE_FINAL_BASELINE.md` / `CURRENT_PROJECT_STATE.md`.

## Scope / truth labels

Normal USB webcam → Jetson Nano camera/OpenCV → detector/crop + identity/behavior runtime boundary → temporal sessions/fusion → SQLite/REST → intent-level USB serial → ESP32 final safety. Existing frontend is untouched. This pass changes only Jetson/offline evaluation/config/scripts/docs; **ESP32 source and UART v1 bytes were not changed**. No physical webcam, serial port or GPU runtime was started by this work.

**SOFTWARE VERIFIED / HOST TEST VERIFIED:** final Windows isolated-Python run of `scripts/run_checks.ps1`: **163 tests, 163 passed, 0 failed, 0 skipped** (all 125 RC2 tests retained). Native C++ remains **140/140**, UART **7/7**, compile guards **5/5**, existing simulator cases pass, and all four inert classic/S3 firmware regression builds remain PASS with the same RC2 footprints. No failing test or meaningful warning was suppressed.

**NOT JETSON VERIFIED / NOT CAMERA HARDWARE VERIFIED / NOT CUDA VERIFIED / NOT TENSORRT VERIFIED. DATASET NOT AVAILABLE. AI NOT TRAINED.** No new milestone or physical validation result follows from the host suite. Previous completion estimates are not inflated from added tests.

## Compatibility and dependencies

`JETSON_PYTHON_COMPATIBILITY.md` documents source and installed package metadata: Python **3.10 minimum** (evaluated union annotations and pinned FastAPI/Starlette/AnyIO/Uvicorn). Host interpreter is **3.14.3**, not a Nano compatibility test. Pydantic-core ARM/glibc wheels, OpenCV Python ABI, GStreamer and exact JetPack/TensorRT remain real-device gates. Older Nano Python must be handled in an isolated supported environment; no system Python or JetPack upgrade is done.

`requirements-core.txt` wraps pinned runtime dependencies; `requirements-test.txt` adds tests; old `requirements.txt` remains compatible. `requirements-ai.txt` and `requirements-deployment.txt` explicitly install no research/GPU packages. Mock/API/SQLite/serial code does not require OpenCV/Torch/TensorRT/Roboflow. Diagnostic shell now reports OS/kernel/architecture, Python/pip, disk/RAM/swap, L4T/JetPack metadata, nodes, OpenCV/GStreamer build lines, SQLite and CUDA/TensorRT presence without installing or loading GPU engines. Jetson shell scripts remain unexecuted on Jetson.

## Camera, model and ROI boundaries

CaptureSettings allows configured device/index, resolution/FPS, AUTO/V4L2 or trusted optional GStreamer pipeline, read timeout and failure bounds; automatic recording sinks are rejected. Status is passive: configured providers are not opened by app import/lifespan/liveness/passive readiness. `list_cameras` enumerates likely nodes without capture, and explicit probing/manual `benchmark_camera` uses a killable child process. Actual backend, negotiated dimensions/FPS/read errors and approximate process usage can be reported later; no camera benchmark was run here.

V4L2/OpenCV timeout/buffer properties are **best effort**. A native driver/model can block despite Python limits; hardware-free tests cannot promise hard live-read deadlines. One managed service worker may be deliberately started; default startup starts none. Stop timeout returns FAULTED instead of rapidly restarting a stuck component; systemd process termination is the later fallback.

Mock interfaces expose load/predict/health/close. ExternalRuntimeAdapter has no installed ONNX/TensorRT/research executor and defaults NOT_CONFIGURED until local files/thresholds/executor exist. Model filenames are validated inside trusted MODEL_ROOT, reject absolute/parent/drive escapes and never arrive from REST. DetectorIdentityModel only classifies one valid confident **crop**, never the whole scene by default; no/multiple/overlapping/low-confidence/tiny detections remain NO_SUBJECT/UNKNOWN. Normalized food/water/approach ROIs and thresholds are explicit local config. Synthetic tests confirm outside-ROI blocks sessions, brief dropout tolerates, and ambiguous identities never authorize an action.

## Observation/lifecycle, backpressure and failure policy

`ObservationService`: STOPPED/STARTING/RUNNING/DEGRADED/FAULTED/STOPPING, one explicitly owned worker or a synchronous bounded run, interruptible pacing, capped backoff, no frame queue. Configured app processing defaults: requested capture 10 FPS, inference budget 2 FPS, processing ≤640×480, queue depth **1**, explicit frame skip/stale-age controls. Slow inference cannot create a Python image backlog; OS/decoder buffering remains hardware validation.

Lifecycle loads models only on explicit observation start, cleans partial loads, releases camera/models, closes serial and storage after the owned worker stops. Component close errors do not skip the remaining resources. Storage failure retains **one** completed visit for paced idempotent retry and prevents reading more frames in a crash loop. Persistent failure yields FAULTED while liveness/readiness remain reportable. If a native worker cannot stop, storage is not concurrently closed underneath it; process-level shutdown must be tested physically.

Default **AI_SHADOW_MODE=true**. Predictions/history are monitoring only; pipeline contains no automatic feed-authorisation path even if a flag is changed. Camera/model/UNKNOWN/multiple-cat/storage failure cannot infer actuator intent. Physical manual SERIAL requests remain blocked by the existing baseline safety gate. Only meaningful events/confirmed visits are persisted, not camera frames. Repeated camera/model/serial warnings use a bounded monotonic rate limiter; latency samples retain 256 entries. Real serial reconnect backoff defaults to 2 s and frequent polls do not extend its retry deadline indefinitely.

`/health` remains the frozen `{status:"ok"}` process liveness contract. Additive `/readiness` is passive cached software usability (DB/camera/AI/link/service), with real-hardware/real-AI validation flags false; `/status` adds service/readiness snapshots and retains explicit transport polling. Offline camera or faulted observations can coexist with live API. CORS remains explicit-origin and local loopback bind is default; no raw-actuator endpoint, auth/TLS/public deployment or frontend modifications.

## Storage and timestamp findings

WAL + busy_timeout 2000 ms + synchronous FULL + 100-page autocheckpoint + 4 MiB journal-size setting are now host-tested. Ledger claims use BEGIN IMMEDIATE, visits atomic/idempotent; retention remains bounded. These are not SD-card/power-loss guarantees: long external readers can prevent WAL truncation. `storage_report` is diagnostic, no deletion; manual datasets/backups/OS temp/journal retention require an operator policy. See `JETSON_STORAGE_POLICY.md`.

Canonical record timestamps are UTC-aware; timeouts/pacing/inference/serial intervals use monotonic clocks. Session end is anchored at wall-clock start plus observed monotonic duration, so clock rollback cannot generate a negative eating duration. Daily tests cover midnight, timezone conversion, empty days, unknown consumed grams and pending feed attempts without claiming dispense. A max-date daily query fails clearly (422) rather than overflow. OTHER_CAT→OWNER_CAT evaluation now exposes both supplied-prediction count and rate; no result exists without predictions.

## Actual host replay / benchmark / soak evidence

`python -m tools.demo_replay`: **SYNTHETIC DEMO**, 23 received frames (one planned missing frame), 22 processed, 2 planned camera/model failures, 3 synthetic visits (owner eating, owner drinking, other-cat eating), **0 automatic actions**, unknown consumption. No trained inference or camera footage.

`python -m tools.benchmark_pipeline --frames 300` final sample, **HOST BENCHMARK ONLY**, synthetic **16×16** frames and trivial fake models, pacing disabled for overhead measurement: **300 processed**, **0 skipped**, **38 synthetic sessions**, **0.0096797 s runtime**, **30,992.70 effective FPS**, **0.027393 ms mean processing latency**, **0.138900 ms p95** over the last **256** latency samples. These high tiny-fixture figures are **software overhead only**, sensitive to host scheduling and absolutely not real model/webcam/GPU/Nano throughput. No performance comparison to Jetson is justified.

**HOST TEST VERIFIED:** accelerated **6000×0.6 s = hour-equivalent** processing retains ≤8 typed rows per tested kind, queue 1, latency samples 256, no leftover active/pending visit, and drains bounded serial pending IDs. Separate warmed Python tracemalloc sanity check stays under a 6 MB growth bound across 1500 more frames; this is not native decoder/GPU leak proof. Synthetic service+model-paused worker+REST polls+ONLINE/OFFLINE serial toggling finishes without deadlock, duplicate feed or health failure. Permanent/transient DB write errors fault or recover the same single visit without duplicate records. RC2 generated-video decode/dataset round trip continue to pass (**VIDEO REPLAY VERIFIED**, not cat video).

Passive host readiness report shows Windows AMD64, Python 3.14.3, SQLite **3.50.4**, OpenCV **4.13.0**, **GStreamer build support NO** on this PC, no detected nvcc/TensorRT module, and no opened camera/serial/model. Build presence is not runtime/hardware readiness.

## Deployment/docs and remaining gates

Prepared `deploy/systemd/forr-cat.service`, **not installed**: non-root placeholder User/Group, explicit venv/working directory/environment file, delayed limited restart, safe SIGTERM/process stop, journal output and write-path restriction. `.env.example` contains camera/model/ROI/budget/log/shadow/serial settings with no secrets. Frontend data map is PARTIAL: fields exist but old client schema, network/auth/TLS and real sensor/model content remain untested.

See audit/compatibility/performance/storage/multi-cat/fail-safe/model-insertion/network/systemd docs. First actual command sequence: inspect board and supply, boot alone, then from `$HOME/forr_cat` run `sh scripts/check_jetson_env.sh`; only with a compatible interpreter run `sh scripts/setup_jetson.sh`. `JETSON_FIRST_DAY.md` gives exact imports/tests/manual camera/serial order; `JETSON_EVIDENCE_LOG_TEMPLATE.md` is blank physical evidence.

**Freeze scope:** Jetson-side pre-hardware software may be frozen with the documented live-driver/ABI/native-runtime/disk limitations. Milestone M2 remains. Nothing starts physical capture, GPU inference, serial or actuator work automatically.
