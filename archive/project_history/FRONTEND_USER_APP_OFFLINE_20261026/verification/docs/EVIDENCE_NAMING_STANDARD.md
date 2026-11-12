# Future evidence naming standard

Use the existing UTC pattern consistently:

`YYYYMMDDTHHMMSSZ_COMPONENT_TEST_RESULT.ext`

COMPONENT/TEST use anonymous lowercase slugs; RESULT is `pass`, `fail`, `not_tested` or `inconclusive`. If collision occurs, append a unique run suffix; never overwrite. These patterns are templates, not evidence that an experiment happened. Wall timestamp records the observed clock/timezone; durations/timeouts use monotonic or validated media time.

Each filename links to a lab note carrying run/session/track IDs, exact hardware/software/config/source/dataset/model/firmware hashes, expected versus actual outcome, units/references/uncertainty/tolerance, raw paths and failures. Preserve unsanitized private originals under restricted access; public copies retain an anonymized evidence ID/hash linkage. No private address/name in public filenames.

Host files go in ignored `.checks/` / `.release/`, labelled HOST/SYNTHETIC/COMPILE. Actual future M3/M4/data/model evidence goes in the appropriate private evidence/experiment corpus, not substituted by compiler logs. `EVIDENCE_INDEX.md` maps gates; `LAB_NOTE_TEMPLATE.md` is blank. Planned filenames or completed templates without actual observations are not PASS evidence.
