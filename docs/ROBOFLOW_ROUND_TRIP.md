# Optional local Roboflow round-trip boundary

No upload, API key or network integration is used. Local classification-folder adapter:

```text
python -m ai.scripts.dataset_release export --dataset LOCAL_DATASET --task identity --output NEW_EXPORT
# --apply writes images/LABEL/SAMPLE + provenance.json after review.
python -m ai.scripts.dataset_release import --source RETURNED_EXPORT --output NEW_LOCAL_DATASET
# --apply writes a new local manifest; revalidate and create new splits/releases afterward.
```

Keep `provenance.json` beside returned images. It retains original session_id/source_hash/sample_id/path/labels. Optional `labels.json` maps preserved export paths to reviewed returned classification labels. Images must retain their original hash; changed encoding/crops require explicit provenance reconciliation, not a guessed session. UNKNOWN/UNSURE/SKIP remain unsuitable for clean targets.

Exports lacking session identity return **SESSION_METADATA_MISSING** with split_allowed=false. Never use folder names/random splits as a replacement. Annotation-platform augmentation can create leakage; group all derivatives with their original source/session and repeat integrity/leakage checks.

This implemented adapter is for image **classification**, not a YOLO/COCO bounding-box parser. For future YOLO/COCO detection exports preserve an image-ID→original-session/source sidecar, validate boxes/classes/crop lineage, then add a format-specific converter. Without that sidecar the current importer rejects the export; it does not flatten detector boxes into whole-frame identity truth. No Roboflow result is claimed.
