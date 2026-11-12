# CAT-only35g food-gate demo — owner requirements

- Owner authorises preparing Jetson recognition to trigger a real food-gate servo
  and close after the load-cell measured35g food increment. No water/pump action.
- **MG996R**, current physical closed position**90°**, open position**45°**;
  close returns to90°. Owner confirmed separate**5V supply**, common GND,
  existing signalGPIO6. HX711 remains GPIO4/5 and owner-confirmed5V board supply.
- **DOG** does not start feeding or move an idle/closed servo. CAT must be fresh
  and valid; mixed scene takes DOG priority via the existing AI tap. During an
  active feed, losing CAT or seeing DOG closes the gate to stop food.
- One feeding episode, no repeated35g while the same CAT remains in view.
- Target35g comes from measured food-weight increase over a stable pre-open
  baseline, not elapsed servo time or a forced display value. Use unsmoothed
  signed median mass; display deadband must not enter the stop decision.
- Earlier Arduino/HX711 port and5/10/20/35g demo evidence are retained. Historical
  slope−1064.4473counts/g was used throughout that fixed-calibration physical
  session; offset−671054.666666667 was captured on ESP32. It is not permanent
  mounting authority. A baseline-difference controller makes the absolute offset
  cancel, while drift/error/actual food flow and overshoot must still be observed.
- Previous firmware is **HX711 diagnostic only**, no servo path; its RAM calibration
  is lost on reset. New firmware/deployment and deliberate persistence handling
  are needed before this requested action can occur.
- Do not change protected detector source/binary/engine or use Python inference.
  Existing C++ OpenCV/YOLOv8n320/TensorRT FP16 CAT/DOG/NONE stays authoritative.
- USB–UART will be moved from the laptop to Jetson by owner. Verify the live
  by-id port and one UART owner before any execution. PWM angle mapping is a
  nominal MG996R command, not measured gate-angle/closure feedback.
