"""Opt-in local SQLite inspection/backup/reset; no REST access and no silent deletion."""

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import DATA_PATH

DEV_DATA = DATA_PATH.parent
KNOWN_TABLES = ("events", "typed_records", "feed_requests")
CONFIRMATION = "RESET_DEV_DB"


def inspect(path: Path) -> dict:
    if not path.is_file():
        return {"status": "DB_NOT_AVAILABLE", "path": str(path)}
    with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as conn:
        integrity = conn.execute("PRAGMA quick_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError("database quick_check failed")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                  for name in KNOWN_TABLES if name in tables}
        return {"status": "DATABASE_OK", "path": str(path),
                "schema_version": conn.execute("PRAGMA user_version").fetchone()[0],
                "counts": counts}


def backup(path: Path, destination: Path, *, apply: bool = False) -> dict:
    state = inspect(path)
    if state["status"] == "DB_NOT_AVAILABLE":
        return state
    if destination.exists() or destination.resolve() == path.resolve():
        raise ValueError("backup destination already exists or equals source")
    if not apply:
        return {"status": "DRY_RUN", "source": str(path), "backup": str(destination)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Reserve exclusively before opening SQLite target. Never replace an existing backup.
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)
                target.commit()
        inspect(destination)  # refuse to call an invalid snapshot a backup
    except Exception:
        destination.unlink()  # only our new exclusive-create file
        raise
    return {"status": "BACKED_UP", "source": str(path), "backup": str(destination)}


def reset(path: Path, *, allowed_root: Path = DEV_DATA, apply: bool = False,
          confirm: str | None = None) -> dict:
    target, root = path.resolve(), allowed_root.resolve()
    if not target.is_relative_to(root) or target.suffix != ".db":
        raise ValueError("reset permitted only for .db files under the development data directory")
    state = inspect(target)
    if state["status"] == "DB_NOT_AVAILABLE":
        return state
    if not apply:
        return {"status": "DRY_RUN", "database": str(target), "counts": state["counts"],
                "requires": f"--apply --confirm {CONFIRMATION}"}
    if confirm != CONFIRMATION:
        raise ValueError(f"reset requires --apply --confirm {CONFIRMATION}")
    archive = root / "backups" / (f"pre-reset-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-"
                                    f"{uuid4().hex[:8]}.db")
    result = backup(target, archive, apply=True)
    with closing(sqlite3.connect(target)) as conn:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            for table in state["counts"]:  # table names came only from KNOWN_TABLES
                conn.execute(f"DELETE FROM {table}")
    return {"status": "RESET_DEV_DB", "database": str(target),
            "snapshot": result["backup"], "previous_counts": state["counts"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local development SQLite maintenance only")
    parser.add_argument("action", choices=("inspect", "backup", "reset"))
    parser.add_argument("--database", type=Path, default=DATA_PATH)
    parser.add_argument("--output", type=Path, help="exclusive backup destination")
    parser.add_argument("--apply", action="store_true", help="default is dry-run")
    parser.add_argument("--confirm", help=f"exactly {CONFIRMATION} for reset")
    args = parser.parse_args()
    try:
        if args.action == "inspect":
            result = inspect(args.database)
        elif args.action == "backup":
            if args.output is None:
                parser.error("backup requires --output")
            result = backup(args.database, args.output, apply=args.apply)
        else:
            result = reset(args.database, apply=args.apply, confirm=args.confirm)
        print(json.dumps(result, indent=2))
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(2, f"DB_MAINTENANCE_FAILED: {exc}\n")
