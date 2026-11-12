# Future PyTorch → ONNX → Jetson contract

No PyTorch/ONNX runtime installation or export was performed. Registry metadata validates a declared contract, not graph correctness.

For each actual artifact record: task/model/dataset/experiment/hash, export tool/framework versions and **opset**, input/output names, dtypes and shapes, static versus dynamic axes, preprocessing, label order, threshold/abstention rule and output interpretation.

Proposed classifier boundary: batch1 float32 NCHW `[1,3,H,W]`, RGB converted from camera BGR, deterministic crop/resize (record stretch versus letterbox), normalization/scaling and mean/std **explicit per model**. Do not assume ImageNet normalization or softmax for every architecture. Identity outputs ordered OWNER_CAT/OTHER_CAT/OTHER_OBJECT; behavior EATING/DRINKING/OTHER; UNKNOWN is rejection/ambiguity unless a later recorded schema includes it. Specify logits versus probabilities, activation, shape and allowed finite values.

Detector output additionally records boxes, normalized/pixel coordinates, class IDs, confidence meaning, letterbox inverse transform and NMS. Future video/embedding candidates need a distinct temporal/embedding schema; current static registry contract does not pretend to support them.

Export acceptance: same held-out input bytes/preprocessing through PyTorch and ONNX, output shape/finite checks, agreed numerical tolerance, label decision/abstention equivalence, corrupt/unsupported graph rejection and report hashes. Dynamic shapes require explicit runtime/profile validation before use; initial registry is static. Do not load untrusted pickle checkpoints or infer a label map from filenames.
