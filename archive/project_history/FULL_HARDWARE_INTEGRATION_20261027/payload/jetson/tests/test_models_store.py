from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.ai.models import Identity, Recognition
from app.behavior.models import Behavior, FoodPreferenceEvidence, VisitRecord
from app.camera.mock_camera import MockCameraProvider
from app.storage.event_store import Event, EventStore, InMemoryEventStore, SQLiteEventStore


def test_mock_camera_and_models():
    frame = MockCameraProvider().capture()
    assert (frame.width, frame.height, frame.synthetic, len(frame.pixels)) == (2, 2, True, 12)
    now = datetime.now(timezone.utc)
    assert Recognition(timestamp=now, identity=Identity.OWNER_CAT).confidence is None
    record = VisitRecord(timestamp=now, identity=Identity.OWNER_CAT, behavior=Behavior.EATING,
                         feeding_session_id="session-1", food_type="dry", eating_start=now,
                         eating_end=now + timedelta(seconds=20), eating_duration_seconds=20,
                         food_dispensed_grams=50, food_remaining_grams=40,
                         estimated_food_consumed_grams=10, repeat_visits=1)
    assert record.eating_duration_seconds == 20
    assert FoodPreferenceEvidence(food_type="dry", feeding_session_ids=["s1", "s2"]).repeat_visits == []
    with pytest.raises(ValidationError):
        VisitRecord(timestamp=now, eating_start=now + timedelta(seconds=1), eating_end=now)


@pytest.mark.parametrize("factory", [lambda: InMemoryEventStore(max_events=3),
                                     lambda: SQLiteEventStore(":memory:", max_events=3)])
def test_event_store_contract_and_retention(factory):
    store = factory()
    assert isinstance(store, EventStore)
    for i in range(5):
        store.append(Event(kind="FEED" if i % 2 else "DRINKING", request_id=i))
    assert [event.request_id for event in store.list(limit=500)] == [4, 3, 2]
    assert [event.request_id for event in store.list(kind="FEED")] == [3]
    assert store.list(limit=0) == []
    store.close()


def test_in_memory_store_copies_events():
    store = InMemoryEventStore(max_events=1)
    original = Event(kind="BEHAVIOR", details={"tags": ["first"]})
    store.append(original)
    original.details["tags"].append("changed")
    store.list()[0].details["tags"].append("changed again")
    assert store.list()[0].details == {"tags": ["first"]}


def test_sqlite_event_store_persistence_and_startup_retention(tmp_path):
    path = tmp_path / "events.db"
    store = SQLiteEventStore(path, max_events=3)
    for i in range(5):
        store.append(Event(kind="FEED" if i % 2 else "DRINKING", request_id=i))
    assert [event.request_id for event in store.list(limit=500)] == [4, 3, 2]
    assert [event.request_id for event in store.list(kind="FEED")] == [3]
    store.close()
    reopened = SQLiteEventStore(path, max_events=2)
    assert [event.request_id for event in reopened.list()] == [4, 3]
    reopened.close()


def test_event_metadata_and_timestamps_are_bounded():
    with pytest.raises(ValidationError):
        Event(kind="FEED", details={"text": "x" * 3000})
    with pytest.raises(ValidationError):
        Event(kind="FEED", timestamp=datetime(2026, 1, 1))
