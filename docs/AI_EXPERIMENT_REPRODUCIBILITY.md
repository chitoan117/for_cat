# Reproducible experiment preparation and supplied result archive

Schema: `ai/experiments.py::Experiment`; illustrative nonproduction config: `ai/experiments/example.json`. Fields: experiment_id, dataset_version, task, architecture candidate ID, seed, input_size, epochs, batch_size, optimizer, learning_rate, augmentation, early_stopping, class_weights and thresholds. Example hyperparameters are plumbing examples, not selected recommendations.

```text
python -m ai.scripts.experiment_tool candidates
python -m ai.scripts.experiment_tool prepare --config ACTUAL_CONFIG.json --release ACTUAL_RELEASE.json --output RUNS_FOLDER
# --apply saves experiment.json, no training.
python -m ai.scripts.experiment_tool archive --config PREPARED_EXPERIMENT.json --metrics SUPPLIED_METRICS.json --evaluation SUPPLIED_EVALUATION.json --artifact-root TRUSTED_ROOT --artifact-name MODEL.onnx --output NEW_RESULT.json
# --apply archives supplied results/hash; no inference/training/activation.
```

Bundle preserves config, versioned dataset release/hash, Git revision/dirty state if available, a source-tree hash when no Git exists, Python/platform/packages, label map, thresholds and explicitly null metrics/artifact hash/evaluation while untrained. Source digest covers Python/firmware/check scripts; config/dataset metadata are stored separately. Source control unavailable here; no Git revision is invented.

Future actual runs must additionally record framework/CUDA/cuDNN versions, determinism settings, split/sample hashes, seeds, augmentations, preprocessing, checkpoint selection, hardware and elapsed times. Archive supplied metrics/evaluation and artifact SHA256 afterward. Tool archive status is SUPPLIED_EXPERIMENT_RESULT_UNVERIFIED/EXPERIMENTAL; it cannot certify how training occurred. Final test candidate is rejected as a training source. Threshold sweeps/early stopping use validation data only.

## Model registry

ModelEntry stores model_id/task/dataset_version/training_experiment, trusted relative file/hash, runtime, static NCHW input shape, exact label map, thresholds and validation status. Registry statuses: EXPERIMENTAL, VALIDATED_HOST, VALIDATED_JETSON, REJECTED. Initial registration allows only EXPERIMENTAL/REJECTED; independent validation evidence and a later explicit promotion workflow are required for validated states. Nothing is VALIDATED_JETSON.

```text
python -m ai.scripts.experiment_tool register --config ACTUAL_MODEL_METADATA.json --artifact-root TRUSTED_MODEL_ROOT --expected-task identity --output LOCAL_REGISTRY
# Dry-run by default; --apply registers inactive metadata. Does not load a binary.
```

Checks metadata, exact task/label map, file/type/existence, relative/symlink containment and SHA256; refuses overwrite. Hash matching is not ONNX correctness. Model activation requires separate explicit runtime/path/threshold configuration and real validation. Binary models, generated runs and local registry entries stay ignored; candidate metadata remains in source.
