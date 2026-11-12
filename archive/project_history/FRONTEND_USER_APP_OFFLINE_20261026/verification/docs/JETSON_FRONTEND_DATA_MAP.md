# Jetson API → existing frontend data map (frontend untouched)

| Existing concept | Current fields/routes | Exact gaps |
| --- | --- | --- |
| Dashboard | `/daily-summary`: feeding requests/success count, drinking count, eating/drinking times/durations, reliable consumed grams or null; `/preferences` experimental evidence | no real sessions/weights/model results; no actual old-client schema test |
| Manual feed | POST `/feed/manual` empty body + Idempotency-Key; poll `/status` for refresh and GET `/feed/manual/{id}` for retained state | physical SERIAL request blocked; no quantity body; ACK/202 not SUCCESS |
| Events/history | `/events`, `/behavior`, `/feeding-history`, `/drinking-history`; typed `/sessions/*` | typed projections are Event-shaped; client must tolerate EATING observations as distinct from FEED success; real observations absent |
| System status | `/status` component/AI/link/service/readiness snapshots; `/health` process liveness; `/readiness` passive cached usability | no real sensor telemetry, GPU validation, actual board/serial outcome or authenticated deployed client |
| Settings | trusted local environment/config (camera, paths, ROIs, thresholds, explicit origins) | no REST settings mutation endpoint or old frontend settings compatibility proved |

Do not build a new frontend or modify the old project. Client network/TLS constraints and authentication remain documented future work. A MOCK or unvalidated component must not be displayed as a physical healthy sensor or trained AI.
