# Optional Roboflow annotation workflow (documentation only)

forr_cat does not depend on Roboflow; no API key, account, upload, hosted inference or library is configured. Local tooling continues to work offline. Future user-reviewed workflow:

Real videos/images → local anonymous **recording session IDs and hashes** → optionally upload selected images and session sidecar → annotate → export → local validation → reconstruct session-safe splits → train only after data quality review.

Keep `sample_id`, original recording `session_id`, source video/hash/offset and conditions in an independent local manifest. Annotation/export tools may rename filenames or remove those fields; keep a reversible sample-ID mapping. **Never accept a random frame-level split** that places neighboring images from one session in train and test. Rebuild all splits by session locally (or stronger source/day group if sessions overlap); verify duplicates and leakage after export.

Future lightweight converters could consume YOLO image/label files or COCO image/annotation JSON, but must resolve original IDs via the sidecar, validate class maps/boxes/image corruption, and preserve local metadata. No YOLO/COCO converter is claimed implemented in RC2. OWNER_CAT/OTHER_CAT identity labels and temporal EATING/DRINKING session labels need a study-specific annotation protocol; object boxes alone are not behavior or identity ground truth. Review privacy/consent, dataset ownership and export licence before any optional upload. Never use an internet dataset as if it were the user's cat.
