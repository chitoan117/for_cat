"""Event-shaped API projections of canonical typed visits; no duplicate event writes."""

from app.behavior.models import Behavior
from app.storage.event_store import Event, EventStore
from app.storage.repositories import RecordRepository


def history(store: EventStore, records: RecordRepository, kind: str | None,
            limit: int = 100) -> list[Event]:
    limit = max(0, min(limit, store.max_events, 1000))
    events = store.list(limit, kind)
    session_ids = {x.details.get("session_id") for x in events if x.details.get("session_id")}
    typed_kind = "drinking" if kind == "DRINKING" else "behavior"
    if kind in (None, "BEHAVIOR", "DRINKING", "FEED"):
        for row in records.list(typed_kind, limit=limit):
            if row.session_id in session_ids:
                continue
            if kind == "FEED" and row.behavior != Behavior.EATING:
                continue
            event_kind = ("DRINKING" if typed_kind == "drinking" else
                          "EATING" if kind == "FEED" else "BEHAVIOR")
            events.append(Event(kind=event_kind, timestamp=row.started_at,
                                details=row.model_dump(mode="json")))
    return sorted(events, key=lambda event: event.timestamp, reverse=True)[:limit]
