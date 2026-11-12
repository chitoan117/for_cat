# GPIO21 Jetson state latency fix — source checkpoint

Measured existing WS snapshot processing ~4–6ms, but full JSON data shown with
~1.4–2s receiver age due to the phase of the 1Hz bridge publisher. Press event
lines were recorded by the arbiter but did not immediately update button state.

Scope: Jetson bridge publication and existing realtime/provider/UI path only.
No ESP32 firmware, GPIO contract, actuator execution or calibration change.
Original source files are pulled into original/ before edits in payload/.
