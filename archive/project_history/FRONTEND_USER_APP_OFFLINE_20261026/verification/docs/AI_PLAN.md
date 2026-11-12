# AI research plan

Historical phase navigation: `CURRENT_PROJECT_STATE.md` · `PRE_HARDWARE_FINAL_BASELINE.md` · `PRE_HARDWARE_HANDOFF.md`.

> **Historical high-level phases, not the current execution order:** use `AI_RESEARCH_EXECUTION_PLAN.md` for the seven future experiments and `CURRENT_PROJECT_STATE.md` for current evidence. No AI results exist.

No datasets downloaded, model training, inference or accuracy claims in Phase 1. The synthetic camera frames do not contain cats. Recognition confidence is optional and remains unset until a real model supplies it.

1. **AI Phase 1:** distinguish owner cat, other cat, other object (plus no subject / unknown).
2. **AI Phase 2:** distinguish eating, drinking, other (plus near bowl, leaving, unknown).
3. **AI Phase 3:** temporal tracking of eating/drinking times, durations and repeat visits.
4. **AI Phase 4:** combine vision observations and validated weight/level sensor measurements.
5. **AI Phase 5:** food-preference **behavioral preference trend** analysis across multiple feeding sessions, never certainty about the animal's internal state.

The data contracts reserve identity, timestamps, behavior, feeding session ID, food type, eating/drinking intervals and durations, dispensed/remaining/estimated consumed grams, approach delay, visit duration and repeat visits. Multiple sessions should contribute percentage consumed, delay, eating duration, leftovers, returns and consistency. Do not infer a food preference from one image. Actual estimates require calibrated hardware and observation validation.
