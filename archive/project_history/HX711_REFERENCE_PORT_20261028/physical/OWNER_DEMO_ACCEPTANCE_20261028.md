# Owner demo acceptance and consumption goal — 2026-10-28

## Owner steering

Owner states the Arduino reference was already accurate enough in their real
setup, with approximately0.3–0.7g under-reading acceptable. They confirm they did
not change the scale/fixture. Do not infer mechanical damage from the diagnostic
zero/session difference, or demand laboratory accuracy for this demo.

Primary goal: continuous food-weight observation so Jetson can estimate how much
a cat ate and classify coarse interest in the served food.

## Current physical check policy

- Known nonzero test masses: accept signed mean error **within±0.70g**. For5g,
  the allowed mean is4.30–5.70g. This supersedes the earlier±max(.10g,1%)
  nonzero rule **for new demo bench observations**.
- Keep raw counts, signed mass, actual error and stability statistics visible.
  No coefficient refit, fake exact mass, deletion of failed readings or automatic
  tare to meet this threshold.
- Existing empty-window and stability checks are retained as observations of
  valid continuous data: empty mean±.10g, window range≤.20g, sigma≤.05g,
  window-fifths drift≤.10g. These are not claims of loaded-mass accuracy.
- A missing calibration/read failure remains null/INVALID; relaxed accuracy does
  not turn missing data into a valid mass. Previous5g attempt after restart remains
  BLOCKED rather than retroactively PASS.
- The35g **meal target** may tolerate a few grams of portion variation for this
  use case. Do not treat exact35.000g delivery as the objective of this HX711-only
  bench check or claim actual dispensing has been tested.

## OLED / Jetson intended semantics (handoff requirement)

- OLED can display **“Khẩu phần:35g”** or **“Mục tiêu:35g”** for the selected meal.
- Remaining-food and consumed-food values are estimates from valid sensor data,
  updated continuously, with appropriate rounding/approximately labels. A nominal
  target35g is a separate field from the actual/estimated remaining mass.
- Preserve the measured, settled initial food weight at meal start and the settled
  remaining weight later; consumed estimate is their difference. Do not compute
  precise consumption solely from the nominal35g target when the initial measured
  portion differs. Sensor faults retain unknown consumption rather than zero.
- For a35g meal, owner examples of eating much/most/all (e.g.20–35g) indicate
  higher interest; eating little (e.g.5g) or leaving much indicates lower interest.
  Values between examples, such as10–19g, are intermediate/partial intake rather
  than an invented binary preference threshold. The wording “eats1–20g” is not
  used to simultaneously label5g both liked and disliked.
- A future Jetson meal-session rule uses CAT presence and valid before/after
  weights to associate an eating episode with intake, then records a coarse
  food-interest estimate (amount/ratio eaten). AI scope remains CAT/DOG/NONE;
  no cat-identity/OWNER_CAT feature is implied.

This note records the intended OLED/Jetson behavior. This change updates the
physical-test acceptance helper only; no backend/frontend/AI/OLED firmware or
actuator code has been changed in response to this steering.
