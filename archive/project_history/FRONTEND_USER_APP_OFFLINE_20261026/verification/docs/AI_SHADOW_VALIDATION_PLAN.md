# Shadow validation plan

AI_SHADOW_MODE=true remains default; ObservationPipeline never authorizes feeding even if configured false. Future model insertion is metadata registration, not activation. No model/runtime was inserted or trained here.

Future sequence: reviewed real dataset/splits → recorded experiment/artifact → independent host output-contract comparison → actual Jetson runtime/budget validation → explicit passive observation run → human annotation comparison. Keep sensors/actuator permission independent from predictions.

Log: UTC/monotonic/media time, source session and track, model/artifact/dataset/config hashes, preprocessing/ROI, proposed identity/behavior/confidence, abstention/ambiguity, temporal start/end, dropped frames and storage/runtime failures. Do not log a commanded action as a sensor observation. Human ground truth remains separate from prediction logs.

Use `evaluate_run shadow` for supplied frame comparisons and `evaluate_run events` for temporal matches. Report confusion, OTHER_CAT false acceptance, owner false rejection, UNKNOWN rate, event errors and lighting/viewpoint/occlusion/multi-cat slices. Review candidate thresholds on validation sessions, freeze them before final test. New real evidence—not a host fixture—determines future deployment readiness. No actuation or public API exposure is needed for this evaluation.
