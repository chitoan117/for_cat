# Failure mode analysis — qualitative, no invented risk scores

| Failure | Effect | Detection | Existing mitigation | Future mitigation | Evidence needed |
| --- | --- | --- | --- | --- | --- |
| Camera offline | Missed visits | Read/failure status | Bounded service retries/dropout; no invented continuation | Actual backend watchdog/recovery | Unplug/replug log |
| Jetson crash | Observation/API unavailable | Service readiness/process state | MCU policy independent; actuator output disabled | Verified service recovery/network-loss rig | Actual crash/reboot tests |
| Serial loss | Unknown command outcome | CRC/IDs/timeouts/link state | Bounded pending/retries; ACK not SUCCESS | Durable MCU outcome/reconciliation | Physical disconnect during requests |
| ESP32 reset | Interrupted action/state uncertainty | Boot/reset trace | Safe boot/inspection latch/no automatic resume | Verified NVS/power-loss rig | Real reset/counter tests |
| RTC invalid | Daily/cooldown policy unreliable | OSF/BCD/calendar/health | Time-sensitive feed rejected | Actual clock/rollback/retention review | RTC fault and battery tests |
| HX711 failure | Invalid food weight/progress | Ready timeout/rail/invalid grams | Feed denied/stopped; grams absent | Load-cell drift/mechanical checks | Known masses/disconnect logs |
| Food sensor failure | Unknown availability | Echo timeout/range/geometry | Invalid availability denied | Calibrated mounting/range | Real empty/full/fault logs |
| Water sensor failure | Unsafe fill estimate | Health/range/staleness | Policy request OFF | Independent high-level/overflow safeguard as rig requires | Wet/empty/echo-loss tests |
| Servo jam | Gate may fail to close | No real closure detector yet | Timeout/no progress; PWM absent | Reviewed mechanics/closure/current/stop feedback | Jam/closure/electrical evidence |
| Pump stuck | Overfill despite software OFF | No actual output/flow feedback yet | Policy stop/time bounds; switching absent | Hardware fail-safe/feedback/containment | Stuck-switch/stop/leak tests |
| Power brownout | Reset/corrupt state/noise | Reset cause/voltage measurement | Write barriers/unknown-safe behavior | Rated separate supplies/protection | Real transients/current traces |
| Database full | Lost history/outcomes | SQLite error/readiness | Bounded retention/pending write; fail-safe ledger | Capacity/backup/deployment monitoring | Fill/failure/recovery evidence |
| AI misclassification | Incorrect recorded activity | Human comparison/confusion/UNKNOWN | Shadow/no auto-feed; ambiguity gates | Real held-out evaluation/threshold review | Annotated real sessions |
| OTHER_CAT false accept | Wrong subject authority | Explicit false-acceptance count/rate | No AI feed authorization at M2 | Independent real identity/multi-cat validation | Held-out other-cat study |
| Dataset leakage | Inflated evaluation | Session/source/exact/near checks | Versioned gates and rejection | Human near/crop-lineage review | Real corpus audit |
| Model/path tampering | Wrong/untrusted artifact | Schema/hash/containment | Inactive registry; no binary execution | Signed/approved artifact supply chain if deployed | Real model/runtime audit |

This table identifies mitigations and gaps, not a numerical risk ranking. Software cannot prove a physical stuck pump or jammed gate is safe. No physical actuator is enabled in the present candidate.
