# Demo script

## A. Software demo today — explicitly SYNTHETIC / MOCK

1. Show final host check summary and M2/unverified labels.
2. From `jetson/`, run `python -m tools.demo_replay`; explain supplied synthetic identity/behavior and fixture frames, not recognition of a real cat.
3. Run `python -m tools.run_simulator NORMAL`; show synthetic feed lifecycle and independent rejection/fault scenarios. ACK is receipt, final simulated SUCCESS is not food dispensing.
4. Start local-only mock API with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`; show readiness/history contracts and missing real sensors/models. Existing Web/App is not integrated by this demo.
5. Run capture-session **dry-run** with explicit future camera source; show manifest plan/no camera opened. Show candidate registry and empty dataset report. Fixture test output is data-pipeline evidence only.
6. Present diagrams, requirements/traceability and remaining bench/data gates. Stop processes explicitly.

## B. Future full hardware demo — NOT EXECUTED

After device/voltage/pins/sensors/persistence/actuator rig/model/network evidence: real camera frames → validated shadow identity/behavior → supervised gated feeding → measured HX711 grams/final outcome → calibrated water state/bounded pump → persistent eating/drinking/history → actual Web/App contract display. Demonstrate invalid sensors/link/reset stop behavior in a controlled rig. Label all observed versus commanded states; no volume/health claim without measurement. Do not place an animal in an unverified actuator experiment.
