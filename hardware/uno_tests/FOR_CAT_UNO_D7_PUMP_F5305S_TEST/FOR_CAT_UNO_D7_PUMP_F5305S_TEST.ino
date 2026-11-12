/*
  FOR_CAT - Arduino UNO D7 + F5305S water pump test

  F5305S input side:
    UNO D7  -> IN
    UNO GND -> GND (signal input)
  F5305S power/output side:
    DC+ / DC-   -> external DC supply matched to pump rating
    OUT+ / OUT- -> pump + / pump -

  This sketch assumes input is ACTIVE HIGH (IN high = ON),
  as expected when using the module's IN and GND signal terminals.
  Verify on your particular board before connecting the pump.

  Commands (Serial Monitor 115200):
    1: pump 0.5 s
    2: pump 1.5 s
    3: pump 3 s
    0: stop immediately
    ?: print help
  Non-blocking and self-stopping after selected duration.
*/

const byte PUMP_PIN = 7;
const byte PUMP_ON  = HIGH;
const byte PUMP_OFF = LOW;

const unsigned long TEST_1_MS = 500UL;
const unsigned long TEST_2_MS = 1500UL;
const unsigned long TEST_3_MS = 3000UL;

bool pumpRunning = false;
unsigned long startedAt = 0;
unsigned long durationMs = 0;

void stopPump() {
  digitalWrite(PUMP_PIN, PUMP_OFF);
  if (pumpRunning) {
    Serial.println("PUMP OFF");
  }
  pumpRunning = false;
}

void startPump(unsigned long requestedMs) {
  stopPump();
  durationMs = requestedMs;
  startedAt = millis();
  digitalWrite(PUMP_PIN, PUMP_ON);
  pumpRunning = true;
  Serial.print("PUMP ON - ");
  Serial.print(requestedMs);
  Serial.println(" ms");
}

void printHelp() {
  Serial.println("=== FOR_CAT UNO D7 - F5305S PUMP ===");
  Serial.println("1 = PUMP ON 500 ms then OFF");
  Serial.println("2 = PUMP ON 1500 ms then OFF");
  Serial.println("3 = PUMP ON 3000 ms then OFF");
  Serial.println("0 = OFF immediately");
  Serial.println("? = Help");
}

void setup() {
  // Preload output LOW before changing pin to OUTPUT.
  digitalWrite(PUMP_PIN, PUMP_OFF);
  pinMode(PUMP_PIN, OUTPUT);
  Serial.begin(115200);
  stopPump();
  printHelp();
}

void loop() {
  while (Serial.available() > 0) {
    char command = (char)Serial.read();
    if (command == '\r' || command == '\n' || command == ' ') continue;

    switch (command) {
      case '0': stopPump(); Serial.println("STOP COMMAND"); break;
      case '1': startPump(TEST_1_MS); break;
      case '2': startPump(TEST_2_MS); break;
      case '3': startPump(TEST_3_MS); break;
      case '?': printHelp(); break;
      default: Serial.println("Unknown command. Type ?"); break;
    }
  }

  if (pumpRunning && (unsigned long)(millis() - startedAt) >= durationMs) {
    stopPump();
  }
}
