#pragma once

#include "board_config.h"

// GENERIC_ESP32DEV is a placeholder, NOT HARDWARE VERIFIED. -1 means unassigned.
namespace pins {
constexpr int UNASSIGNED = -1;
constexpr int PIN_NOT_ASSIGNED = UNASSIGNED;
constexpr int HX711_DOUT = UNASSIGNED;
constexpr int HX711_SCK = UNASSIGNED;
constexpr int FOOD_TRIG = UNASSIGNED;
constexpr int FOOD_ECHO = UNASSIGNED;
constexpr int WATER_TRIG = UNASSIGNED;
constexpr int WATER_ECHO = UNASSIGNED;
constexpr int SERVO_PWM = UNASSIGNED;
constexpr int PUMP_MOSFET = UNASSIGNED;
constexpr int I2C_SDA = UNASSIGNED;
constexpr int I2C_SCL = UNASSIGNED;
constexpr int BUZZER = UNASSIGNED;
constexpr int MANUAL_FEED_BUTTON = UNASSIGNED;
static_assert(SERVO_PWM == PIN_NOT_ASSIGNED && PUMP_MOSFET == PIN_NOT_ASSIGNED,
              "Safe profiles prohibit assigning actuator GPIOs");
static_assert(HX711_DOUT == PIN_NOT_ASSIGNED && HX711_SCK == PIN_NOT_ASSIGNED &&
              FOOD_TRIG == PIN_NOT_ASSIGNED && FOOD_ECHO == PIN_NOT_ASSIGNED &&
              WATER_TRIG == PIN_NOT_ASSIGNED && WATER_ECHO == PIN_NOT_ASSIGNED &&
              I2C_SDA == PIN_NOT_ASSIGNED && I2C_SCL == PIN_NOT_ASSIGNED &&
              BUZZER == PIN_NOT_ASSIGNED && MANUAL_FEED_BUTTON == PIN_NOT_ASSIGNED,
              "RC2 has no verified sensor pin profile");
}  // namespace pins
