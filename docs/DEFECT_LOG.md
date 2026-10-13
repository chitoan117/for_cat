# Defect log — evidenced findings only

Statuses: OPEN, BLOCKED_HARDWARE, BLOCKED_DATA, DEFERRED, RESOLVED. RED tests/source analysis and rerun evidence distinguish defects from future desired features. No bugs invented to raise test counts.

| ID | Verified issue / scope | Status | Resolution / remaining evidence |
| --- | --- | --- | --- |
| DQ-01 | Speculative stream resync emits CRC-valid nested payload frame before outer completes | RESOLVED | Wait for outer length/CRC or candidate timeout; malformed-length recovery now timeout-bound;7 vectors/wire unchanged |
| DQ-02 | Plain app.main import opened/created SQLite | RESOLVED | Lazy compatibility attribute for explicit uvicorn app lookup; isolated import trap passes |
| DQ-03 | Terminal result published/ledger committed before feeding materialization succeeds | RESOLVED | Atomic ledger+typed transaction, publish after persistence; SQL denial/rollback/retry tests |
| DQ-04 | Content-Length:0 bypassed empty feed body contract | RESOLVED | Check stream regardless of zero header; body/UTF cases rejected |
| DQ-05 | Untimed/stale/mismatched weight evidence could yield consumption | RESOLVED | Internal sampled_at freshness/subject/interval guards, known portion bound; updated timed synthetic fixtures |
| DQ-06 | Temporal unconfirmed candidate bridged a long unobserved gap | RESOLVED | Candidate last-positive/dropout bound; no phantom duration; finite config/count saturation |
| DQ-07 | Nonfinite temporal/serial timing config could disable expected bounds | RESOLVED | Validate finite bounded config; typed records reject nonfinite measurements |
| DQ-08 | Same basenames in different session subfolders overwrite during ingestion | RESOLVED | Destination sample-ID names; hashes/cleanup collision regression |
| DQ-09 | Deep JSON/invalid manifest path/object/export mapping lacked clear resource/schema rejection | RESOLVED |64-level budget, valid filename, directory handling and provenance-label checks |
| DQ-10 | Partial exclusive metadata write left invalid registry file | RESOLVED | Clean only newly owned file on failure; preserve existing data |
| DQ-11 | Unsupported DB revision cause masked by closing before context exit | RESOLVED | Close after rollback; original error retained; owned factory store closed on failure |
| DQ-12 | Missing trial confounders could produce sufficient trend | RESOLVED | Missing context yields INSUFFICIENT_DATA, no trend/confidence claim |
| DQ-13 | Background/synchronous re-entry and join-self/shutdown-error state handling | RESOLVED (tested scope) | Reject managed re-entry, bounded stop/FAULTED; controlled model/DB-write cleanup tests |
| DQ-19 | Legacy preference path scored UNKNOWN/OTHER weight rows as owner trend | RESOLVED | Known OWNER attribution required; negative-subject RED tests then PASS; positive synthetic fixture explicitly identifies its subject |
| DQ-14 | Generic event store and durable ledger are separate transactions | DEFERRED | Generic history may have a gap under event-write failure; durable terminal truth retained/reconciled, no resend; tested and explicitly reported |
| DQ-15 | Native camera/model/serial backend may block despite requested timeout | BLOCKED_HARDWARE | Python thread cannot forcibly cancel native IO; honest FAULTED/worker-alive, process intervention and real target evidence required |
| DQ-16 | V1 has no boot nonce/durable MCU result replay or sensor telemetry | DEFERRED / BLOCKED_HARDWARE | Host IDs never wrap/reuse; peer-reset unknown result stays pending; physical feeds blocked, no protocol change |
| DQ-17 | Supplied VALIDATED_SENSOR metadata cannot independently prove calibration/attribution | BLOCKED_HARDWARE / BLOCKED_DATA | Actual reference/session/source evidence required; no physical claim from unit inputs |
| DQ-18 | Full target ABI, SD/NVS power-loss, real corpus/model/tracking absent | BLOCKED_HARDWARE / BLOCKED_DATA | Existing gates/risk register; not fabricated or solved by more mocks |

Tool/test issues diagnosed during this pass: byte-index limit in sparse soak fixture (fixed, not camera defect); link checker initially missed root README references (fixed); PlatformIO CLI lacks `pkg list --json-output` (used actual matching local manifest instead); CPython3.14 accepted deep JSON (explicit budget added). None is hidden by a warning filter. Runtime/source architecture, UART bytes and actuator gates unchanged.
