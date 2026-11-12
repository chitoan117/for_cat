# Future real AI insertion checklist — AI NOT TRAINED

1. Collect real supervised recordings with anonymous session metadata and actual camera conditions.
2. Label and validate corruption/duplicates; split by recording session, review cross-session near-duplicates.
3. Train only train sessions; early-stop on validation, reserve test sessions for final evaluation.
4. Evaluate identity and behavior per class/events; explicitly report **OTHER_CAT→OWNER_CAT count/rate**, EATING↔DRINKING confusion, uncertain/occluded/multiple-cat cases.
5. Select detector/identity/behavior thresholds from genuine validation evidence (blank defaults are NOT_CONFIGURED, not calibrated science).
6. Export with label map/preprocessing/crop coordinates/version/checksum and trusted local file path; never accept arbitrary REST model paths.
7. Host replay through the runtime-independent boundary, ROI/temporal/fusion/history and failure tests.
8. Audit exact Nano/JetPack/CUDA/TensorRT/ONNX compatibility; test real Jetson inference and memory/latency.
9. Benchmark under sustained physical camera/load conditions; record drops, uncertainty and power/thermal behavior.
10. Run **SHADOW MODE FIRST**: observations/history only, no feeding. Compare against human ground truth and controlled sensor evidence.
11. Only after validated results, separately review explicit automatic feeding policy integration and ESP32 safety. No identity-only actuation.

No trained model, runtime installation, real prediction metric, threshold calibration or deployment pass is claimed here. `ai/evaluation.py` computes false-acceptance from supplied predictions only; numeric synthetic test outputs are never model accuracy evidence.
