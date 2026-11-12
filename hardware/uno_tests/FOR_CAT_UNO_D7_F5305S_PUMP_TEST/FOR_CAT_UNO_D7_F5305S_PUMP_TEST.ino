// FOR_CAT: Arduino UNO -> existing pump driver input (PC817/MOSFET).
// NEVER connect the pump motor directly to an UNO pin.
// Disconnect ESP32 GPIO7 from the driver input before connecting UNO D7.
// UNO output is 5V: only use a driver input verified compatible with 5V.
// ACTIVE_HIGH is an assumption to verify physically, not an OFF guarantee.
// Keep pump power disconnected while uploading/changing polarity.

constexpr byte PUMP_PIN = 7;
constexpr bool ACTIVE_HIGH = true; // Set false if LOW turns the driver ON.
constexpr unsigned long TEST_MS = 10000UL;
bool running = false;
unsigned long startedAt = 0;

void writePump(bool requestedOn) {
  const byte level = (requestedOn == ACTIVE_HIGH) ? HIGH : LOW;
  digitalWrite(PUMP_PIN, level);
}

void stopPump() {
  writePump(false);
  running = false;
  Serial.println(F("OFF REQUEST SENT. Check that the real pump stops."));
}

void printMenu() {
  Serial.println(F("=== FOR_CAT UNO PUMP D7 ==="));
  Serial.println(F("1 = TEST 10 SECONDS; 0 = STOP; ? = MENU"));
  Serial.print(F("Configured ON level: "));
  Serial.println(ACTIVE_HIGH ? F("HIGH") : F("LOW"));
}

void setup() {
  writePump(false); // Set output latch before enabling OUTPUT.
  pinMode(PUMP_PIN, OUTPUT);
  Serial.begin(115200);
  printMenu();
  Serial.println(F("No test started automatically."));
}

void loop() {
  // Service the timeout even if serial input is continuously arriving.
  if (running && (unsigned long)(millis() - startedAt) >= TEST_MS) {
    stopPump();
    Serial.println(F("10-SECOND TEST FINISHED."));
  }

  if (Serial.available() <= 0) return;
  const char cmd = (char)Serial.read();
  if (cmd == '\n' || cmd == '\r' || cmd == ' ') return;
  switch (cmd) {
    case '0':
      stopPump();
      break;
    case '1':
      if (running) {
        Serial.println(F("BUSY. Timer not extended. Press 0 to stop."));
        break;
      }
      startedAt = millis();
      running = true;
      writePump(true);
      Serial.println(F("ON REQUEST: 10 SECONDS. Press 0 to stop."));
      break;
    case '?':
      printMenu();
      break;
    default:
      Serial.println(F("Use 1, 0 or ?."));
      break;
  }
}