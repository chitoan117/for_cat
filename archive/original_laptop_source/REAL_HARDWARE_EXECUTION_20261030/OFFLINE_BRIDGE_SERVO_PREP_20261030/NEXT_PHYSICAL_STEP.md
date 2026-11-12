# ONE next physical step — servo-specific wiring/model/cutoff evidence

Pump isolation is already OWNER_CONFIRMED: BOTH motor wires removed from F5305S OUTPUT, GPIO7/GND unchanged. Keep the two removed motor leads insulated and disconnected. No repeat isolation task/photo required. Unknown pump polarity no longer blocks the servo-first path.

**Now provide one small photo set:** servo model/voltage label plus wiring showing servo V+ from the common5V source, servo ground referenced to ESP32, GPIO6 signal and the exact independent servo-load cutoff point. Add a sentence confirming the cutoff is reachable and the mechanism has no food/load/hand obstruction. Do not energize/move the servo, change pulse values, reset/unplug ESP32, or open Serial to provide this evidence. If model is not printed, state UNKNOWN instead of selecting a generic model.

Why this is next: GPIO and supply rating are established, but source cannot identify the actual servo voltage range, physical ground/reference, disconnect route or safe starting pulse. ARM can immediately move at CLOSE. Photos identify the actual path/model so the next voltage/initial-position review is specific rather than a guessed1500us or90deg.

Still needed before flashing: exact current HX coefficients or compatible persisted calibration; four ECHO protection evidence; actual bank/security and recovery/executor review in approved maintenance; explicit APP-only approval. Static HX PASS/backup bytes do not close those gates. No need to weigh again or retrain AI.

Conditional commands for the later approved test are in SERVO_TEST_READY.md. They use the unchanged `build_safe_txatomic` image and manual console: SESSION → approved configure → explicit ARM/OPEN → automatic bounded CLOSE/PWMoff. **No command to execute on the device now.** APP FLASH remains NO-GO, first movement awaits specific approval and verified prerequisites.
