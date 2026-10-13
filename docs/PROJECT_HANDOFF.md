# Project backup and handoff

Source entry points: `README.md`, `CURRENT_PROJECT_STATE.md`, `PRE_HARDWARE_FINAL_BASELINE.md`, `DOCUMENTATION_SOURCE_OF_TRUTH.md`. No Git repository exists in the current workspace; do not invent a commit or use reset to prepare delivery. Transfer source separately from private operational data/evidence/model binaries. No archive or private dataset is automatically packaged by this documentation pass.

## 1. Prepare a clean source transfer

Retain `jetson/app`, `jetson/tools`, both Python test trees, `ai` tooling/candidate/example config, `esp32` source/include/tests/platformio.ini, scripts, docs, requirements, pytest.ini, `.gitignore` and `.env.example`. Keep blank evidence/layout instructions if deliberately included; do not include actual private evidence.

Exclude venv/tool installations, `.pio`, `.native-build`, `.checks`, `__pycache__`, `.pytest_cache`, generated DB/WAL/backups, private captures/raw/processed/splits/releases/exports, local model/run registries and model binaries, secrets/keys and generated archives. Review all remaining files: filenames alone do not certify absence of credentials/private data. Do not copy an old PC events.db as device/safety validation.

Manual Windows copy example, from source root. `EXISTING_DESTINATION_PARENT` is a placeholder to replace with an existing reviewed destination; these commands are not executed here:

```powershell
$Source = (Get-Location).Path
$Parent = 'EXISTING_DESTINATION_PARENT'
if (-not (Test-Path -LiteralPath $Parent)) { throw 'Choose an existing destination parent' }
$Destination = Join-Path $Parent 'forr_cat_handoff'
if (Test-Path -LiteralPath $Destination) { throw 'Destination exists; choose a new handoff directory' }
$ExcludedDirs = @('.venv', '.tools-venv', '.tools-zig', '.pio', '.checks', '.native-build', '__pycache__', '.pytest_cache', '.git', 'evidence', (Join-Path $Source 'jetson\data'), (Join-Path $Source 'ai\models'), (Join-Path $Source 'ai\datasets\raw'), (Join-Path $Source 'ai\datasets\processed'), (Join-Path $Source 'ai\datasets\capture'), (Join-Path $Source 'ai\datasets\releases'), (Join-Path $Source 'ai\datasets\exports'), (Join-Path $Source 'ai\experiments\runs'), (Join-Path $Source 'ai\registry\local'))
$ExcludedFiles = @('.env', '.env.local', '.env.production', '*.pem', '*.key', '*.db', '*.db-*', '*.sqlite', '*.sqlite3', '*.pyc', '*.log', '*.zip', '*.onnx', '*.engine', '*.pt', '*.pth', 'manifest.jsonl', 'sources.jsonl', 'splits.json')
robocopy $Source $Destination /E /L /XD $ExcludedDirs /XF $ExcludedFiles
if ($LASTEXITCODE -ge 8) { throw 'Robocopy preview failed' }
```

`/L` is preview, not delivery. Review it and any `ai/reports/` generated/private JSON, source-context notes, hidden files and destination ancestry. Destination must be outside the source subtree. After review run the same command **without `/L`**; stop if return code≥8 (Robocopy uses0–7 for nonfailure outcomes). No `/MIR`/deletion/reset is needed. Copy required blank `.gitkeep`/`evidence/README.md` separately only if desired. Inspect any manually created ZIP to ensure source configs/hidden `.gitignore`/`.env.example` were retained and excluded secrets/caches were not reintroduced; record its SHA256 after creation.

## 2. Another Windows PC

1. Put reviewed source in a writable new folder; inspect requirements and `.env.example` without importing private settings.
2. Select compatible isolated Python (observed3.14.3; target/source minimum is not an ABI promise). Run from root:

```powershell
& .\scripts\setup_dev_windows.ps1 -WithOpenCV
& .\scripts\run_checks.ps1
```

3. Install/review a native C++17 compiler; observed Zig0.16.0 is discovered via PATH or `.tools-zig/`. PlatformIO6.2.0 is isolated in `.tools-venv`; firmware platform pinned in platformio.ini. Do not transfer old venvs across PCs.
4. Compare actual summary counts/status, dependencies and all11 profiles; keep the new PC log. Missing tools/failures are not a PASS.
5. Software demo from `jetson/`: `..\.venv\Scripts\python.exe -m tools.demo_replay`. Label SYNTHETIC/MOCK. No model/camera/actuator starts automatically.

Observed dependency snapshot is reproduction evidence, not a security or Jetson lock. See `REPRODUCIBLE_ENVIRONMENT.md` for package/tool versions.

## 3. Jetson Nano

Transfer reviewed source to a new directory, e.g. `$HOME/forr_cat`; preserve hierarchy/case. First inspect actual board/power/OS/JetPack/Python with existing `JETSON_FIRST_DAY.md` commands. Do not replace system Python or JetPack to force Windows dependency pins.

From root, on the **real reviewed machine**, prepare only a compatible isolated runtime:

```sh
sh scripts/check_jetson_env.sh
PYTHON_BIN=ACTUAL_COMPATIBLE_PYTHON sh scripts/setup_jetson.sh
jetson/.venv/bin/python -c 'import sys; sys.path.insert(0,"jetson"); import app.main; print("core imports checked")'
```

The setup script creates `jetson/.venv`, not the Windows/root venv. Audit compatible test, Pillow, OpenCV/GStreamer and optional inference packages separately; the complete host suite requires its available decoder/test/native/PIO dependencies. After provisioning explicitly run `jetson/.venv/bin/python scripts/check_release.py` from root to use that interpreter, or the shell wrapper from an appropriate environment. Preserve actual failure/skip/platform differences; do not copy the Windows PASS as a Jetson result. Runtime-only setup alone does not supply full codec/firmware tooling. No camera/model activation, service installation or public exposure is part of source transfer.

Then actual M3: identify ESP32-S3 memory/USB route, review safe image, explicit physical flash/status/reconnect with sensors/actuators disconnected. Use existing `ESP32_S3_FIRST_FLASH.md` and `M3_M4_GATE_DEFINITION.md`; `ACTUAL_COMPATIBLE_PYTHON`, `COMx`/`ACTUAL_NODE` are placeholders, not detected values.

## 4. Database, dataset, model and evidence handling

- **Database:** stop API/observation writers for transfer; inspect and use SQLite backup, not a live copy of the main file without WAL. From `jetson/`:

```text
python -m tools.db_maintenance inspect
python -m tools.db_maintenance backup --output data/backups/UNIQUE_HANDOFF_NAME.db
# Review dry-run, then add --apply for an exclusive validated snapshot.
python -m tools.db_maintenance inspect --database data/backups/UNIQUE_HANDOFF_NAME.db
```

After actual backup, validate schema/counts/hash before a separate protected transfer. Do not reset or overwrite the recipient DB; choose a new reviewed location and explicit DATABASE_PATH when restoring. Empty mock/development history must remain labelled; uncertain feed outcomes are not resumed. Backup/restore on deployed power-loss conditions remains unverified.
- **Dataset:** currently none. If actual footage later exists, transfer separately under agreed privacy/access rules with session manifests, hashes, annotation history, release version/splits and raw provenance. Rerun integrity/leakage gates on the recipient; do not upload or infer a session from filenames.
- **Models:** currently none. Transfer only an actual trusted artifact plus experiment/dataset/label/preprocessing/runtime/threshold/hash metadata; verify hash and inactive registration. Metadata checks do not prove graph correctness. No automatic activation/VALIDATED_JETSON status or pickle loading.
- **Evidence:** real hardware/data/training logs/photos stay separate from source; keep timestamps, exact devices/configuration, source/image/artifact hashes, outcomes and failure logs. Share only reviewed sanitized copies. Existing host logs are not physical evidence.

## 5. Another developer/instructor

Read current state/requirements/traceability/source map first; reproduce checks; review thesis outline/draft/blank tables, known debt/security and gates. Record source-control revision if a real repo is later introduced, otherwise a verified archive/source manifest hash—never fake an ID. The handoff contains no new features/tests or changed UART/actuator permissions. **Stop pre-hardware development; proceed only with real engineering evidence.**
