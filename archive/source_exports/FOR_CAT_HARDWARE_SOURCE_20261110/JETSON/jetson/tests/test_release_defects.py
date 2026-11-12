"""Risk regressions; synthetic/fake evidence ONLY, no hardware/model activation."""
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.ai.models import Identity
from app.behavior.models import Behavior
from app.behavior.fusion import WeightSample, estimate_consumed
from app.behavior.temporal import SessionSignal, SignalType
from app.main import create_app
from app.serial_link.protocol import Command, FeedCode, Frame, FrameStreamDecoder, encode
from app.storage.event_store import InMemoryEventStore


def test_fragmented_valid_payload_does_not_emit_nested_frame():
    nested = encode(Frame(99, Command.PING))
    outer = Frame(7, Command.ACK, b"prefix" + nested + b"suffix")
    data = encode(outer)
    parser = FrameStreamDecoder()
    cut = 10 + len(b"prefix") + len(nested)
    assert parser.feed(data[:cut], 0) == []
    assert parser.feed(data[cut:], 0.1) == [outer]


def test_import_main_does_not_create_a_database(tmp_path):
    path = tmp_path / "must-not-exist.db"
    environment = {**os.environ, "DATABASE_PATH": str(path), "PYTHONPATH": os.pathsep.join(("jetson", "."))}
    code = "import sqlite3; sqlite3.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('DB opened on import')); import app.main, ai.capture, ai.experiments, app.ai.service"
    result = subprocess.run([sys.executable, "-c", code], env=environment, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert not path.exists()


def test_failed_terminal_insert_does_not_publish_or_commit_success():
    app = create_app(store=InMemoryEventStore())
    with TestClient(app, raise_server_exceptions=False) as client:
        request_id = client.post("/api/v1/feed/manual").json()["request_id"]
        app.state.transport.complete_feed(request_id, FeedCode.SUCCESS)
        app.state.records.connection.set_authorizer(lambda action, arg1, *rest:
            sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_INSERT and arg1 == "typed_records" else sqlite3.SQLITE_OK)
        response = client.get("/api/v1/status")
        assert response.status_code == 503
        assert response.json() == {"detail": "local storage unavailable"}
        assert app.state.records.find_feed(request_id=request_id)[1] == "PENDING"
        assert app.state.feeds.get(request_id).state.value == "PENDING"
        app.state.records.connection.set_authorizer(None)
        assert client.get("/api/v1/status").json()["feeds"][0]["state"] == "SUCCESS"
        assert app.state.records.count("feeding") == 1
        assert client.get("/api/v1/status").status_code == 200
        assert app.state.records.count("feeding") == 1


def test_body_cannot_bypass_feed_bound_with_content_length_zero():
    with TestClient(create_app(store=InMemoryEventStore())) as client:
        response = client.post("/api/v1/feed/manual", content=b"\xffunexpected", headers={"Content-Length": "0"})
        assert response.status_code == 413
        assert not client.app.state.transport.feeds


def test_fusion_rejects_missing_stale_or_mismatched_weight_evidence():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    start = SessionSignal(signal=SignalType.START, session_id="synthetic", identity=Identity.OWNER_CAT,
                          behavior=Behavior.EATING, started_at=now)
    end = start.model_copy(update={"signal": SignalType.END, "ended_at": now + timedelta(seconds=10)})
    assert estimate_consumed(start, end, [WeightSample(50, True)] * 3, [WeightSample(40, True)] * 3) is None
    stale = [WeightSample(50, True, now - timedelta(minutes=5))] * 3
    after = [WeightSample(40, True, end.ended_at)] * 3
    assert estimate_consumed(start, end, stale, after) is None
    before = [WeightSample(50, True, now)] * 3
    assert estimate_consumed(start, end, before, after) == 10
    assert estimate_consumed(start, end.model_copy(update={"identity": Identity.OTHER_CAT}), before, after) is None


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), -1])
def test_temporal_rejects_invalid_confidence_configuration(bad):
    from app.behavior.temporal import TemporalEngine
    with pytest.raises(ValueError):
        TemporalEngine(min_confidence=bad)
