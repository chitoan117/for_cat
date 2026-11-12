# OLED / buzzer / Manual Feed button — independent M4 checks

> **Current command availability:** `diag_oled_button_buzzer` exists for minimal SSD1306, active-buzzer patterns and button intents; see `M4_DIAGNOSTIC_COMMANDS.md`. Earlier interface-only wording is HISTORICAL / NOT CURRENT. All modules/wiring remain unverified and actuator requests stay rejected.

Prerequisites: M3, exact GPIO/I2C/logic plan, identified modules and **approved bounded accessory-only drivers**. Current code has interfaces/debouncer/simulators, not real accessory test tools. Keep servo/pump disconnected.

| Component | Connections/test | PASS / FAIL |
| --- | --- | --- |
| SSD1306 OLED | verified I2C voltage/address, show actual status/fault; unplug/fault the display safely under test image | PASS readable real status and display fault cannot block safety/control; FAIL bus hang, fake healthy sensor label or control waits indefinitely |
| Buzzer | identify active/passive, current rating/driver; short scheduled alert; no blocking delay loop | PASS bounded non-blocking pattern with control still responsive; FAIL stuck sound/current issue or alarm stalls control |
| Manual button | define pull-up/pull-down and pressed polarity, stable released boot, debounce; press/hold/release/bounce | PASS one intent per stable press, no boot/hold duplicate; FAIL floating input, boot strap conflict or repeated unintended intent |

Commands: after reviewed future test firmware, `pio device monitor --port ACTUAL_COM --baud 115200` records its accessory/control timing. No present CLI activates hardware. Save wiring/photo, firmware hash, actual displayed state, alert duration/responsiveness and button event trace under `evidence/esp32/`. A Manual Feed button test must still pass the policy and **reject execution in disabled-output builds**. Next gate: later unloaded servo, only after separate approval/power/mechanical review.
