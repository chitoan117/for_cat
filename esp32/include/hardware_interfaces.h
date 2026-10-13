#pragma once

// Phase 1 contracts only. No pins, drivers, or actuators are initialized.
struct SensorSnapshot {
  bool loadCellValid;
  float foodGrams;
  bool foodLevelValid;
  bool waterLevelValid;
  bool rtcValid;
};

class LoadCellHx711 {
 public:
  virtual ~LoadCellHx711() = default;
  virtual bool readGrams(float& grams) = 0;
};

class FoodLevelSensor {
 public:
  virtual ~FoodLevelSensor() = default;
  virtual bool foodAvailable() = 0;
};

class WaterLevelSensor {
 public:
  virtual ~WaterLevelSensor() = default;
  virtual bool waterAvailable() = 0;
};

class Ds3231Clock {
 public:
  virtual ~Ds3231Clock() = default;
  virtual bool validTime() = 0;
};

class Ssd1306Display {
 public:
  virtual ~Ssd1306Display() = default;
  virtual void showStatus(const char* status) = 0;
};

class BuzzerInterface {
 public:
  virtual ~BuzzerInterface() = default;
  virtual void signalFault() = 0;
};

class ManualFeedButton {
 public:
  virtual ~ManualFeedButton() = default;
  virtual bool pressed() = 0;
};

class SafetyController {
 public:
  // Future checks: cooldown, daily limit, sensor faults, level, RTC and timeout.
  // A remote request must pass here before any actuator can be driven.
  bool mayFeed(const SensorSnapshot&) const { return false; }
};

class ServoInterface {
 public:
  virtual ~ServoInterface() = default;
  virtual void stop() = 0;
  virtual bool dispense() = 0;
};

class PumpInterface {
 public:
  virtual ~PumpInterface() = default;
  virtual void stop() = 0;
  virtual bool runFor(unsigned long maxMilliseconds) = 0;
};
