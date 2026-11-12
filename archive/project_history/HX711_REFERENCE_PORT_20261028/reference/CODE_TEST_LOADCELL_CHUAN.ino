/*
   LOAD CELL 1KG + HX711
   FAST RESPONSE + STABLE DISPLAY
   Arduino UNO

   HX711:
   DT  -> D4
   SCK -> D5
   VCC -> 5V
   GND -> GND

   Serial Monitor: 115200
*/

#define HX711_DT   4
#define HX711_SCK  5

// Calibration da do duoc cua ban
long offsetRaw = -668483;
float scaleFactor = -1064.4473;

// Nho hon +/-0.20g thi xem nhu 0g
const float ZERO_DEADBAND = 0.20;

// Neu trong luong thay doi >= 1g
// -> cap nhat NGAY LAP TUC, khong loc cham
const float FAST_CHANGE_THRESHOLD = 1.0;

// Khi can dang dung yen,
// chi loc nhe de so khong rung
const float STABLE_ALPHA = 0.40;

float displayedWeight = 0.0;


// =====================================================
// DOC HX711
// =====================================================
bool readHX711(long &value)
{
  unsigned long startTime = millis();

  while (digitalRead(HX711_DT) == HIGH)
  {
    if (millis() - startTime > 500)
      return false;
  }

  unsigned long data = 0;

  noInterrupts();

  for (byte i = 0; i < 24; i++)
  {
    digitalWrite(HX711_SCK, HIGH);
    delayMicroseconds(1);

    data <<= 1;

    if (digitalRead(HX711_DT))
      data |= 1;

    digitalWrite(HX711_SCK, LOW);
    delayMicroseconds(1);
  }

  // Pulse 25 -> Channel A, Gain 128
  digitalWrite(HX711_SCK, HIGH);
  delayMicroseconds(1);

  digitalWrite(HX711_SCK, LOW);
  delayMicroseconds(1);

  interrupts();

  // Chuyen signed 24-bit -> signed 32-bit
  if (data & 0x800000UL)
    data |= 0xFF000000UL;

  value = (long)data;

  // Gia tri loi
  if (value == 0 || value == -1)
    return false;

  return true;
}


// =====================================================
// LAY TRUNG VI 3 MAU
// Giam nhieu nhung van rat nhanh
// =====================================================
long median3(long a, long b, long c)
{
  if (a > b)
  {
    long t = a;
    a = b;
    b = t;
  }

  if (b > c)
  {
    long t = b;
    b = c;
    c = t;
  }

  if (a > b)
  {
    long t = a;
    a = b;
    b = t;
  }

  return b;
}


// =====================================================
// DOC 3 MAU
// =====================================================
bool readStableRaw(long &result)
{
  long a, b, c;

  if (!readHX711(a))
    return false;

  if (!readHX711(b))
    return false;

  if (!readHX711(c))
    return false;

  result = median3(a, b, c);

  return true;
}


// =====================================================
// TARE LAI
// =====================================================
void tareScale()
{
  Serial.println();
  Serial.println("LAY HET VAT RA...");
  Serial.println("Dang TARE...");

  long sum = 0;
  int count = 0;

  for (int i = 0; i < 15; i++)
  {
    long raw;

    if (readHX711(raw))
    {
      sum += raw;
      count++;
    }
  }

  if (count > 0)
  {
    offsetRaw = sum / count;

    displayedWeight = 0.0;

    Serial.print("TARE OK. OFFSET = ");
    Serial.println(offsetRaw);
  }
  else
  {
    Serial.println("TARE ERROR");
  }
}


// =====================================================
// SETUP
// =====================================================
void setup()
{
  Serial.begin(115200);

  pinMode(HX711_DT, INPUT);
  pinMode(HX711_SCK, OUTPUT);

  digitalWrite(HX711_SCK, LOW);

  delay(1000);

  Serial.println();
  Serial.println("==================================");
  Serial.println(" LOAD CELL FAST RESPONSE");
  Serial.println(" DT  = D4");
  Serial.println(" SCK = D5");
  Serial.println("==================================");

  Serial.print("OFFSET = ");
  Serial.println(offsetRaw);

  Serial.print("SCALE = ");
  Serial.println(scaleFactor, 4);

  Serial.println();
  Serial.println("Nhan t de TARE lai khi can rong.");
  Serial.println();

  displayedWeight = 0.0;
}


// =====================================================
// LOOP
// =====================================================
void loop()
{
  // -------------------------------
  // Lenh TARE
  // -------------------------------
  if (Serial.available())
  {
    char command = Serial.read();

    if (command == 't' || command == 'T')
    {
      tareScale();
    }
  }


  // -------------------------------
  // DOC CAN
  // -------------------------------
  long raw;

  if (!readStableRaw(raw))
    return;


  float currentWeight =
      ((float)(raw - offsetRaw)) / scaleFactor;


  // -------------------------------
  // VUNG 0g
  // -------------------------------
  if (currentWeight > -ZERO_DEADBAND &&
      currentWeight < ZERO_DEADBAND)
  {
    currentWeight = 0.0;
  }


  // Khong cho am nhe
  if (currentWeight < 0.0 &&
      currentWeight > -0.5)
  {
    currentWeight = 0.0;
  }


  // -------------------------------
  // PHAT HIEN THAY DOI LON
  // -------------------------------
  float difference =
      currentWeight - displayedWeight;

  if (difference < 0)
    difference = -difference;


  if (difference >= FAST_CHANGE_THRESHOLD)
  {
    // THAY DOI LON:
    // DAT / LAY VAT -> CAP NHAT NGAY
    displayedWeight = currentWeight;
  }
  else
  {
    // THAY DOI NHO:
    // Chi la nhieu -> loc nhe
    displayedWeight =
        STABLE_ALPHA * currentWeight +
        (1.0 - STABLE_ALPHA) * displayedWeight;
  }


  // Gan 0 thi ep ve 0
  if (displayedWeight > -ZERO_DEADBAND &&
      displayedWeight < ZERO_DEADBAND)
  {
    displayedWeight = 0.0;
  }


  // -------------------------------
  // HIEN THI
  // -------------------------------
  Serial.print("KHOI LUONG = ");
  Serial.print(displayedWeight, 2);
  Serial.println(" g");
}
