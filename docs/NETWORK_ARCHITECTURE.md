# Network architecture

Existing Flutter/Web ↔ reviewed local REST endpoint on Jetson. Jetson ↔ ESP32-S3 over direct USB serial, not Internet commands. Sensor/actuator safety remains local to ESP32 even when network/Jetson fails.

Default API host is127.0.0.1; CORS is empty unless explicit allowed origins are configured. No public endpoint, port forwarding, authentication deployment or TLS setup is created here. CORS is browser policy, not authentication. SERIAL feed requests remain locally rejected at M2.

Future remote access choices require separate deployment work: private VPN, authenticated TLS reverse proxy or an explicitly designed relay. Do not expose an unauthenticated device directly. Hosted HTTPS frontend to private HTTP Jetson needs mixed-content/private-network/CORS review; an API contract alone does not prove old frontend compatibility. Local observation/model/capture tools are operator CLIs, not upload endpoints.
