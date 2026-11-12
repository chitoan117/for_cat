import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.serial_link.mock_transport import MockEsp32Transport
from app.serial_link.protocol import Command, FeedCode, Frame, decode, encode
from app.storage.event_store import InMemoryEventStore


@pytest.fixture
def system():
    transport = MockEsp32Transport()
    with TestClient(create_app(transport=transport, store=InMemoryEventStore())) as client:
        yield client, transport


def test_health_status_events_and_reserved_routes(system):
    client, _ = system
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    status = client.get("/api/v1/status").json()
    assert status["esp32_online"] is True and status["feeds"] == []
    assert status["camera"] == status["esp32"] == "MOCK"
    assert status["sensors"] == "NOT_CONNECTED"
    assert client.get("/api/v1/events").json() == []


@pytest.mark.parametrize("route", ["behavior", "feeding-history", "drinking-history"])
def test_empty_history_is_structured_list_without_observations(system, route):
    client, _ = system
    response = client.get(f"/api/v1/{route}")
    assert response.status_code == 200
    assert response.json() == []


def test_ack_only_pending_then_success(system):
    client, transport = system
    response = client.post("/api/v1/feed/manual")
    assert response.status_code == 202
    request_id = response.json()["request_id"]
    assert response.json()["state"] == "PENDING"
    assert [e["state"] for e in reversed(client.get("/api/v1/events").json())] == ["REQUEST_RECEIVED", "PENDING"]
    assert client.get("/api/v1/status").json()["feeds"][0]["state"] == "PENDING"
    transport.complete_feed(request_id, FeedCode.SUCCESS)
    assert client.get("/api/v1/status").json()["feeds"][0]["state"] == "SUCCESS"
    assert client.get("/api/v1/feeding-history").json()[0]["state"] == "SUCCESS"


@pytest.mark.parametrize("outcome", [FeedCode.REJECTED, FeedCode.ERROR])
def test_terminal_operation_results(system, outcome):
    client, transport = system
    request_id = client.post("/api/v1/feed/manual").json()["request_id"]
    transport.complete_feed(request_id, outcome)
    assert client.get("/api/v1/status").json()["feeds"][0]["state"] == outcome.name


def test_nack_rejected(system):
    client, transport = system
    transport.reject_requests = True
    assert client.post("/api/v1/feed/manual").json()["state"] == "REJECTED"


@pytest.mark.parametrize("failure", ["online", "timeout"])
def test_offline_or_timeout_before_ack_is_error(system, failure):
    client, transport = system
    setattr(transport, failure, False if failure == "online" else True)
    assert client.get("/api/v1/status").json()["esp32_online"] is False
    result = client.post("/api/v1/feed/manual").json()
    assert result["state"] == "ERROR"
    assert [e["state"] for e in reversed(client.get("/api/v1/events").json())] == ["REQUEST_RECEIVED", "ERROR"]


def test_timeout_after_ack_does_not_claim_result(system):
    client, transport = system
    client.post("/api/v1/feed/manual")
    transport.timeout = True
    status = client.get("/api/v1/status").json()
    assert status["esp32_online"] is False
    assert status["feeds"][0]["state"] == "PENDING"


def test_unexpected_ack_and_wrong_id_are_errors():
    class BadTransport:
        def exchange(self, request):
            frame = decode(request)
            return encode(Frame(frame.request_id + 1, Command.ACK, bytes([Command.FEED_REQUEST])))

    with TestClient(create_app(transport=BadTransport(), store=InMemoryEventStore())) as client:
        assert client.post("/api/v1/feed/manual").json()["state"] == "ERROR"


def test_events_persist_and_recover_recent_feed(tmp_path):
    path = tmp_path / "persist.db"
    with TestClient(create_app(path)) as client:
        client.post("/api/v1/feed/manual")
    with TestClient(create_app(path)) as client:
        assert client.get("/api/v1/status").json()["feeds"][0]["state"] == "PENDING"
        assert client.post("/api/v1/feed/manual").json()["request_id"] == 2
