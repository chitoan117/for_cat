# AI task architecture — current sensor-fusion direction 2026-10-21

Production: USBcamera -> C++14/OpenCV/CUDA/TensorRT FP16 YOLOv8n -> CAT/DOG/NONE.
One black cat; no required OWNER classifier. Preserve `cat_dog_trt.cpp` and engine.

Next: reuse standalone C++single-cat IoU/centroid tracker/ROI/session foundations,
bridge fresh species+near evidence to calibrated load-cell filtering and rule FSM.
CAT nearfood + sustained significant negative trend -> EATING_START; departure
+ stable final weight -> EATING_END / consumedgrams. Noise/near alone is insufficient.
APPROACHING/NEAR_FOOD/LEAVING are rule/geometry states, not extra NN classes.
Missing/invalid/discontinuous/refill/tare/calibration/contact evidence cannot produce
clean consumption. **A newly trained EATING NN is not the next prerequisite.**
DRINKING remains observation-only; food scale cannot establish water consumption.
Pump uses operational water sensing, independent of a DRINKING classifier.

Feed request is separate: fresh CAT+stable calibrated approachdistance+safety ->
one arbiter -> ESP32 final safety; DOG/NONE never feed. Default output0/shadowtrue.
Actual C++tracker-to-camera/scale/eventstore integration remains TODO, not enabled
by documenting it. Existing Python identity/FSM/storage contracts are legacy
host-tested foundations; adapt single-cat semantics explicitly, never fakeOWNER_CAT.

Windows pilot:165assistant-reviewed images, real CPU frozen-backbone/head trial,
test13/52(25%), no EATING in test. Not a production behavior model and not deployed.
Retain as exploratory evidence, no need to train another NN to start scale fusion.
See `CURRENT_PROJECT_STATE.md` and `ROADMAP.md` for evidence and acceptance gates.

## Legacy/future identity-model architecture (not current requirement)

**Historical/future identity architecture below.** Current implementation has a
validated C++ latest-frame COCO CAT/DOG runtime and single-cat Behavior V2 dataset
tools. V2 labels are EATING/DRINKING/IDLE, with no required owner classifier.
No V2 behavior model is trained or integrated. A separate C++14 shadow
tracker/ROI/time-based FSM/event library is now implemented and offline-tested
on Nano, documented in `CPP_BEHAVIOR_SHADOW.md`. It does not replace the legacy
Python identity/storage contracts or alter the production detector.
See `CURRENT_PROJECT_STATE.md`, `JETSON_CAMERA_LATENCY_RESULT.md` and
`SINGLE_CAT_BEHAVIOR_V2.md` for current facts.

```mermaid
flowchart TD
  F[Frame] --> D[Cat detector]
  D --> C[Crop / caller-supplied track ID]
  C --> I[Identity: OWNER / OTHER / UNKNOWN]
  C --> B[Behavior: EATING / DRINKING / OTHER]
  I --> T[Temporal engine]
  B --> T
  T --> S[Session fusion]
  S --> W[Validated sensor fusion]
  W --> DB[Database / REST history]
```

OTHER_OBJECT is a negative identity-training class; no detection/ambiguous input may yield UNKNOWN/NO_SUBJECT at runtime. Crop geometry, channel conversion and confidence rejection must be explicit. Separate detector, identity and behavior components allow different data, evaluation, budgets and deployment choices; one giant model is not required.

Implemented boundaries: `app/vision/detector.py`, `tracking.py`, `app/ai/{interfaces,runtime,pipeline,service}.py`, `behavior/{temporal,fusion}.py`. The detector adapter is injected, not bundled; current temporal engine has one active session, not multi-track engines. TrackLedger preserves supplied IDs/first_seen/last_seen with TTL/budgets; it does not associate detections or perform Re-ID. Future integration requires one temporal state per subject track and reviewed ROI assignment.

Attribution: OWNER only may produce clean owner evidence; OTHER only is observed without owner authority; OWNER+OTHER, multiple OTHER, unknown identity or overlap are AMBIGUOUS by default. Existing detector adapter rejects multiple detections. Ambiguous sessions cannot become clean preference trials. No AI path authorizes feeding in this candidate; shadow mode remains true.

Candidate configs: `ai/registry/candidates.json` (YOLO-light/SSD-MobileNet, ResNet18/MobileNetV3/Re-ID option, frame/temporal/video options). Input sizes/complexities are conceptual configurations, not measurements. No models were downloaded; no Jetson FPS exists.
