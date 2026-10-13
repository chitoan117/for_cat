# Existing Web/App integration (design only)

Current architecture: USB webcam → Jetson Nano REST API → USB serial → ESP32 → sensors/actuators. Existing Flutter Web/App ↔ Jetson Nano `/api/v1/*`. The old project is not copied or modified here. Existing endpoints remain available; GET `/api/v1/feed/manual/{request_id}` is an additive poll route. POST `/api/v1/feed/manual` accepts an optional 1–64 character `Idempotency-Key` header; retrying with the same key returns a retained request, not another command. In real SERIAL mode this API refuses to send FEED_REQUEST until a separate approved hardware safety phase. HTTP 202 and serial ACK do **not** assert feeding success.

Deployment options to evaluate **later**, none implemented now:
1. Flutter Android app → Jetson over a trusted private LAN (discovery, auth and device permissions still needed).
2. Local HTTPS on Jetson with a trusted certificate, restricted local origins and access control.
3. VPN/private overlay network for authenticated clients.
4. Secure cloud relay designed for bounded commands and confirmed results.
5. Future MQTT over TLS with separate device identities and authoritative ESP32 outcomes.

The existing Cloudflare Pages Web site is HTTPS. Browser mixed-content, private-network, CORS and certificate restrictions may block calls to an HTTP-only private LAN Jetson; merely allowing CORS does not resolve those restrictions. `CORS_ORIGINS` defaults to empty and requires explicit origins; `*` is rejected. The Jetson is not exposed publicly by this project. LAN security (authentication, rate limiting, TLS and origin policy) is required before network deployment. No raw GPIO/servo/pump endpoint exists.
