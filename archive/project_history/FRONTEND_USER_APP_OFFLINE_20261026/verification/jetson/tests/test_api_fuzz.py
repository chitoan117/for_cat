import random

from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.event_store import InMemoryEventStore


def test_bounded_rest_input_fuzz_never_returns_server_error():
    # SYNTHETIC_TEST_DATA: deterministic malformed input, no physical feed.
    rng = random.Random(0xF00D)
    alphabet = "abcXYZ019_-!@/ "
    with TestClient(create_app(store=InMemoryEventStore(max_events=8))) as client:
        for _ in range(120):
            identifier = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 90)))
            path = f"/api/v1/feed/manual/{identifier}"
            assert client.get(path).status_code in (200, 400, 404, 405, 422)
            result = client.post("/api/v1/feed/manual", headers={"Idempotency-Key": identifier})
            assert result.status_code in (200, 202, 400, 429, 503)
        assert client.post("/api/v1/feed/manual", content=b"a" * 10000).status_code == 413
