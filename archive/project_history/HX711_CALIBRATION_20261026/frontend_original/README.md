# Bữa ăn của MÈO — Flutter REAL frontend for for_cat

The original orange/blue five-tab design is preserved. Default provider is REAL;
it consumes the existing Jetson SystemState REST/WS and shared dry-run arbiter.
No frontend serial reader, second backend, fake grams or inventory fallback.

Production/demo local build (Windows Flutter SDK):

```text
flutter pub get
flutter analyze
flutter test
flutter build web --release --no-web-resources-cdn --base-href=/flutter/ --dart-define=FEEDER_MODE=real --output=<new-release-directory>
```

Serve the static artifact via the SAME existing Jetson backend using
FORCAT_FLUTTER_WEB_DIR. /kiosk and /app use the same build; URI path selects
MANUAL sub-source KIOSK or APP. /api/status, /api/ws/state and /api/feed/preview
are same-origin, not private HTTP calls from a Cloudflare HTTPS page.

FEEDER_API_BASE_URL is an optional explicit base URL for development. HTTPS
Cloudflare -> private HTTP/ws is subject to browser restrictions; CORS alone is
not a solution. The public pages.dev demo is not redeployed by local integration.

Development mock is explicit: --dart-define=FEEDER_MODE=mock. Its UI is labelled
MOCK. REAL failures become UNKNOWN/DISCONNECTED/STALE/null, never scenario values.

35g is the ACTUAL ADDED dispensing target for future calibrated closed-loop work.
Current controls create DRY RUN requests only. actual_dispensed_grams=null,
actuator_execution=false; no servo/pump operation. HX gram calibration DEFERRED.

Original source/build checkpoint: D:/for_cat/FLUTTER_REAL_INTEGRATION_20261025.

## Original template notes (historical)

A new Flutter project.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Learn Flutter](https://docs.flutter.dev/get-started/learn-flutter)
- [Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Flutter learning resources](https://docs.flutter.dev/reference/learning-resources)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.
