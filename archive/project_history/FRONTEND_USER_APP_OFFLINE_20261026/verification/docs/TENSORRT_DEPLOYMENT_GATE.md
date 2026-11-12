# TensorRT deployment gate — NOT JETSON VALIDATED

ONNX supplied → actual Jetson OS/JetPack/CUDA/TensorRT/environment check → conversion on that device/toolchain → correctness comparison with reference outputs → sustained runtime/performance/memory measurement → passive shadow run.

Record Jetson model/power mode/temperature, exact versions, ONNX opset/hash, engine device/version/precision/profile, preprocessing and labels; conversion errors, numerical differences, UNKNOWN/false-acceptance effects, latency distributions and failure/dropout rates. Agree tolerances/budgets before acceptance. Engines are device/toolchain-specific; a PC file is not a Nano compatibility result.

FP16/INT8 require separate correctness evidence; INT8 needs representative real calibration data kept distinct from test data. No engine was generated, no FPS measured, and no entry is VALIDATED_JETSON. Compatible runtimes, conversion, real data and explicit shadow validation are still required.
