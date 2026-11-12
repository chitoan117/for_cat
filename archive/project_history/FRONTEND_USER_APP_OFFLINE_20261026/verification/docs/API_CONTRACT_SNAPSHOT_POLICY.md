# API v1 snapshot policy

`docs/openapi_v1.json` is the actual generated existing FastAPI v1 schema, exported via an in-memory app without startup/devices/on-disk DB. `scripts/api_contract.py` checks existing paths/methods/schemas/parameters/responses; descriptions/titles and added keys are allowed, removal/type/enum/required/parameter changes require explicit contract review. The conservative comparator intentionally requires review of changed contract lists even when a change might be additive.

No endpoint was introduced. POST manual feed now documents its existing202/200 and400/413/429/error responses; polling documents400/404. Storage errors are explicit503 with `{ "detail": "local storage unavailable" }`, not an unhandled traceback or prematurely published SUCCESS. Request body must be empty even if Content-Length lies. Validation422 uses the framework detail list; unknown GET query fields are ignored by the existing framework policy, never file/model controls. Limits remain bounded/clamped; invalid dates/IDs are rejected.

Quality tests cover every existing public GET, manual feed and polling, empty responses, method rejection, boundary IDs/limits/dates, body/UTF-8 handling and absence of raw actuator/model/file/upload endpoints. Dynamic untyped dict endpoints remain partially specified by OpenAPI; runtime field/error tests supplement it. Snapshot is a compatibility baseline, not old frontend validation or production auth.

Generate a first snapshot explicitly with `python scripts/api_contract.py --write`; existing snapshots are not silently replaced. Future approved changes need reviewed diff/policy plus an intentionally updated artifact. Check with `python scripts/api_contract.py`. Source/runtime wire remains UART v1 with unchanged golden vectors.
