# Development SQLite inspection, backup and reset

From `jetson/`, use `python -m tools.db_maintenance inspect` for schema version and counts. `python -m tools.db_maintenance backup --output data/backups/manual.db` is dry-run; add `--apply` for an exclusive-create SQLite snapshot that refuses to overwrite an existing file. A backup is not a hardware result.

**Stop the Jetson API before development reset.** `python -m tools.db_maintenance reset` only prints the planned action; `python -m tools.db_maintenance reset --apply --confirm RESET_DEV_DB` creates a verified, uniquely named pre-reset snapshot under `jetson/data/backups/` and clears only known development tables inside a SQLite transaction. It never exposes reset through REST and refuses files outside `jetson/data/`. Preserve and verify snapshots before resetting any device with real history. Do not copy the PC's ignored `events.db` to the Jetson as a validation result.

Typed schema uses explicit `PRAGMA user_version=2`; the generic events, typed records and durable feed-request ledger all live in the local SQLite file. Snapshot/restore procedures for a deployed system require separate hardware, power-loss and filesystem testing.
