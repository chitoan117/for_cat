# Dataset acceptance gates

Executable checks: `ai/releases.py`; CLI `python -m ai.scripts.dataset_release validate --dataset PATH --task identity --stage PILOT_DATASET`.

| Status | Meaning |
| --- | --- |
| PILOT_DATASET | Integrity/leakage checks pass; coverage/diversity issues reported; useful for pipeline exploration, not accuracy claims |
| TRAINING_CANDIDATE | Full bounded integrity, splits/class/session checks pass, coverage/diversity/near-duplicate concerns resolved |
| TEST_CANDIDATE | Same data checks for a reserved evaluation candidate; never used to train/select thresholds |
| REJECTED | Corruption, bad paths/hashes/metadata, leakage, insufficient candidate coverage or outstanding checks |

Empty repository data reports DATASET_NOT_AVAILABLE, not PILOT. Full validation checks up to10000 samples; exceeding budget rejects rather than certifying unchecked files. Near comparison is configurable/bounded (default256, up to1000), and incomplete checking is reported. dHash neighbors are **review warnings**, not proof of duplication. Candidate gates conservatively block unresolved warnings. Review/remove suspect data or rerun within the supported coverage budget; do not silently waive warnings.

Required: decodable samples and matching file hashes; no session, source-video hash or exact-image hash crossing splits; task-specific known class coverage in train/validation/test; multiple usable sessions; diversity in recorded lighting/view angle; imbalance and usable-rate reports. Default identity coverage is OWNER_CAT/OTHER_CAT/OTHER_OBJECT; behavior EATING/DRINKING/OTHER. Pilot missing OTHER_CAT is reported rather than fabricating samples. Required class subset/minimum-session policy is explicit in the report; two sessions means only “multiple”, not a statistically sufficient corpus.

No fixed scientific sample-size, balance, precision or accuracy threshold is asserted. Define acceptance requirements with the supervisor and real pilot evidence. Counts/imbalance/diversity are diagnostics; pilot success is not validated classifier performance. Keep sessions/source videos grouped together when preparing splits. Final test sessions are frozen and isolated before model/threshold selection.
