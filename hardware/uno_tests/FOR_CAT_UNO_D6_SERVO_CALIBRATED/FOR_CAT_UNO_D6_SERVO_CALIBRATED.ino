#include <Servo.h>

// FOR_CAT - Thu servo quay lien tuc tren Arduino UNO
// Da thu tren co cau that: mo sang PHAI, dong sang TRAI.
// Signal D6. Servo dung nguon 5-6V NGOAI, GND chung voi UNO.

Servo feederServo;

constexpr byte SERVO_PIN = 6;
constexpr int STOP_US  = 1500;
constexpr int OPEN_US  = 1400;    // Chieu mo sang PHAI da xac nhan
constexpr int CLOSE_US = 1600;    // Chieu dong sang TRAI da xac nhan

constexpr unsigned long OPEN_MS = 1200;  // 6 x 200 ms
constexpr unsigned long CLOSE_MS = 1040; // 4 x 200 ms + 2 x 120 ms
constexpr unsigned long FINE_MS = 120;

bool moving = false;
unsigned long moveStart = 0;
unsigned long moveFor = 0;

void stopServo() {
  feederServo.writeMicroseconds(STOP_US);
  moving = false;
  Serial.println(F("SERVO STOP (1500us)"));
}

void startMove(int pulseUs, unsigned long durationMs, const __FlashStringHelper* label) {
  if (moving) {
    Serial.println(F("DANG CHAY. BAM 0 NEU CAN DUNG NGAY."));
    return;
  }
  feederServo.writeMicroseconds(pulseUs);
  moveStart = millis();
  moveFor = durationMs;
  moving = true;

  Serial.print(label);
  Serial.print(F(" | pulse="));
  Serial.print(pulseUs);
  Serial.print(F("us | time="));
  Serial.print(durationMs);
  Serial.println(F("ms"));
}

void printMenu() {
  Serial.println(F("=== FOR_CAT UNO SERVO D6 - CALIBRATION ==="));
  Serial.println(F("3 = MO SANG PHAI (1400us, 1200ms)"));
  Serial.println(F("4 = DONG SANG TRAI (1600us, 1040ms)"));
  Serial.println(F("1 = DONG BU 120ms"));
  Serial.println(F("2 = MO BU 120ms"));
  Serial.println(F("0 = DUNG NGAY"));
  Serial.println(F("Chi kiem tra khi dang quan sat co cau."));
}

void setup() {
  Serial.begin(115200);
  feederServo.attach(SERVO_PIN);
  feederServo.writeMicroseconds(STOP_US);
  printMenu();
}

void loop() {
  // Nhan lenh lien tuc de co the dung khan cap trong khi dang quay.
  while (Serial.available() > 0) {
    const char cmd = (char)Serial.read();
    if (cmd == '\n' || cmd == '\r' || cmd == ' ') continue;

    switch (cmd) {
      case '0':
        stopServo();
        break;
      case '3':
        startMove(OPEN_US, OPEN_MS, F("MO PHAI"));
        break;
      case '4':
        startMove(CLOSE_US, CLOSE_MS, F("DONG TRAI"));
        break;
      case '1':
        startMove(CLOSE_US, FINE_MS, F("DONG BU"));
        break;
      case '2':
        startMove(OPEN_US, FINE_MS, F("MO BU"));
        break;
      default:
        Serial.println(F("LENH KHONG HOP LE"));
        printMenu();
        break;
    }
  }

  if (moving && (millis() - moveStart >= moveFor)) {
    stopServo();
  }
}
