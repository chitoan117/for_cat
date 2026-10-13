#pragma once
#include "board_config.h"
#include "health.h"

#ifndef M4_DIAGNOSTIC_MODE
#define M4_DIAGNOSTIC_MODE 0
#endif
#if M4_DIAGNOSTIC_MODE < 0 || M4_DIAGNOSTIC_MODE > 6
#error "Unknown M4 component diagnostic mode"
#endif
#if M4_DIAGNOSTIC_MODE && (!defined(FORR_HW_SAFE) || defined(SIMULATED_SENSORS))
#error "Real-driver diagnostics must be explicitly selected HW_SAFE, never SIM"
#endif
#ifndef M4_PINS_REVIEWED
#define M4_PINS_REVIEWED 0
#endif
#ifndef M4_HX711_DOUT
#define M4_HX711_DOUT -1
#endif
#ifndef M4_HX711_SCK
#define M4_HX711_SCK -1
#endif
#ifndef M4_I2C_SDA
#define M4_I2C_SDA -1
#endif
#ifndef M4_I2C_SCL
#define M4_I2C_SCL -1
#endif
#ifndef M4_FOOD_TRIG
#define M4_FOOD_TRIG -1
#endif
#ifndef M4_FOOD_ECHO
#define M4_FOOD_ECHO -1
#endif
#ifndef M4_WATER_TRIG
#define M4_WATER_TRIG -1
#endif
#ifndef M4_WATER_ECHO
#define M4_WATER_ECHO -1
#endif
#ifndef M4_BUTTON_PIN
#define M4_BUTTON_PIN -1
#endif
#ifndef M4_BUTTON_ACTIVE_LOW
#define M4_BUTTON_ACTIVE_LOW 1
#endif
#ifndef M4_BUTTON_PULL
#define M4_BUTTON_PULL 0
#endif
#ifndef M4_BUZZER_PIN
#define M4_BUZZER_PIN -1
#endif
#ifndef M4_ULTRASONIC_MIN_CM
#define M4_ULTRASONIC_MIN_CM 0
#endif
#ifndef M4_ULTRASONIC_MAX_CM
#define M4_ULTRASONIC_MAX_CM 0
#endif
#ifndef M4_OLED_ADDRESS
#define M4_OLED_ADDRESS 0
#endif
#ifndef M4_OLED_HEIGHT
#define M4_OLED_HEIGHT 64
#endif
#if M4_PINS_REVIEWED != 0 && M4_PINS_REVIEWED != 1
#error "M4_PINS_REVIEWED is a reviewed local configuration flag, 0/1 only"
#endif
#if M4_BUTTON_PULL < 0 || M4_BUTTON_PULL > 2
#error "Button pull setting is NONE=0, UP=1, DOWN=2"
#endif
namespace m4 {
inline Pin diagnosticPin(int number) { return {number,M4_PINS_REVIEWED==1}; }
inline const char* diagnosticName() {
  switch (M4_DIAGNOSTIC_MODE) {
    case 1: return "diag_hx711"; case 2: return "diag_rtc"; case 3: return "diag_i2c";
    case 4: return "diag_food_sensor"; case 5: return "diag_water_sensor";
    case 6: return "diag_oled_button_buzzer"; default: return "NONE";
  }
}
}  // namespace m4
