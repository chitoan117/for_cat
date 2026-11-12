# Implementation roadmap — owner decision 2026-10-21

Current source/evidence: `CURRENT_PROJECT_STATE.md`. Wiring/staged commands:
`ESP32_S3_SENSOR_STATION.md`. Earlier M2 freeze/RC/Phase docs are historical;
they do not override this authorized incremental hardware roadmap.

## Phase 1 — current physical integration (first priority)

- [x] Preserve physically working owner-confirmed C++ CAT/DOG/NONE detector.
- [x] Declare approved GPIO4..18 roles; retire conflicting old6/7/10/11/12/13 roles.
- [x] Keep runtime servo/pump outputs disabled; inventory #2 GPIOs remain TBD.
- [ ] **First physical task:** HX711 tare/known-mass calibration/add-remove repeats
  with food bowl on isolated load-cell support, actuator power disconnected.
- [ ] Supervised servo mechanics/closed-position testing: explicit guarded BENCH
  MODE defaultOFF, manual arm, short expiry, bounded pulse/runtime, local stop,
  close-on-fault/reboot, no automatic re-arm. Current firmware has no such driver.
- [ ] Pulse-close-settle closed-loop **added delta**≈40g. Stable baseline, maximum
  pulses/time/grams, no-progress/stale-scale handling, closure evidence, durable
  daily/session limits and uncertain-reset lockout. Existing portable controller
  is desired-state simulation logic, not a physically complete pulse controller.
- [ ] HC-SR04 #1 physical voltage/range/near threshold/stable-time calibration;
  fresh CAT+near gating. Reject DOG/NONE/ambiguous/stale/distance-invalid requests.
- [ ] Operational-water placement/blind-zone/full-empty/LOW-TARGET validation.
  F5305S polarity, safeOFF/boot behavior, limited pump test, cooldown/timeout/
  dry-run protection. DRINKING has no control path to pump.
- [ ] Unified arbiter skeleton with durable request IDs/source/session and one
  active operation, shared cooldown/dailymax; do not expose three actuator paths.

**Acceptance:** actual serial/weight/closure/distance logs and supervised evidence;
host/compile PASS alone cannot authorize unattended operation.40g tolerance is a
physical result, not a current promise. If the cat eats/touches the bowl during
dispensing, net scale change is not necessarily dispensed mass: stop/flag the
measurement rather than keep dispensing to compensate for unobserved consumption.

## Phase 2 — tracking, sensor fusion, eating sessions

- [ ] Reuse existing C++14 `SingleCatTracker`/ROI/monotonic FSM foundation; no need
  to add SORT/ByteTrack dependencies for one cat before measuring a need.
- [ ] Bridge fresh timestamped species/track/near evidence and calibrated weight;
  preserve sensor sequence/boot epoch/calibration identity, flag clock mismatch.
- [ ] Filter/bounded weight window; stable detection; significant negative trend
  sustained for a calibrated duration; entry/exit hysteresis. Exclude dispense,
  refill, tare/recalibration, bowl removal/contact, ambiguous/spill observations.
- [ ] IDLE -> APPROACHING -> NEAR_FOOD -> EATING -> LEAVING -> IDLE. Geometry
  states are rules, not mandatory NN classes. CAT+near without trend is not eating.
- [ ] START/END paired events; END on departure plus stable valid post-weight;
  timeout missing post-weight as incomplete/null. Consumed=pre-eating minus stable
  post-eating, not pre-dispense minus post-eating. No weight/no calibration -> null.
- [ ] Visit/return/session logging; single-cat storage adapter without inventing
  OWNER_CAT identity. Preserve legacy record consumers with versioned migrations.

**Acceptance:** noise-only sequences never EATING; sustained decrease can confirm;
added-food/calibration/epoch changes cannot create clean consumption. Physical
video+scale replay checks follow software fixtures; no newly trained EATING NN gate.

## Phase 3 — inventory, telemetry, alerts

- [ ] Audit/owner approval of HC-SR04 #2 and JSN-SR04T #2 GPIO candidates before
  wiring or assigning them in code. All current inventory TRIG/ECHO are TBD.
- [ ] Food hopper and water reservoir independent FULL/EMPTY calibration and valid
  measurement range/blind zone; height-based percent explicitly labeled. Hopper
  geometry may require a measured curve for volume/mass, not linear assumption.
- [ ] Extend interleaved ultrasonic scheduling from2 to4 channels without crosstalk,
  ensure no blocking IO during edge capture, validate timeout/recovery on actualrig.
- [ ] Versioned ESP32 telemetry -> C++ receiver/control bridge -> SQLite/API; keep
  old UARTv1 wire contract unchanged until an explicit extension is implemented
  and tested at both ends. ASCII diagnostics currently log JSONL, not DB ingest.
- [ ] FOOD_RESERVOIR_LOW / WATER_RESERVOIR_LOW with persistence/hysteresis/stale
  validity and refill acknowledgement; show null/uncalibrated instead of fakepercent.

## Phase 4 — one Web/control plane and meal scheduling

- [ ] Reuse existing REST/history/SQLite/idempotency contracts. Audit Nano runtime
  deployment compatibility; existing FastAPI source requiresPython>=3.10 versus
  Nano system3.6. Do not switch C++ AI to Python or blindly upgrade targetPython.
- [ ] **One backend, one database, one API, one responsive Web:** `/kiosk` simple
  touchscreen view; `/app` phone/admin dashboard/settings/history/inventory/alerts.
  Neither route/UI is implemented by this documentation/pin update.
- [ ] Kiosk: species, grams, food inventory, water operational/reservoir state,
  nextmeal, servo/pump state, camera/ESP32health, bounded Feed Now.
- [ ] One-time/daily/weekday schedules with enable/disable and bounded targetgrams;
  durable due-instance ID, timezone/daylight/manual-RTC-change policy, missed-meal
  policy, no catch-up bursts. Source=AUTO/SCHEDULE/MANUAL feeds one arbiter.
- [ ] Internet loss: localhost/kiosk continues. Jetson unavailable is different:
  revisioned necessary schedule/state sync to ESP32+validatedDS1302, ownership/
  acknowledgement/expiry and reboot reconciliation prevent double feeding.
- [ ] Chromium fullscreen may open `http://localhost:<configured-port>/kiosk`
  only after the route/service exists. Remote Internet access remains later;
  do not expose raw Jetson port publicly.

## Phase 5 — analytics (no new deep-learning model needed)

- [ ] Multi-trial preference: trial_id, food_variant, actual dispensed/consumed,
  ratio, approach_latency, eating_duration, return_visits, refusal. Match comparable
  conditions, require minimum clean sessions, show evidence/uncertainty. Existing
  OWNER-only scoring is legacy research, not current single-cat measured result.
- [ ] Correct ratio attribution for food already in bowl/added during a visit;
  never infer preference from one fixed40g threshold or equate long dwell with liking.
- [ ] Inventory history/valid daily usage; estimated days food/water remaining only
  after adequate history and calibrated quantity conversion. Percent alone is not
  grams/day or liters/day. Null for insufficient history; handle refills separately.

## Phase 6 — optional later

- [ ] Baseline grams/day, visits and durations; report unusual feeding patterns,
  never diagnosis. OWNER_CAT/OTHER_CAT and multi-animal attribution remain future.

## Evidence and execution rules

`ACTUATOR_OUTPUTS_ENABLED=0`, `AI_SHADOW_MODE=true`, automatic authorizationfalse
remain current. This pass updates canonical state/map and safe sensor subset;
it does not implement all unchecked items. Guarded bench additions require their
own tests/explicit arm; no unbounded command. Keep historical V2 evidence/handoffs,
original videos, production source/engine/binary and remote dirty work intact.
