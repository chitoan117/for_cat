import sqlite3

import pytest

from app.storage.event_store import Event, SQLiteEventStore
from app.storage.repositories import RecordRepository
from tools.db_maintenance import backup, inspect, reset


def test_development_database_backup_reset_requires_confirmation(tmp_path):
    path = tmp_path / "history.db"
    events = SQLiteEventStore(path)
    events.append(Event(kind="FEED", state="PENDING"))
    events.close()
    records = RecordRepository(path)
    records.claim_feed("synthetic-key")
    records.close()
    assert inspect(path)["counts"]["events"] == 1
    assert inspect(path)["schema_version"] == 2
    copy = tmp_path / "backup.db"
    assert backup(path, copy)["status"] == "DRY_RUN"
    assert not copy.exists()
    assert backup(path, copy, apply=True)["status"] == "BACKED_UP"
    assert inspect(copy)["counts"]["feed_requests"] == 1
    with pytest.raises(ValueError, match="already exists"):
        backup(path, copy, apply=True)
    assert reset(path, allowed_root=tmp_path)["status"] == "DRY_RUN"
    with pytest.raises(ValueError, match="--confirm"):
        reset(path, allowed_root=tmp_path, apply=True)
    assert inspect(path)["counts"]["events"] == 1
    outcome = reset(path, allowed_root=tmp_path, apply=True, confirm="RESET_DEV_DB")
    assert outcome["status"] == "RESET_DEV_DB"
    assert inspect(path)["counts"] == {"events": 0, "typed_records": 0, "feed_requests": 0}
    assert inspect(path)["schema_version"] == 2
    assert inspect(type(path)(outcome["snapshot"]))["counts"]["events"] == 1


def test_reset_refuses_outside_dev_directory_and_missing_database(tmp_path):
    outside = tmp_path / "elsewhere.db"
    with pytest.raises(ValueError, match="development data"):
        reset(outside, allowed_root=tmp_path / "data", apply=True, confirm="RESET_DEV_DB")
    assert inspect(outside)["status"] == "DB_NOT_AVAILABLE"
