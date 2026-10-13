# Power-tree finalization — ratings PENDING physical measurements

```text
Supply matched to exact Jetson board/revision ──→ Jetson

Reviewed ESP32 development power ──→ chosen USB port ──→ ESP32-S3

Adequate reviewed actuator rail ──┬──→ MG996R servo
                                 └──→ pump + MOSFET/flyback stage

Signal-reference/common ground: only where electrically required by the reviewed design
```

| Item | Exact part/rating measured | Evidence / reviewer |
| --- | --- | --- |
| Jetson board/revision and required input supply | PENDING | |
| Jetson + webcam operating/current transient | PENDING | |
| ESP32 USB/regulator/power-route/backfeed limits | PENDING | |
| Servo idle/motion/inrush/stall constraints | PENDING | |
| Pump starting/running/current/noise constraints | PENDING | |
| Actuator rail rating/wiring/connector/protection | PENDING | |
| MOSFET 3.3 V drive/flyback/thermal ratings | PENDING | |
| Logic/actuator return paths/common reference | PENDING | |
| Bulk/local decoupling and reset/brownout evidence | PENDING | |

Do not assume one weak 5 V source can support Jetson + servo + pump. Do not connect two independent 5 V rails/USB supplies blindly or run motor current through logic returns. Do not specify a final Jetson PSU rating until actual board/revision and documentation are confirmed. See `POWER_AND_ELECTRICAL_SAFETY.md` and `GPIO_VOLTAGE_PLAN.md`. All supplies, pins and connections remain unverified; no actuator rail is enabled by this worksheet.
