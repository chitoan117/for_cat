# Deep quality/failure-injection scope

Starting command `scripts/run_checks.ps1` actually passed:217 Python,1328 native (140+1188),UART7,guards18,builds11; timestamp2026-10-05T05:55:03.083603+00:00. This pass adds only justified correctness/resource/contract/release checks and fixes, not endpoints/drivers/AI actions. Actual final values are recorded after full rerun in `PRE_HARDWARE_RELEASE_CANDIDATE.md`.

| Area | Executed risk coverage | Limit |
| --- | --- | --- |
| Generative UART |800 valid seeded variable/max-payload/uint32 round trips + CRC/truncation;2000 bounded noise chunks; nested payload regression | Wire/golden unchanged; valid truncated-length ambiguity resolved only after timeout |
| Native records/calendar/level |100 seeded date/calibration/percent trials, all200 safety-record bit flips, padded partial writes, unsupported versions, inspection/no resume, UTC year/leap/RTC fault and stale-water stop | Codec/fake I/O, not actual Preferences/power loss |
| IDs/link |0/1/max values, near-max ledger allocation/exhaustion, duplicate/restart, stale mismatch/peer-cache reset, existing backoff/state tests | No wrap/reuse; no boot nonce in v1; pending outcome not magically resolved |
| DB |WAL/busy timeout,25ms explicit lock injection, SQL denial/rollback, terminal atomicity, reopen/duplicate/partial metadata writes | Generic event log transaction separate; SD/disk interruption not simulated physically |
| ACCELERATED HOST SOAK |1-day and7-day **sparse hourly** virtual spans:8 frames/hour,48/336 eating/drinking sessions, UTC year rollover, retention/ledger cap8, explicit manual mock requests, serial loss/recovery and insufficient preference summaries | Not continuously sampled24h/7d or real wall-time reliability; no FPS/resource guarantee on target |
| Composite faults |Camera/model/serial-active-session/DB-after-confirm, pending service/peer restarts; native RTC/weight/water faults | Health/state/store/no-auto-action assertions; synthetic only |
| AI/adversarial |UNKNOWN/multi-cat/crossed order/identity flips/occlusion/gaps, exceptions, stale/missing/increased/impossible weights and missing confounders | Track association real library/data absent; timestamps and source validity are supplied evidence |
| Lifecycle |Blocked managed model/visit write, duplicate worker guard, bounded stop/FAULTED then controlled release/cleanup; existing camera/serial/partial model cleanup | Native thread can remain honestly alive until external/process intervention |
| API/data/security |Every current GET + feed/poll, method/empty/bounds/date/body/UTF/error/traceback, snapshot; manifest/path/provenance/schema/hash/model nonactivation | Trusted-local CLI, simulated resolved symlink case; no browser/client or broad production security claim |
| Static |Ruff selected correctness rules, mypy5 files, strict compiler both native harnesses/no project warnings | No whole-project typing/cppcheck/clang-tidy claim |
| Docs/release |Internal links/named refs/anchors,9 Mermaid blocks structurally, contextual claim audit/redacted source scan, local BOM + source/firmware hashes | No browser render/legal license/CVE/secret-absence proof |

Fusion now requires aware `sampled_at` evidence close to event boundaries; default5s is a configurable **software** window, not a measured sensor specification. Legacy positive math fixtures were given explicit synthetic timestamps; missing evidence returns none. Trial confounders missing yield INSUFFICIENT_DATA. No dataset/model/hardware results were created.

Lock order review: FeedService→LinkManager→transport; FeedService→repository/event store; observation writes→repository only. No reverse lock cycle found in reviewed production paths. Caller-supplied fusion/runtime callbacks remain trusted/single-owner boundaries. stdout/journald/SD quotas and native allocations are external deployment responsibilities; bounded Python dictionaries/deques/ledger/retention do not prove those are bounded.

Reproduce: install `requirements-quality.txt` into isolated dev venv; run `scripts/run_checks.ps1`, then `python scripts/run_quality_checks.py`, `python scripts/make_release_manifest.py`, `python scripts/make_release_manifest.py --verify`. `.release/` is ignored metadata/log evidence, not a source dump or physical result. Frozen v1 bytes and all physical outputs remain unchanged/disabled.
