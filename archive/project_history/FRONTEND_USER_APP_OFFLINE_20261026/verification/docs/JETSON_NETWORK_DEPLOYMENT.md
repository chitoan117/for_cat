# Prototype network modes — no public exposure performed

- Default: loopback `127.0.0.1`, empty CORS origins, no camera/serial/GPU auto-start. Useful for local tests only.
- Later trusted LAN: explicit host binding and client/origin allow-list after physical validation, firewall and device access review. Prototype authentication is **not implemented**; do not expose this interface publicly or on an untrusted LAN.
- Android on LAN: confirm actual app schema/device permissions/discovery and authoritative result polling; CORS is a browser concept, not a substitute for authentication.
- Hosted HTTPS browser: private HTTP Jetson may be blocked by mixed content/private-network/CORS restrictions. Future local TLS/reverse proxy, private VPN/overlay or an authenticated relay needs separate design. Explicit CORS origins only; no wildcard production default.

No TLS certificate, reverse proxy, cloud deployment, MQTT replacement or public API was installed. No raw GPIO/servo/pump endpoint exists. Unknown/camera/AI failure cannot authorize automatic physical action.
