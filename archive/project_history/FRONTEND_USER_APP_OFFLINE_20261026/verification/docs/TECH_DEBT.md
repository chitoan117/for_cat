# Technical debt — inspected, no aggressive cleanup

| Finding | Evidence / effect | Deferred cleanup boundary |
| --- | --- | --- |
| Legacy firmware contracts overlap | `hardware_interfaces.h` included by main; old SafetyController always denies, alongside newer policies/drivers/snapshot types | Consolidate only after actual integration/bench regression; retain gates now |
| Placeholder runtime | `FutureInferenceAdapter` definition has no production caller in app search; ExternalRuntimeAdapter requires a supplied executor | Implement real executor after real artifact/Jetson evidence, not fake predictions |
| Root ai versus app.ai | Research data/training plan and deployed runtime boundary have similar names | Keep map/import instructions; consider packaging later |
| Single-subject temporal pipeline | Current ObservationPipeline owns one active TemporalEngine; TrackLedger is future supplied-ID contract only | Multi-track engines/association require detector/tracker data and ROI evidence |
| New report metadata separate from persistence | FoodDefinition/FoodTrial carry confounders/attribution; existing FoodType/feeding DB do not store all of them automatically | Versioned schema/migration only when real experiment data requirements settle |
| Legacy dataset plan is not training acceptance | `training.prepare` is a plan; old report hashes first1000 and near-check first256 | Use full new release gates before training; eventually consolidate validators |
| Classification-only interoperability | Local sidecar round-trip; no YOLO/COCO bounding-box converter | Add format-specific lineage-aware adapter for an actual chosen task/export |
| Bounded near checks are heuristics | dHash can flag unrelated flat scenes/miss crops; candidate blocks incomplete/unresolved review | Human audit/lineage and justified larger-scale comparison after pilot |
| Fixed-FPS replay capture | Media offsets from index/reported FPS, no variable-frame-rate timeline parser | For VFR sources use a validated timestamp-aware decoder; current tool unsuitable for precise VFR event alignment |
| Trusted-local single-writer tools | New output/session creation checks and staging do not implement multi-operator distributed locks | Avoid concurrent writes; coordinate/version artifacts if collaboration needs arise |
| Event matching greedy | Highest-overlap one-to-one matching, not globally optimal assignment | Document algorithm; upgrade only if real split/merge cases justify it |
| Supplied metadata is not independent validation | Registry checks hash/shape declarations, not binary inference; report VALIDATED_SENSOR is caller provenance | Real graph/runtime/measurement review and explicit promotion gates |
| Future actuator/telemetry paths absent | PWM/switching prohibited; binary v1 sensor telemetry extension design only | Actual physical evidence and negotiated protocol changes first |
| Duplicate test/simulation worlds | Python twin and native policies, fake models/ports/weight fixtures | Keep parity regression; never deploy fixtures as calibrated data |
| Dependency/security/platform gap | Full host snapshot exists, target wheels/runtime unverified, no CVE scan in this pass | Audit target/upgrades; do not treat pip consistency as vulnerability certification |

No stable safety/protocol/frontend code was removed. The new preparation tools are meaningful foundations; they do not close these real integration/validation gaps.
