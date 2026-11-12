# Software architecture map

Jetson: `app/main.py` assembles FastAPI, stores, mock/default camera and serial, ObservationPipeline/Service. `api/routes.py` exposes v1 and durable bounded feed lifecycle; `storage/` owns SQLite events, typed records/history and request ledger; `camera/` owns mock/file/USB and frame budgets; `ai/` owns interfaces/runtime/lifecycle and injected predictions; `vision/` owns crop/detector and supplied-track boundary; `behavior/` confirms temporal sessions/fuses validated weights; `analytics/` computes cautious read-only trends/reports; `serial_link/` owns framed protocol/IDs/reconnect; `tools/` are explicit operator commands.

Research/data: root `ai/` owns session schema/capture/sampling, image manifests/labeling/splits, leakage/releases/interchange, experiments/candidates/inactive registry and supplied-prediction evaluation. It is not the deployed Jetson inference package `app.ai`; no training framework is a startup dependency. Candidate metadata never loads a model or starts a worker automatically.

ESP32: protocol/dispatch + portable feed/water policy, hard board/output gates, separate safety persistence and M4 sensor calibration, configured drivers and explicit ASCII diagnostic modes. Normal binary v1 and diagnostic ASCII are distinct builds. No firmware changes are made in this productization pass.

Data flow: explicit capture → human annotation → source/session-safe versioned release → future reproducible training → registered inactive artifact → validated explicit runtime → shadow observation → typed history/read-only report. Physical actuator authority is separate and remains blocked. Future multi-track orchestration, real model executor, production telemetry and frontend deployment remain gaps.
