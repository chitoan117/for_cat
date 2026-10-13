import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field, model_validator
from app.storage.sqlite_policy import connect


class Event(BaseModel):
    kind: str = Field(min_length=1, max_length=32)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: int | None = Field(default=None, ge=0, le=0xFFFFFFFF)
    state: str | None = Field(default=None, max_length=64)
    details: dict = Field(default_factory=dict, max_length=16)

    @model_validator(mode="after")
    def bound_details_and_timestamp(self):
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("event timestamp must be timezone aware")
        self.timestamp = self.timestamp.astimezone(timezone.utc)
        try:
            size = len(json.dumps(self.details, ensure_ascii=False).encode("utf-8"))
        except (TypeError, ValueError, RecursionError) as exc:
            raise ValueError("event metadata must be JSON serializable") from exc
        if size > 2048:
            raise ValueError("event metadata exceeds 2 KB")
        return self


@runtime_checkable
class EventStore(Protocol):
    max_events: int

    def append(self, event: Event) -> None: ...

    def list(self, limit: int = 100, kind: str | None = None) -> list[Event]: ...

    def close(self) -> None: ...


class InMemoryEventStore:
    def __init__(self, max_events: int = 1000):
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self.max_events = max_events
        self.lock = RLock()
        self.events: deque[Event] = deque(maxlen=max_events)

    def append(self, event: Event) -> None:
        with self.lock:
            self.events.append(event.model_copy(deep=True))

    def list(self, limit: int = 100, kind: str | None = None) -> list[Event]:
        limit = max(0, min(limit, self.max_events))
        with self.lock:
            return [event.model_copy(deep=True) for event in reversed(self.events)
                    if kind is None or event.kind == kind][:limit]

    def close(self) -> None:
        pass


class SQLiteEventStore:
    def __init__(self, path: str | Path, max_events: int = 1000):
        if max_events < 1:
            raise ValueError("max_events must be positive")
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.max_events = max_events
        self.lock = RLock()
        self.connection = connect(path)
        with self.lock, self.connection:
            self.connection.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL)")
            self._prune()

    def _prune(self) -> None:
        self.connection.execute(
            "DELETE FROM events WHERE seq NOT IN (SELECT seq FROM events ORDER BY seq DESC LIMIT ?)",
            (self.max_events,),
        )

    def append(self, event: Event) -> None:
        with self.lock, self.connection:
            self.connection.execute("INSERT INTO events (kind, body) VALUES (?, ?)", (event.kind, event.model_dump_json()))
            self._prune()

    def list(self, limit: int = 100, kind: str | None = None) -> list[Event]:
        limit = max(0, min(limit, self.max_events))
        with self.lock:
            if kind is None:
                rows = self.connection.execute("SELECT body FROM events ORDER BY seq DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = self.connection.execute("SELECT body FROM events WHERE kind = ? ORDER BY seq DESC LIMIT ?", (kind, limit)).fetchall()
        return [Event.model_validate_json(row[0]) for row in rows]

    def close(self) -> None:
        with self.lock:
            self.connection.close()
