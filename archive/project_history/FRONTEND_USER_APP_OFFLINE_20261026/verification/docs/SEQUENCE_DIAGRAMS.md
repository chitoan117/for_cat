# Sequence diagrams — current software and future gated actions

## Manual Feed (current safe behavior)
```mermaid
sequenceDiagram
  participant U as Web/App caller
  participant J as Jetson API / ledger
  participant E as ESP32 authority
  U->>J: Manual intent + idempotency key
  J->>J: Validate / persist request
  alt SERIAL mode M2
    J-->>U: REJECTED locally (no physical feed frame)
  else Mock/simulation
    J->>E: Synthetic FEED_REQUEST
    E-->>J: ACK receipt only
    J-->>U: PENDING
    E-->>J: Synthetic final result
    J->>J: Persist outcome/history
  end
```

## Automatic Feed candidate (future only)
```mermaid
sequenceDiagram
  participant C as Camera/AI
  participant J as Jetson
  participant E as ESP32
  participant A as Actuator rig
  C->>J: Track/identity/behavior evidence
  J->>J: UNKNOWN/multi-cat/threshold review
  Note over J,E: M2 shadow: no automatic authorization
  opt Future validated explicit mode
    J->>E: Negotiated feed intent
    E->>E: RTC/weight/food/limits/persistence/interlocks
    E->>A: Reviewed bounded output only if all gates pass
    A-->>E: Actual feedback
    E-->>J: Verified final outcome
  end
```

## Eating observation
```mermaid
sequenceDiagram
  participant C as Frame/crop/track
  participant T as Temporal engine
  participant F as Session/sensor fusion
  participant D as Database/API
  C->>T: Supplied identity/EATING/ROI/confidence/time
  T->>T: Confirm positives / bound dropout
  T->>F: START then END at last positive evidence
  F->>F: Associate subject/feed; validated stable weights or null
  F->>D: Typed visit/history, no feeding action
```

## Drinking observation
```mermaid
sequenceDiagram
  participant C as Frame/track
  participant T as Temporal engine
  participant D as Database/report
  C->>T: Supplied DRINKING/water ROI evidence
  T->>T: Confirm / reject ambiguity / end on dropout
  T->>D: Drinking start/end/duration
  Note over D: Volume unknown; no diagnosis
```

## Serial loss
```mermaid
sequenceDiagram
  participant J as Jetson link manager
  participant E as ESP32
  J-xE: USB loss / timeout
  J->>J: OFFLINE, bounded retry, retain uncertain request
  E->>E: Independent safe policy/default disabled outputs
  J->>E: Explicit reconnect/status reconciliation
  Note over J,E: Real outcome/reboot reconciliation still needs physical validation
```

## ESP32 reboot
```mermaid
sequenceDiagram
  participant E as ESP32
  participant N as Separate safety/calibration storage
  E->>E: Safe boot, output gates disabled
  E->>N: Load safety state / sensor calibration separately
  N-->>E: Valid record or missing/invalid
  E->>E: Inspection latch / NOT_CALIBRATED / no action resume
```

## Jetson reboot
```mermaid
sequenceDiagram
  participant J as Jetson service
  participant D as SQLite ledger/history
  participant E as ESP32 link
  J->>D: Restore persisted request/session state
  J->>J: Default MOCK/shadow; observation worker not auto-started
  opt Explicit future serial configuration
    J->>E: Passive bounded status/reconciliation
  end
  Note over J,E: No blind resend of uncertain feeding; no model auto-activation
```
