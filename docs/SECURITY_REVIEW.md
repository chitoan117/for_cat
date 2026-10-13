# Local pre-hardware security review

Reviewed boundaries: `app/{main,config}.py`, API feed lifecycle, runtime paths, SQLite policies, serial framing and new data/model tools. This is a bounded source/host-test review, not production security certification or a dependency CVE scan.

| Area | Current behavior/evidence | Remaining work |
| --- | --- | --- |
| API exposure | API_HOST defaults127.0.0.1; no deployment/public binding changed | Auth/TLS/network review before remote use |
| CORS | Explicit HTTP(S) origins; wildcard rejected; empty by default | CORS is not access control/authentication |
| Raw actuators | No raw GPIO endpoint; SERIAL manual feed locally rejected; AI authorization false | Any future operational feed contract must retain MCU gates |
| Serial input | Bounded payload/parser/timeouts/CRC/request IDs; seven vectors/fuzz tests | CRC is corruption detection, not authentication; physical link evidence absent |
| Path traversal | New dataset/artifact readers reject absolute/rooted/drive/backslash/parent paths and resolved symlink escapes; model runtime also uses trusted root | Tools are trusted-local, not hardened multi-user upload services; avoid concurrent mutation/TOCTOU |
| Model insertion | Type/existence/hash/task/label metadata checks; inactive registry; no pickle/inference execution | Actual graph trust/correctness/runtime audit; no VALIDATED_JETSON promotion |
| Uploads/data | No API upload/Roboflow client/key; explicit CLI --apply; caps/staging/no silent overwrite | Review privacy, video/device metadata and annotation-platform policies before manual sharing |
| Capture | Default dry-run, explicit source/apply, child deadline and frame/storage budgets | Actual backend/device behavior still needs testing |
| Database | Parameterized queries, retention/metadata/pending bounds, WAL and bounded busy timeout, tested write-failure paths | Actual disk capacity/power-loss/backups; retention is not a disk quota |
| JSON/metadata | New artifact JSON cap5MB/nonfinite rejection; versioned schemas and task checks | Existing legacy metadata semantics remain distinct; release revalidation after changes |
| Secrets | New tools contain no API keys/credentials, no model download/upload and no environment-secret dump; package inventory only | Keep real tokens/private data out of source; ignored files still require operator privacy review |

Generated capture/data/model/run/check outputs are ignored. Logs/manifests may contain source paths/notes; do not publish them blindly. The old frontend is untouched. Full auth/hardening is deliberately future deployment work; default local/private behavior remains intact.
