# Local demo access and startup

Scheduled Worker update2026-10-26: the existing API now starts an ASGI background
DRY RUN scheduler from50-scheduled-dry-run.conf. It does not start a separate
systemd actuator/AI/serial service. The existing API boot enablement/lingering
also preserves this worker's startup. See [SCHEDULED_WORKER.md](SCHEDULED_WORKER.md).
The original network-recovery description below predates this explicit worker activation.

## Preferred links

- `http://server-jetson.local:8000/app`
- `http://server-jetson.local:8000/kiosk`
- `http://server-jetson.local:8000/diagnostics`

These use the Jetson's existing Avahi/mDNS hostname, same backend/port and
same-origin REST/WS. Windows HTTP200 and actual Jetson Chromium REAL state/
Meal Plan views were verified at this hostname on2026-10-26. Observed IPv4 is
192.168.123.8, PC192.168.123.15. The old192.168.137.59 belonged to the previous
network and is not the current bookmark. No static IP, network profile, router,
firewall or public port-forward setting was changed.

If a client cannot resolve mDNS, read the Jetson's actual LAN IPv4 locally:

```sh
ip -4 -brief address
```

Use the connected LAN interface address, not docker0's172.17.0.1. Check from
Windows with `curl.exe --max-time 5 http://server-jetson.local:8000/api/status`.

## Existing services now enabled

The existing safe user services are enabled under default.target:

```sh
systemctl --user is-enabled for-cat-esp32-bridge for-cat-api for-cat-ai
systemctl --user is-active for-cat-esp32-bridge for-cat-api for-cat-ai
loginctl show-user toan -p Linger
```

Expected enabled/active and Linger=yes. Own-user lingering lets the manager run
without a logged-in desktop/SSH session. Existing unit ExecStart/configuration
is unchanged: one read-only C++ serial bridge, unchanged C++ detector/passive tap,
one existing REAL API, canonical database, reviewed Flutter artifact. No AUTO,
servo/pump or autonomous scheduler activation is part of enabling these units.

For an intentional manual recovery:

```sh
systemctl --user start for-cat-esp32-bridge for-cat-ai for-cat-api
```

Do not start separate camera/serial processes. The existing runner waits for an
available camera; bridge discovers its identified ESP32. Missing data must remain
UNKNOWN/null. The MCU's Echo acknowledgments are volatile and are not silently
enabled by boot services. The existing verified sensor-only helper is a separate
deliberate operation after safe telemetry/divider review.

No cold reboot was performed just to test configuration; enabled symlinks,
Linger and live services were checked. To opt out later, disable these specific
user services. Lingering is an account-wide setting: review other user jobs
before disabling it. Existing unit snapshots and pre-change Linger=no are in
the recovery evidence directory.

## Overnight review and graceful stop

The previous watch saved28110.011s (7h48m30s),938 periodic samples,937 API
successes/ESP32-connected/AI-online observations. The only API error was a
connection-refused sample at16:05:10Z during the planned API deployment restart.
HC valid19/937 and JSN valid16/937; most later distance samples were invalid/null.
Owner acceptance of basic~25cm ranging does not turn these into valid readings.
These are periodic30s observations, not every ultrasonic pulse or a calibration.

The source SUMMARY still said RUNNING and FINAL was absent after the later
reboot. Record INCOMPLETE_CAPTURE_NO_FINAL_FILE. Exact stop cause was not
established; the previous-boot persistent journal was unavailable. Original
files remain unmodified. Do not claim a full8h run from this capture.

`scripts/watch_real_overnight.py` now handles SIGTERM/SIGINT: graceful interruption
writes status INTERRUPTED, signal and actual elapsed duration to FINAL.json.
Actual Linux normal2s and own-child SIGTERM tests passed. Sudden power removal
or SIGKILL can still prevent finalization; a missing final stays incomplete.
The one-off watch is NOT enabled at boot and is not restarted automatically.

Evidence: `evidence/network_boot_recovery_20261026T011718847595Z/`, including
before-state, original overnight copy, watcher shutdown checks, browser proof
and an explicitly derived overnight review. Original36-file index and protected
AI hashes remain unchanged. Servo/pump/arm/AUTO flags remain disabled and
35g remains the future actual-added-mass target, HX gram calibration DEFERRED.
