# Report figures plan

Existing Mermaid/text figures are design evidence, not physical photographs/results. No pending figure is claimed captured. Export a design diagram with caption “design at M2”; label mock screenshots unmistakably. Actual result captions need version/hash/date/conditions and evidence path.

| Figure | Existing source / status | Required later evidence |
| --- | --- | --- |
| System block diagram | `SYSTEM_BLOCK_DIAGRAM.md` / `REFERENCE_ARCHITECTURE.md`, exists | As-built diagram after hardware verification |
| Jetson photo | NOT CAPTURED | Actual revision/carrier/storage/power/mount |
| ESP32-S3 photo | NOT CAPTURED | Module markings, board/ports/header identity |
| Webcam mounting | NOT CAPTURED | Actual camera, bowl positions, field-of-view |
| Sensor wiring | Candidate table/design only | Verified pins/rails/conditioning/wiring photo |
| Feeder mechanism | NOT CAPTURED | Actual gate/servo closure/jam-safe rig |
| Water mechanism | NOT CAPTURED | Actual tubing/pump/driver/containment |
| API/software architecture | `SOFTWARE_ARCHITECTURE.md`, `SEQUENCE_DIAGRAMS.md`, exists | Actual deployed routing/client evidence |
| UART frame | `UART_PROTOCOL.md` + shared vectors, exists | Real correlated USB trace/RTT/CRC/recovery |
| Camera result | Generated fixtures only, not final image | Real Jetson camera frame with conditions/privacy review |
| AI detection/identity result | NOT AVAILABLE | Real artifact outputs and held-out annotations |
| Feeding graph | NOT AVAILABLE | Synchronized real mass/command/feedback/outcome |
| Drinking history | Format/replay design only | Actual confirmed drinking events/time evidence |
| Web/App screenshots | Existing frontend outside repo; not verified | Actual client/API integration; label mock screens if used |

Synthetic overhead benchmark plots cannot be captioned Nano FPS; simulator SUCCESS cannot be captioned physical feeding. Obtain/share only necessary consented/private-safe images; do not put raw cat video, secrets or generated private evidence into the source handoff.
