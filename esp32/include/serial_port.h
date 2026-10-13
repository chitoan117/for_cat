#pragma once
#include <Arduino.h>
#include "board_config.h"

// Bridge profile: explicit UART0. S3 native profile: Serial aliases HW CDC
// with official manifest ARDUINO_USB_MODE=1 / CDC_ON_BOOT=1. No pin remapping.
inline auto& protocolSerial() {
#if defined(FORR_NATIVE_USB) && FORR_NATIVE_USB
  return Serial;
#else
  return Serial0;
#endif
}
