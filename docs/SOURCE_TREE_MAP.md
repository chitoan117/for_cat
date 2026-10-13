# Source tree map

| Need | Look here |
| --- | --- |
| API/config/lifecycle | `jetson/app/main.py`, `api/routes.py`, `config.py` |
| Camera/video/frame processing | `jetson/app/camera/`, `jetson/tools/{test_webcam,run_observations,replay_video,capture_session}.py` |
| Runtime AI/interface/shadow orchestration | `jetson/app/ai/` |
| Detector/crop/track boundary | `jetson/app/vision/` |
| Temporal behavior/sensor fusion | `jetson/app/behavior/` |
| Database/history/ledger | `jetson/app/storage/` |
| Preference/activity reports | `jetson/app/analytics/`, `jetson/tools/activity_report.py` |
| Serial protocol/reconnect | `jetson/app/serial_link/`, frozen golden CSV |
| ESP32 protocol/dispatch | `esp32/src/main.cpp`, `esp32/include/{uart_v1,command_dispatch}.h` |
| ESP32 safety/gates | `esp32/include/{safety_logic,board_config,pins}.h` |
| Drivers/diagnostics/persistence | `esp32/include/m4/`, `src/diagnostics.cpp`, safety persistence headers |
| Capture/session/sampling | `ai/{capture,session,sampling}.py` |
| Dataset import/labels/splits/releases | `ai/dataset.py`, `releases.py`, `interchange.py`, `ai/scripts/` |
| Experiment/model candidates/registration | `ai/experiments.py`, `ai/registry/candidates.json`, `ai/experiments/example.json` |
| Training | `ai/training.py` plan only; no trainer/framework/model bundled |
| Evaluation/threshold sweep | `ai/evaluation.py`, `ai/scripts/evaluate_run.py` |
| Tests | `jetson/tests/`, `ai/tests/`, `esp32/test/native_*.cpp` |
| One-command check | `scripts/run_checks.ps1`, `.sh`, `check_release.py` |
| Current state/handoff/thesis | `docs/CURRENT_PROJECT_STATE.md`, `PRE_HARDWARE_HANDOFF.md`, `THESIS_*_VI.md`, `PROJECT_HANDOFF.md` |
| Requirements/report/security/evidence instructions | `docs/`; local physical evidence layout `evidence/` |

Root `ai` is research/data tooling; `jetson/app/ai` is the runtime boundary. Generated private capture/data/models/run/check output are ignored. Start with `CURRENT_PROJECT_STATE.md`, `PRE_HARDWARE_FINAL_BASELINE.md` and `PRE_HARDWARE_HANDOFF.md`, then relevant requirement/module tests. Older Phase/RC/status ledgers are historical.
