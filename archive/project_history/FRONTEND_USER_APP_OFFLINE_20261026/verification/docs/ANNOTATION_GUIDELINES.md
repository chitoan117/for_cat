# Annotation guideline — label schema v1

Annotate visible evidence, not the capture-session target or a model guess. Preserve session_id, source hash and media offset. Inspect adjacent frames for temporal context; do not move those frames between splits. UNKNOWN/UNSURE/SKIP are valid review outcomes, excluded from clean classifier targets. Record disagreement and review decisions.

## Identity

| Label | Evidence |
| --- | --- |
| OWNER_CAT | Known project subject, visually identifiable from distinguishing features; corroborating adjacent frames allowed |
| OTHER_CAT | Cat clearly identifiable as not the owner; not merely low confidence in OWNER_CAT |
| OTHER_OBJECT | Visible non-cat subject/object/person; for negatives, not a default for a hidden cat |
| UNKNOWN | Cat/subject exists but identity cannot be assigned confidently; partial crop, blur or indistinguishable features |
| SKIP | Corrupt/irrelevant frame, mixed subjects without separable annotation, privacy-sensitive material or unusable framing |

For two cats, do not give a whole frame one clean identity. Future detection/crop annotation must attribute a subject track; current classification capture should mark UNKNOWN/SKIP and retain ambiguity notes. A hidden face is not automatically OTHER_CAT.

## Behavior

| Label | Evidence |
| --- | --- |
| EATING | Visible food-taking/chewing sequence consistent with the food bowl; proximity alone is insufficient |
| DRINKING | Visible lapping/drinking sequence at water bowl, including adjacent-frame confirmation when appropriate |
| NEAR_FOOD | Approaching/inspecting food area without positive eating evidence |
| NEAR_WATER | Approaching/inspecting water area without positive drinking evidence |
| LEAVING | Moving away from a previously occupied interaction region; record context |
| OTHER | Clear non-eating/non-drinking behavior; not a catch-all for insufficient evidence |
| UNSURE | Insufficient/contradictory evidence, hidden mouth, blur or ambiguous overlap |
| SKIP | Unusable/corrupt/irrelevant frame or scene that cannot be cleanly attributed |

## Difficult cases

- Head near bowl but no food-taking: NEAR_FOOD, not EATING.
- Passing behind bowl: OTHER or LEAVING with context, not eating/drinking.
- Drinking with face hidden: DRINKING only if visible temporal evidence supports it; otherwise UNSURE.
- Two cats/overlap: preserve track-specific annotation when possible; otherwise UNKNOWN/UNSURE/SKIP, never clean preference data.
- Person handling food: OTHER_OBJECT / OTHER; note disturbance, exclude affected weight/preference interval.
- Empty bowl: label the visible action, not inferred hunger. Inspecting empty food bowl is NEAR_FOOD; do not infer consumption.
- Partial occlusion: assign identity/behavior independently. Identity may be known while behavior is UNSURE, or vice versa.

Annotate event start/end at first/last positively supported media times; do not extend eating over an unobserved gap. Review sample ambiguity, source quality, label consistency and held-out-session membership before release. Dataset version/schema must change when label semantics change.
