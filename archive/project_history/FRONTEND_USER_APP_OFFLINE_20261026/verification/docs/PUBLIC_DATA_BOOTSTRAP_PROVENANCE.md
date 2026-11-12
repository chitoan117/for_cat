# Public-data bootstrap — offline provenance first, not owner's final dataset

No public dataset is selected/downloaded/trained in this pass. Reference links in `REFERENCE_MAP.md` are not a licensed corpus. Roboflow/GitHub hosting or “public” visibility does not prove reuse permission, original capture ownership or session independence. This workflow must not delay hardware bring-up.

1. Select a named research/platform release and original publisher/version URL; inspect actual license/data usage and image/video origin. Keep license text/URL/version/date and any limits/attribution separately.
2. Record explicit source groups (original video/session/subject/derivative lineage) and source/file hashes. If groups were lost, SESSION_METADATA_MISSING: quarantine from clean final train/test split; do not invent independence.
3. Record an offline manifest schema1: dataset_id,publisher,version,source_url,license_name,license_url,timezone-aware accessed_at,source_grouping,license_reviewed=true,use_for_final_test=false,label_mapping. `python -m ai.scripts.public_provenance --manifest ACTUAL_RECORD.json` validates fields; it does not legally approve/download/import data.
4. Map reviewed CAT/OTHER_CAT/OTHER_OBJECT/behavior or UNKNOWN/UNSURE/SKIP, not public OWNER_CAT. Generic cat images are not proof of this owner's identity. Whole-frame labels, detector boxes and event annotations are different tasks; do not flatten YOLO/COCO boxes as identity truth.
5. After operator-approved local acquisition, existing bounded import/extract/label/release tools validate images/hashes/groups/duplicates. Keep PUBLIC_BOOTSTRAP domain in separate folders/release/provenance sidecar, preserve source groups through any derivatives/Roboflow round-trip.
6. Use bootstrap for detector, other-cat diversity or preliminary behavior/training plumbing. Preserve all test/report labels as PUBLIC-DOMAIN EXPERIMENT, not installed-system accuracy.
7. OWNER_CAT must come from the user's own cat. Final test prioritizes **new** recordings from actual4a54:5233 camera, actual bowl/mount/lighting, held-out original sessions/videos; no nearby/duplicate frames shared with train/validation. Repeat leakage/near/crop lineage review across public and owner data.

Behavioral labels need temporal evidence; public EATING/DRINKING descriptions alone are not verified event boundaries. Confidence/threshold selection uses validation only; actual own-camera held-out errors and shadow evidence are required. AI_SHADOW_MODE stays true; public import never activates a model or physical feed.
