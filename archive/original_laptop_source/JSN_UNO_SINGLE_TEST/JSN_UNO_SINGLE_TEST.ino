// One JSN-SR04T in TRIG/ECHO pulse mode on Arduino UNO.
// VCC -> 5V, GND -> GND, TRIG -> D9, ECHO -> D10.
// These are UNO test pins, not the ESP32 production pin map.
// Serial Monitor: 115200 baud. No external library required.

const byte TRIG_PIN = 9;
const byte ECHO_PIN = 10;
const unsigned long ECHO_TIMEOUT_US = 45000UL;

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  digitalWrite(TRIG_PIN, LOW);
  pinMode(ECHO_PIN, INPUT);

  Serial.println(F("=== ONE JSN / ARDUINO UNO ==="));
  Serial.println(F("TRIG=D9, ECHO=D10, UART=115200"));
  Serial.println(F("Test a flat target at 50cm, then 100cm."));
  Serial.println(F("TRIG/ECHO pulse mode required; not UART mode."));
  delay(500);
}

void loop() {
  // A high ECHO before triggering is not a valid new measurement.
  if (digitalRead(ECHO_PIN) == HIGH) {
    Serial.println(F("ERROR: ECHO HIGH before trigger; check mode/wiring."));
    delay(500);
    return;
  }

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  const unsigned long pulseUs = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);

  if (pulseUs == 0) {
    Serial.println(F("TIMEOUT: no complete ECHO pulse. Not a 0cm reading."));
  } else {
    // Approximate speed of sound: 343 m/s. Round trip -> divide by two.
    const float distanceCm = pulseUs * 0.0343f / 2.0f;

    Serial.print(F("pulse_us="));
    Serial.print(pulseUs);
    Serial.print(F(" | distance_cm="));
    Serial.print(distanceCm, 1);

    if (distanceCm < 25.0f) {
      Serial.print(F(" | NEAR/BLIND-ZONE: check exact module specification"));
    }

    Serial.println();
  }

  // Long enough spacing for a single module and straightforward bench checks.
  delay(500);
}
