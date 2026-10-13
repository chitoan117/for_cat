"""Schema-versioned, bounded typed records alongside generic events."""

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from threading import RLock

from pydantic import BaseModel

from app.storage.records import (BehaviorRecord, DrinkingSession, FeedingSession,
                                 FoodType, PreferenceSummary)
from app.storage.sqlite_policy import connect, database_health

SCHEMA_VERSION = 2
KINDS: dict[str, type[BaseModel]] = {
    "feeding": FeedingSession, "drinking": DrinkingSession,
    "behavior": BehaviorRecord, "food_type": FoodType,
    "preference": PreferenceSummary,
}


class RecordRepository:
    def __init__(self, path: str | Path = ":memory:", max_rows: int = 10000):
        if not 1 <= max_rows <= 100000:
            raise ValueError("max_rows out of range")
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.max_rows = max_rows
        self.lock = RLock()
        self.connection = connect(path)
        try:
            with self.lock, self.connection:
                version = self.connection.execute("PRAGMA user_version").fetchone()[0]
                if version not in (0, 1, SCHEMA_VERSION):
                    raise RuntimeError(f"unsupported record schema version: {version}")
                self.connection.execute(
                    "CREATE TABLE IF NOT EXISTS typed_records ("
                    "kind TEXT NOT NULL, id TEXT NOT NULL, occurred_at TEXT NOT NULL, body TEXT NOT NULL, "
                    "PRIMARY KEY(kind, id))"
                )
                self.connection.execute("CREATE INDEX IF NOT EXISTS idx_records_day "
                                        "ON typed_records(kind, occurred_at)")
                self.connection.execute(
                    "CREATE TABLE IF NOT EXISTS feed_requests ("
                    "request_id INTEGER PRIMARY KEY, client_key TEXT UNIQUE, state TEXT NOT NULL, "
                    "created_at TEXT NOT NULL)"
                )
                if version < SCHEMA_VERSION:
                    self.connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        except Exception:
            # Close after transaction __exit__, otherwise the original cause is masked.
            self.connection.close()
            raise

    def claim_feed(self, client_key: str | None) -> tuple[int, str, bool]:
        """Durable first-writer-wins ID allocation. At capacity, fail closed, never reuse IDs."""
        with self.lock, self.connection:
            self.connection.execute("BEGIN IMMEDIATE")  # serialize first-writer claim across connections
            if client_key is not None:
                old = self.connection.execute(
                    "SELECT request_id,state FROM feed_requests WHERE client_key=?", (client_key,)
                ).fetchone()
                if old:
                    return old[0], old[1], False
            count, last_id = self.connection.execute(
                "SELECT COUNT(*),COALESCE(MAX(request_id),0) FROM feed_requests"
            ).fetchone()
            if count >= self.max_rows or last_id >= 0xFFFFFFFF:
                raise OverflowError("feed request ledger full; new operations blocked")
            new_id = last_id + 1
            self.connection.execute(
                "INSERT INTO feed_requests(request_id,client_key,state,created_at) VALUES (?,?,?,?)",
                (new_id, client_key, "REQUEST_RECEIVED", datetime.now(timezone.utc).isoformat()),
            )
            return new_id, "REQUEST_RECEIVED", True

    def set_feed_state(self, request_id: int, state: str) -> None:
        with self.lock, self.connection:
            cursor = self.connection.execute(
                "UPDATE feed_requests SET state=? WHERE request_id=?", (state, request_id)
            )
            if cursor.rowcount != 1:
                raise ValueError("feed request missing from durable ledger")

    def commit_feed_state(self, request_id: int, state: str, terminal: FeedingSession | None = None) -> None:
        """Ledger and terminal materialization commit before a result is published."""
        if state not in ("REQUEST_RECEIVED", "PENDING", "SUCCESS", "REJECTED", "ERROR"):
            raise ValueError("invalid feed state")
        if terminal is not None and (terminal.session_id != f"feed-{request_id}" or terminal.result != state):
            raise ValueError("mismatched terminal record")
        with self.lock, self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            previous = self.connection.execute("SELECT state FROM feed_requests WHERE request_id=?", (request_id,)).fetchone()
            if previous is None:
                raise ValueError("feed request missing from durable ledger")
            if previous[0] in ("SUCCESS", "REJECTED", "ERROR") and previous[0] != state:
                raise ValueError("terminal result cannot be changed")
            self.connection.execute("UPDATE feed_requests SET state=? WHERE request_id=?", (state, request_id))
            if terminal is not None:
                old = self.connection.execute("SELECT body FROM typed_records WHERE kind='feeding' AND id=?", (terminal.session_id,)).fetchone()
                if old:
                    if FeedingSession.model_validate_json(old[0]).result != state:
                        raise ValueError("conflicting terminal result")
                else:
                    self.connection.execute("INSERT INTO typed_records(kind,id,occurred_at,body) VALUES ('feeding',?,?,?)",
                        (terminal.session_id, terminal.requested_at.isoformat(), terminal.model_dump_json()))
                    self.connection.execute("DELETE FROM typed_records WHERE kind='feeding' AND id NOT IN "
                        "(SELECT id FROM typed_records WHERE kind='feeding' ORDER BY occurred_at DESC,id DESC LIMIT ?)", (self.max_rows,))

    def find_feed(self, *, client_key: str | None = None,
                  request_id: int | None = None) -> tuple[int, str] | None:
        if client_key is None and request_id is None:
            raise ValueError("feed key or ID required")
        with self.lock:
            if client_key is not None:
                return self.connection.execute(
                    "SELECT request_id,state FROM feed_requests WHERE client_key=?", (client_key,)
                ).fetchone()
            return self.connection.execute(
                "SELECT request_id,state FROM feed_requests WHERE request_id=?", (request_id,)
            ).fetchone()

    def recent_feeds(self, limit: int = 256) -> list[tuple[int, str, str | None, str]]:
        with self.lock:
            return self.connection.execute(
                "SELECT request_id,state,client_key,created_at FROM feed_requests ORDER BY request_id DESC LIMIT ?",
                (max(0, min(limit, 256)),),
            ).fetchall()

    def add(self, kind: str, record: BaseModel) -> None:
        model = KINDS.get(kind)
        if model is None or not isinstance(record, model):
            raise ValueError("unknown kind or wrong record type")
        record_id = record.food_type if kind in ("food_type", "preference") else record.session_id
        when = (getattr(record, "requested_at", None) or getattr(record, "started_at", None)
                or getattr(record, "calculated_at", None) or datetime.now(timezone.utc))
        body = record.model_dump_json()
        if len(body.encode("utf-8")) > 16384:
            raise ValueError("record too large")
        with self.lock, self.connection:
            try:
                self.connection.execute(
                    "INSERT INTO typed_records (kind,id,occurred_at,body) VALUES (?,?,?,?)",
                    (kind, record_id, when.astimezone(timezone.utc).isoformat(), body),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("record already exists; never silently overwrite") from exc
            self.connection.execute(
                "DELETE FROM typed_records WHERE kind=? AND id NOT IN "
                "(SELECT id FROM typed_records WHERE kind=? ORDER BY occurred_at DESC, id DESC LIMIT ?)",
                (kind, kind, self.max_rows),
            )

    def add_visit(self, behavior: BehaviorRecord, drinking: DrinkingSession | None = None) -> bool:
        """Atomic canonical visit write. Exact retry is idempotent; conflicts never overwrite."""
        entries = [("behavior", behavior)]
        if drinking is not None:
            if (drinking.session_id != behavior.session_id or drinking.cat_identity != behavior.cat_identity
                    or drinking.started_at != behavior.started_at or drinking.ended_at != behavior.ended_at):
                raise ValueError("mismatched visit evidence")
            entries.append(("drinking", drinking))
        with self.lock, self.connection:
            existing = self.connection.execute(
                "SELECT body FROM typed_records WHERE kind='behavior' AND id=?", (behavior.session_id,)
            ).fetchone()
            if existing:
                if BehaviorRecord.model_validate_json(existing[0]) != behavior:
                    raise ValueError("conflicting visit ID; not overwritten")
                if drinking is not None:
                    stored = self.connection.execute("SELECT body FROM typed_records WHERE kind='drinking' AND id=?",
                                                     (drinking.session_id,)).fetchone()
                    if stored is None or DrinkingSession.model_validate_json(stored[0]) != drinking:
                        raise ValueError("conflicting drinking materialization; not overwritten")
                return False
            for kind, record in entries:
                body = record.model_dump_json()
                if len(body.encode()) > 16384:
                    raise ValueError("visit too large")
                self.connection.execute(
                    "INSERT INTO typed_records(kind,id,occurred_at,body) VALUES (?,?,?,?)",
                    (kind, record.session_id, record.started_at.isoformat(), body),
                )
                self.connection.execute(
                    "DELETE FROM typed_records WHERE kind=? AND id NOT IN "
                    "(SELECT id FROM typed_records WHERE kind=? ORDER BY occurred_at DESC,id DESC LIMIT ?)",
                    (kind, kind, self.max_rows),
                )
        return True

    def list(self, kind: str, limit: int = 100, day: date | None = None) -> list[BaseModel]:
        if kind not in KINDS:
            raise ValueError("unknown kind")
        limit = max(0, min(limit, 1000, self.max_rows))
        with self.lock:
            if day is None:
                rows = self.connection.execute(
                    "SELECT body FROM typed_records WHERE kind=? ORDER BY occurred_at DESC,id DESC LIMIT ?",
                    (kind, limit),
                ).fetchall()
            else:
                rows = self.connection.execute(
                    "SELECT body FROM typed_records WHERE kind=? AND occurred_at>=? "
                    "AND occurred_at<? ORDER BY occurred_at DESC,id DESC LIMIT ?",
                    (kind, day.isoformat(), date.fromordinal(day.toordinal() + 1).isoformat(), limit),
                ).fetchall()
        return [KINDS[kind].model_validate_json(row[0]) for row in rows]

    def get(self, kind: str, record_id: str) -> BaseModel | None:
        if kind not in KINDS or len(record_id) > 64:
            return None
        with self.lock:
            row = self.connection.execute(
                "SELECT body FROM typed_records WHERE kind=? AND id=?", (kind, record_id)
            ).fetchone()
        return KINDS[kind].model_validate_json(row[0]) if row else None

    def count(self, kind: str, day: date | None = None) -> int:
        if kind not in KINDS:
            raise ValueError("unknown kind")
        with self.lock:
            if day is None:
                return self.connection.execute("SELECT COUNT(*) FROM typed_records WHERE kind=?", (kind,)).fetchone()[0]
            return self.connection.execute(
                "SELECT COUNT(*) FROM typed_records WHERE kind=? AND occurred_at>=? AND occurred_at<?",
                (kind, day.isoformat(), date.fromordinal(day.toordinal() + 1).isoformat()),
            ).fetchone()[0]

    def count_feed_requests(self, day: date) -> int:
        """Count pending ledger attempts as well as imported typed feeds, without double counting."""
        start, end = day.isoformat(), date.fromordinal(day.toordinal() + 1).isoformat()
        with self.lock:
            ledger = self.connection.execute("SELECT COUNT(*) FROM feed_requests WHERE created_at>=? AND created_at<?",
                                             (start, end)).fetchone()[0]
            imported = self.connection.execute(
                "SELECT COUNT(*) FROM typed_records WHERE kind='feeding' AND occurred_at>=? AND occurred_at<? "
                "AND id NOT IN (SELECT 'feed-' || request_id FROM feed_requests)", (start, end)).fetchone()[0]
        return ledger + imported

    def close(self) -> None:
        with self.lock:
            self.connection.close()

    def health(self) -> str:
        with self.lock:
            return database_health(self.connection)
