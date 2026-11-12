# Empty-bowl gate diagnosis — 2026-11-06

At15:56:59 the live bridge sent CAT request and the MCU refused it because signed bowl mass was-2.47g outside the existing ±2g empty-bowl condition. The subsequent read was-16.56g, READY, no inspect lock, and healthy communication. Servo profile1350us/900ms OPEN,1600us/1450ms CLOSE remained unchanged.

Owner confirmed bowl empty and in the intended position. A preserving-factor retare was saved, and automatic CAT/DOG mode was kept exited for a stationary test. The first45s check did not pass. A further read-only30s window showed a sustained-26.6g interval followed by0g and a6.41g transient, with corresponding raw ADC changes. Owner then confirmed lifting or touching the bowl/scale during that window. These observations do not establish an electrical or software-filter fault.

The zero reference includes the empty bowl. Removing that bowl is expected to produce a negative reading; it must not prompt another empty-platform tare when the desired operational reference is the bowl in place.

settled_rezero.py rejected its unstable pre-window and did NOT perform an additional tare. verify_and_resume.py performs a new30s stationary check without changing calibration, requires fresh telemetry and a last20-sample span<0.8g with absolute mass<1.5g, and only then issues START. Actual completion must be evidenced by verified_resume.json; if absent, automatic mode remains exited from the earlier failed test. No direct servo OPEN/CLOSE/feed command was sent. No UI, firmware, sensor pin or empty-bowl threshold change was made.

Completion: verified_resume.json confirms a fresh30s stationary-bowl observation with the last20 readings all0.0g, no additional tare, followed by acknowledged exited=0, sensor=1, READY, inspect_lock=0 and moving=0. Servo defaults still1350us/900ms OPEN and1600us/1450ms CLOSE. AI was online/NONE and E1≈55.6cm at restoration. Subsequent observation remained READY; no fresh automatic CAT request had been logged at the final check. Owner's next physical cat trial remains pending; no actual new automatic opening is claimed for this session.
