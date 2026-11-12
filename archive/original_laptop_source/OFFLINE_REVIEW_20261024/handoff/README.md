# Backend availability update — OFFLINE, not deployed to Jetson

This package contains exactly six Python source/test files. It was prepared after
the user requested work without Jetson access. No SSH, serial, camera, actuator,
firmware flash, partition or NVS operation is performed by this package.

## Changes

- Missing Linux boot identity no longer crashes backend startup. REAL returns
  explicit unavailable state; it never generates a fake boot ID to accept cache.
- Malformed/duplicate/non-finite cache JSON, bad sensor shapes/types and unsafe
  cache flags fail closed instead of becoming live numeric values or API errors.
- AI cache validates confidence/timestamps and returns UNKNOWN on corrupt/stale data.
- Missing AI is UNKNOWN observed behavior, not a claimed animal IDLE. The internal
  controller state remains available separately. No real EATING/consumed grams
  are claimed while gram calibration is deferred. Water policy remains independent.
- REST and realtime survive a provider exception, keep the REAL/MOCK declaration,
  rate-limit repeated error logs and recover on the next valid snapshot.
- A malformed history row no longer hides all valid history rows.

Exact old/new SHA256: `manifest.json`. Reviewable changes: `review.diff`.
Only `jetson/app/{device_state,ai_state,system_state}.py` and three test files
are included. No AI detector source/binary/engine or ESP32 source is changed.

## Offline verification already run

- Windows/Python3.14: **103 API/state/legacy contract tests PASS**, Ruff PASS.
- Existing portable C++ cores built/run with Zig/UBSan flags: **67 decision/FSM/
  water checks**, **99 dispense-policy assertions**, **9 actual-added35g fake-HX checks PASS**.
- All data is synthetic/temp SQLite. This is NOT new Jetson or physical PASS.
- Original Jetson baseline had303 backend tests PASS before these new changes;
  the updated revision must be checked again on Jetson/Python3.11.
- Guarded updater:8 tests PASS for read-only comparison, index preservation,
  idempotency, source/payload conflicts, rollback, concurrent edits and scope limits.

## Tomorrow: compare before applying

Copy this entire folder to a new Jetson directory, e.g. `/tmp/for_cat_offline_20261024`.
Use the existing isolated Python environment:

```sh
/home/toan/for_cat/.venv/jetson-integration/bin/python /tmp/for_cat_offline_20261024/apply_source_update.py --project /home/toan/for_cat --check
```

Default/check mode is read-only. Unexpected source edits, payload corruption or
unexpected paths abort the whole preflight. Already-applied files are recognized.
Do not bypass a conflict or bulk-copy the old workspace over the real project.

After comparison/review, application is explicit:

```sh
/home/toan/for_cat/.venv/jetson-integration/bin/python /tmp/for_cat_offline_20261024/apply_source_update.py --project /home/toan/for_cat --apply
```

Application snapshots Git status/diffs and original target files into a uniquely
named `evidence/offline_source_update_*` directory. The Git index is never staged,
reset or restored. Atomic writes have rollback; concurrent user edits are preserved
for manual comparison rather than overwritten. No service is restarted by this tool.

## Validate the actual Jetson revision

From `/home/toan/for_cat`:

```sh
PYTHONPATH=jetson:. .venv/jetson-integration/bin/python -m pytest jetson/tests -q
git diff --check
```

Record the actual Linux result, then restart only the backend when appropriate:

```sh
systemctl --user restart for-cat-api.service
curl --fail http://127.0.0.1:8000/api/status
```

No C++ bridge or firmware source is modified here, so no ESP32 rebuild/reflash is
required. Linux PTY/reconnect and live API/WS/DOM verification remain tomorrow's
checks, after reconnecting Jetson reliably. Preserve35g actual-dispensed target,
gram-calibration DEFERRED, all actuator execution blocked and no near threshold.

The last resumed Jetson had only a link-local Ethernet IPv6 plus Docker172.17.0.1;
find current addresses with `ip -br address`. Docker172.17.0.1 is not its LAN IP.
Existing hardware availability faults and the SSH dropout are not marked resolved
by this offline package. Camera/OLED/button physical checks remain separate.
