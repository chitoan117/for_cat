from datetime import date, datetime, timedelta, timezone
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.ai.models import Identity
from app.analytics.preference import PreferencePolicy, trend
from app.main import create_app
from app.config import HardwareConfig
from app.storage.event_store import InMemoryEventStore
from app.storage.records import DrinkingSession, FeedingSession, FoodType
from app.storage.repositories import RecordRepository
from app.storage.summary import daily_summary


def synthetic_feeding(number: int, *, source: str = "SYNTHETIC_TEST_DATA") -> FeedingSession:
    return FeedingSession(session_id=f"synthetic-{number}", food_type="dry",
                          cat_identity=Identity.OWNER_CAT, requested_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                          dispensed_grams=20, estimated_consumed_grams=16,
                          approach_delay_seconds=10, repeat_visits=1, source=source,
                          result="SUCCESS",
                          eating_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                          eating_finished_at=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc))


def test_empty_typed_repo_schema_and_summary(tmp_path):
    db = tmp_path / "records.db"
    repo = RecordRepository(db)
    assert repo.list("feeding") == repo.list("drinking") == []
    assert daily_summary(repo, date(2026, 1, 1))["reliable_food_consumed_grams"] is None
    repo.add("food_type", FoodType(food_type="dry"))
    with pytest.raises(ValueError, match="already exists"):
        repo.add("food_type", FoodType(food_type="dry"))
    repo.add("feeding", synthetic_feeding(1))
    repo.add("drinking", DrinkingSession(session_id="drink-1", started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                                         duration_seconds=5))
    assert daily_summary(repo, date(2026, 1, 1))["feeding_sessions"] == 1
    assert daily_summary(repo, date(2026, 1, 1))["reliable_food_consumed_grams"] is None
    repo.close()
    again = RecordRepository(db)
    assert again.get("feeding", "synthetic-1").cat_identity == Identity.OWNER_CAT
    again.close()


def test_typed_repository_retention_and_rejects_naive_dates(tmp_path):
    repo = RecordRepository(tmp_path / "bounded.db", max_rows=2)
    for i in range(3):
        repo.add("feeding", synthetic_feeding(i))
    assert len(repo.list("feeding")) == 2
    with pytest.raises(ValueError):
        FeedingSession(session_id="naive", requested_at=datetime(2026, 1, 1))
    repo.close()


def test_preference_requires_multiple_reliable_sessions():
    assert trend("dry", [synthetic_feeding(1)])["status"] == "INSUFFICIENT_DATA"
    assert trend("dry", [synthetic_feeding(i, source="UNVALIDATED") for i in range(4)])["status"] == "INSUFFICIENT_DATA"
    result = trend("dry", [synthetic_feeding(i) for i in range(4)],
                   PreferencePolicy(allow_synthetic_test_data=True))
    assert result["status"] == "SUFFICIENT_DATA" and result["sessions"] == 4
    assert result["preference_trend"] == "HIGH" and result["method"] == "EXPERIMENTAL"
    assert "consumption_ratio_stddev" in result["evidence"]


def test_session_api_empty_and_body_idempotency_bounds():
    with TestClient(create_app(store=InMemoryEventStore(max_events=3))) as client:
        assert client.get("/api/v1/sessions/feeding").json() == []
        assert client.get("/api/v1/sessions/drinking").json() == []
        assert client.get("/api/v1/preferences").json() == []
        assert client.get("/api/v1/food-types").json() == []
        assert client.get("/api/v1/daily-summary?day=2026-01-01").json()["preference_status"] == "INSUFFICIENT_DATA"
        assert client.post("/api/v1/feed/manual", json={"grams": 20}).status_code == 413
        assert client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "wrong key"}).status_code == 400
        first = client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "once"}).json()
        assert client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "once"}).json() == first
        assert client.get(f"/api/v1/feed/manual/{first['request_id']}").json() == first
        assert client.get("/api/v1/feed/manual/0").status_code == 400
        assert client.get("/api/v1/feed/manual/999").status_code == 404


def test_durable_request_key_and_id_survive_event_pruning_and_restart(tmp_path):
    path = tmp_path / "durable.db"
    with TestClient(create_app(db_path=path, max_events=3)) as client:
        first = client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "same-key"}).json()
        client.post("/api/v1/feed/manual")  # prunes first key's generic events
    with TestClient(create_app(db_path=path, max_events=3)) as client:
        retry = client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "same-key"}).json()
        assert retry == first
        assert client.get(f"/api/v1/feed/manual/{first['request_id']}").json() == first
        assert client.post("/api/v1/feed/manual").json()["request_id"] == 3


def test_durable_ledger_fails_closed_at_capacity(tmp_path):
    repo = RecordRepository(tmp_path / "ledger.db", max_rows=2)
    assert repo.claim_feed("one") == (1, "REQUEST_RECEIVED", True)
    repo.set_feed_state(1, "PENDING")
    assert repo.claim_feed("one") == (1, "PENDING", False)
    assert repo.claim_feed("two")[0] == 2
    with pytest.raises(OverflowError, match="full"):
        repo.claim_feed("three")
    repo.close()


def test_schema_v1_migrates_explicitly_to_v2(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 1")
    repo = RecordRepository(path)
    assert repo.claim_feed("migrated")[0] == 1
    repo.close()
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2


def test_feed_rate_limit_and_default_cors_never_wildcard():
    with TestClient(create_app(store=InMemoryEventStore(max_events=100))) as client:
        preflight = client.options("/api/v1/feed/manual", headers={
            "Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
        assert preflight.headers.get("access-control-allow-origin") != "*"
        for i in range(30):
            assert client.post("/api/v1/feed/manual").status_code == 202
        assert client.post("/api/v1/feed/manual").status_code == 429
    explicit = HardwareConfig(cors_origins=("https://trusted.example",))
    with TestClient(create_app(store=InMemoryEventStore(), hardware=explicit)) as client:
        response = client.options("/api/v1/feed/manual", headers={
            "Origin": "https://trusted.example", "Access-Control-Request-Method": "POST"})
        assert response.headers.get("access-control-allow-origin") == "https://trusted.example"
