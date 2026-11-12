# Real-hardware adaptation audit — before changes

Actual workspace inspected: PlatformIO/config/board/pins/build banner, all M4 headers/diagnostic entry points, camera/settings/config, capture/session/data/provenance tools, release/guards and operator utilities. Application architecture remains normal USB webcam→Jetson→USB serial→ESP32-S3, Web/App↔REST↔Jetson; no alternate MCU/camera.

Before this pass `.checks/summary.json` records301 Python,140 safety+3131 driver assertions,7 vectors,18 guards,11 builds PASS at2026-10-05T08:47:23.028710+00:00. That is the historical host run, not a new physical observation. `platformio.ini` actually contains the user's appended `esp32s3_16mb_no_psram_hw_safe_uart` block; it was preserved/refactored, not discarded as unfamiliar work.

| Before-change finding | Adaptation needed |
| --- | --- |
| Five legacy MCU profiles / six diagnostic profiles use official S3 N16R8 compile surrogate with BOARD_HAS_PSRAM/qio_opi | Keep explicit surrogate compatibility targets, select measured16MB/no-used-PSRAM bridge profile for current board |
| Manual real-safe environment duplicates flags and banner still labels generic N16R8 | Reusable no-PSRAM base/compile guard and accurate build label |
| Production pins are all-1; diagnostics default unreviewed/-1 | Preserve default gates; separate explicit candidate sensor-only mapping, actuator pins-1 |
| GPIO38 not excluded in conservative S3 adapter | Reserve onboard RGB38 as supplied;43/44,19/20 and special pins stay reserved |
| Modern camera requests640×480/10 without FourCC; reopen on every failed read | Preferred physical720pMJPG30 config + bounded retry/backoff, no hidden capture |
| Main runtime/tool annotations/packages require modern Python | Do not backport/reinstall system stack blindly; independent Python3.6 utilities, separate-runtime recommendation |
| Capture/session/splits/interchange already implemented | Reuse canonical manifests/sampling, adapt camera negotiation and portable recording, retain provenance/UNKNOWN/unusable labels |
| Current-facing docs broadly state no hardware verified | Supersede with supplied observations and explicit provenance; old pre-hardware timestamps/results retained |
| Historical classic/S3/camera wording and benchmark scopes | Legacy/surrogate only; generic observed webcam identity instead of presumed brand;1080p advertised is not runtime evidence |

New physical facts originate in the user's report, not tools run remotely by this agent. PSRAM NOT DETECTED overrides seller N16R8 advertising for software selection. No board photo/pin voltage/sensor/actuator result was supplied. Post-reconnect operation is user-reported PASS without a stored raw transcript; formal closeout retains that evidence gap. Python3.6.9/OpenCV4.8/CUDA/TensorRT installed versions do not certify modern API/model compatibility or AI performance.
