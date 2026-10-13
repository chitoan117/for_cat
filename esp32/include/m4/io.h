#pragma once
#include <cstddef>
#include "health.h"

namespace m4 {
enum class Pull : uint8_t { NONE, UP, DOWN };
class PinIO {
 public:
  virtual ~PinIO() = default;
  virtual bool inputAllowed(int pin) const = 0;
  virtual bool outputAllowed(int pin) const = 0;
  virtual void input(int pin, Pull pull) = 0;
  virtual void output(int pin) = 0;
  virtual bool read(int pin) = 0;
  virtual void write(int pin, bool high) = 0;
  virtual void pauseMicros(uint32_t short_us) = 0; // only HX711 1–2 us pulses, never waiting for readiness
  virtual void enterCritical() = 0;
  virtual void exitCritical() = 0;
};
inline bool inputValid(PinIO& io, Pin pin) { return pin.reviewed && io.inputAllowed(pin.number); }
inline bool outputValid(PinIO& io, Pin pin) { return pin.reviewed && io.outputAllowed(pin.number); }

class I2CBus {
 public:
  virtual ~I2CBus() = default;
  virtual bool begin(Pin sda, Pin scl, uint16_t timeout_ms) = 0;
  virtual bool configured() const = 0;
  virtual bool ping(uint8_t address) = 0;
  virtual bool readRegisters(uint8_t address, uint8_t first, uint8_t* output, size_t count) = 0;
  virtual bool writeRegisters(uint8_t address, uint8_t first, const uint8_t* data, size_t count) = 0;
  virtual bool packet(uint8_t address, uint8_t control, const uint8_t* data, size_t count) = 0;
};
}  // namespace m4
