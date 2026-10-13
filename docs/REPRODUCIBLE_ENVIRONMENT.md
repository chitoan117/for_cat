# Reproducible development/check environment

Observed host: Windows, Python3.14.3 isolated `.venv`; PlatformIO6.2.0 isolated `.tools-venv`; Zig0.16.0 for C++17; firmware platform `espressif32@55.3.311`, Arduino3.3.11 / Xtensa14.2.0+20260121. These are PC results, not Jetson compatibility.

Direct requirements are pinned in `requirements-dev.txt` and `jetson/requirements-{runtime,test}.txt`. `requirements-host-snapshot.txt` records the observed full host dependency set including optional OpenCV4.13.0.92/NumPy2.5.3/Pillow12.1.1. It is a reproduction snapshot, not a Jetson deployment lock or security guarantee. `pip check` verifies consistency; it is not a vulnerability scan. Review releases/security/platform wheels before future upgrades; do not impose incompatible old pins on Jetson.

Windows setup/check:

```powershell
& .\scripts\setup_dev_windows.ps1 -WithOpenCV
& .\scripts\run_checks.ps1
# Optional exact observed-host reconstruction in a separately chosen venv:
python -m pip install -r requirements-host-snapshot.txt
```

Linux/Jetson preparation remains separate: audited Python/OS/JetPack first, core requirements only, then compatible local OpenCV/GStreamer/runtime packages. `sh scripts/run_checks.sh` uses `.venv/bin/python` if available, otherwise python3. No PyTorch/ONNX/TensorRT is installed by setup.

Both check wrappers call `scripts/check_release.py`: Python suite (including dataset/video fixtures), passive imports, pip consistency, default dataset acceptance, native safety/drivers, seven UART vectors, compile guards and eleven compile-only firmware profiles. A failed step prints full output, writes its log and returns nonzero; missing compiler/PlatformIO also fails rather than claiming an omitted build passed. Successful output is concise; `.checks/summary.json` and per-step logs preserve actual counts/profiles/environment. No upload, camera opening, model training or physical evidence occurs. Shell wrapper has not been executed on Linux in this Windows pass.

Source has no Git repository here. Experiment tooling records source hash and config/dataset separately; no commit ID is fabricated. Future developers should use normal source control and archive validated dataset/model hashes with each release. The repeatable host environment is ready; Nano runtime/performance and actual hardware remain unverified.

## Developer-only release quality checks

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements-quality.txt
& .\scripts\run_checks.ps1
& .\.venv\Scripts\python.exe scripts/run_quality_checks.py
& .\.venv\Scripts\python.exe scripts/make_release_manifest.py
& .\.venv\Scripts\python.exe scripts/make_release_manifest.py --verify
```

Ruff0.14.10/mypy1.19.1 are isolated dev tools, not runtime/Jetson dependencies. Quality scope includes strict native compiler, existing OpenAPI snapshot and redacted source/docs audit; logs/manifests go to ignored `.release/`. No project warning filter, upload, model activation or dataset download. Reproduction uses actual counts/status, not a forced217 baseline; see `PRE_HARDWARE_RELEASE_CANDIDATE.md`.
