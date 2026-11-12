"""Current v1 public contract, input bounds and generated-schema compatibility."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.event_store import InMemoryEventStore
from scripts.api_contract import breaking_changes,current_schema


def test_openapi_snapshot_has_no_breaking_change_or_raw_file_endpoints():
    root=Path(__file__).resolve().parents[2]
    old=json.loads((root/"docs/openapi_v1.json").read_text(encoding="utf-8"))
    current=current_schema(); assert not breaking_changes(old,current)
    assert not any(word in path for path in current["paths"] for word in ("/gpio","/pump","/servo","/model","/upload"))
    removed=json.loads(json.dumps(old)); removed["paths"].pop("/api/v1/health")
    assert breaking_changes(old,removed)


@pytest.mark.parametrize("path",["health","readiness","status","events","behavior","feeding-history","drinking-history",
    "sessions/feeding","sessions/drinking","preferences","food-types","daily-summary"])
def test_each_existing_public_get_empty_schema(path):
    app=create_app(store=InMemoryEventStore())
    with TestClient(app) as client:
        result=client.get("/api/v1/"+path)
        assert result.status_code==200
        if path in ("events","behavior","feeding-history","drinking-history","sessions/feeding","sessions/drinking","preferences","food-types"):
            assert result.json()==[]
        assert "Traceback" not in result.text
        assert client.post("/api/v1/"+path).status_code==405


@pytest.mark.parametrize("identifier",["-1","0","4294967296","not-an-id","9"*200])
def test_polling_id_edges_never_expose_tracebacks(identifier):
    with TestClient(create_app(store=InMemoryEventStore())) as client:
        response=client.get("/api/v1/feed/manual/"+identifier)
        assert response.status_code in (400,422) and "detail" in response.json() and "Traceback" not in response.text


def test_limits_invalid_dates_and_undeclared_query_paths_are_not_control():
    with TestClient(create_app(store=InMemoryEventStore())) as client:
        for limit in ("-1","0","100000000000","bad"):
            result=client.get("/api/v1/events",params={"limit":limit})
            assert result.status_code in (200,422)
            if result.status_code==200: assert len(result.json())<=1000
        for day in ("2025-02-29","bad","9999-12-31"):
            assert client.get("/api/v1/daily-summary",params={"day":day}).status_code==422
        assert client.get("/api/v1/food-types",params={"path":"../../secret","food_type":"../../bad"}).json()==[]
        assert client.app.state.transport.feeds=={}


@pytest.mark.parametrize("payload",[b"",b"{}",b"\xff",b"x"*10000])
def test_manual_feed_empty_body_contract(payload):
    with TestClient(create_app(store=InMemoryEventStore())) as client:
        response=client.post("/api/v1/feed/manual",content=payload)
        assert response.status_code==(202 if not payload else 413)
        assert "Traceback" not in response.text
