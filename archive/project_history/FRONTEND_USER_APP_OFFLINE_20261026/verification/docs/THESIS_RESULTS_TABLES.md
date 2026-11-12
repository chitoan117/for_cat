# Blank thesis results tables — NOT EXECUTED

All `—` cells are absent results, never zero. Status stays **[CHỜ KẾT QUẢ THỰC NGHIỆM]** until actual evidence and predeclared acceptance criteria exist. Record units, date, device/source/config/hash, conditions, reference/uncertainty, trial count, all failures and log paths. Host fixture values do not belong here.

## HX711 calibration
| Trial | Reference mass g | Tare/raw average counts | Factor g/count | Measured g | Absolute error g | Relative error % | Repeatability/environment | PASS/FAIL/evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — | [CHỜ KẾT QUẢ THỰC NGHIỆM] |

## Food/water ultrasonic error
| Sensor/geometry/trial | Reference cm | Raw cm | Filtered cm | Absolute error cm | Relative error % | Full/empty calibration | Echo fault/conditions | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — | — |

## Camera FPS on actual Jetson
| Camera/Jetson/backend/hash | Resolution | Duration s | Frames read | Read failures/dropouts | Measured capture FPS | Environment/power | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

## Physical serial RTT
| Board/USB route/image hash | Command | Trials | RTT mean/median ms | RTT p95/max ms | CRC/ID/timeouts | Unplug/replug recovery | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

## Identity confusion matrix (actual rows, predicted columns)
| Actual | OWNER_CAT | OTHER_CAT | OTHER_OBJECT | UNKNOWN | Support |
| --- | --- | --- | --- | --- | --- |
| OWNER_CAT | — | — | — | — | — |
| OTHER_CAT | — | — | — | — | — |
| OTHER_OBJECT | — | — | — | — | — |

## OTHER_CAT false acceptance / owner false rejection
| Model/dataset/split/threshold | Actual OTHER count | OTHER→OWNER count/rate | Actual OWNER count | OWNER→OTHER count/rate | UNKNOWN rate | Coverage/conditions | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

## Behavior confusion matrix (actual rows, predicted columns)
| Actual | EATING | DRINKING | OTHER | UNKNOWN | Support |
| --- | --- | --- | --- | --- | --- |
| EATING | — | — | — | — | — |
| DRINKING | — | — | — | — | — |
| OTHER | — | — | — | — | — |

## Event-level behavior
| Model/temporal config/source | Start/end tolerance s; overlap policy | True/predicted events | Matches | False/missed | Precision/recall/F1 | Boundary errors/overlap | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

## Feeding accuracy — no animal in initial rig
| Trial/firmware/calibration | Requested target g | Independently weighed dispense g | Absolute/relative error | Closure/time/current | Fault/limit outcome | PASS/FAIL | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

## Food consumption estimate error
| Session/subject/food | Independent reference consumed g | Validated before/after g | Estimated g | Absolute/relative error | Added food/confounders/uncertainty | Excluded? | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

## Water control
| Trial/level calibration | Low/high/state trajectory | Actual pump start/stop | Runtime/current/progress | Sensor/no-progress/max-time fault | Spill/dry-run/stop result | PASS/FAIL | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

## Power/reset
| Device/rail/test | Supply/current/transient measurements | Reset cause | Persistence/recovery | Actual safe output state | Uncertain request/inspection | PASS/FAIL | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — |

At reference0, relative error is N/A; record absolute residual instead. Record valid trial denominators and unknown/exclusions; do not cherry-pick. Capture FPS is separate from inference throughput; CRC is not authentication; output command is not physical feedback. No water-volume estimate without independent measuring hardware.
