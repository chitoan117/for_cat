#pragma once
#include "pins.h"
// Restored from the existing Windows hardware work: candidate wiring, not GPIO PASS.
#ifndef M4_SENSOR_BRINGUP
#define M4_SENSOR_BRINGUP 0
#endif
#if M4_SENSOR_BRINGUP != 0 && M4_SENSOR_BRINGUP != 1
#error "M4_SENSOR_BRINGUP must be 0 or 1"
#endif
#ifndef M4_SERVO_PWM
#define M4_SERVO_PWM -1
#endif
#ifndef M4_PUMP_MOSFET
#define M4_PUMP_MOSFET -1
#endif
static_assert(M4_SERVO_PWM == -1 && M4_PUMP_MOSFET == -1,"Sensor profile cannot assign actuators");
#if M4_SENSOR_BRINGUP
#if !defined(FORR_REAL_S3_NO_PSRAM) || !defined(FORR_HW_SAFE) || !M4_DIAGNOSTIC_MODE
#error "Candidate sensors require the explicit S3 no-PSRAM diagnostic profile"
#endif
#if defined(M4_RTC_CLK) || defined(M4_RTC_DAT) || defined(M4_RTC_CE) || defined(M4_HX711_DOUT) || defined(M4_HX711_SCK) || defined(M4_I2C_SDA) || defined(M4_I2C_SCL) || defined(M4_FOOD_TRIG) || defined(M4_FOOD_ECHO) || defined(M4_WATER_TRIG) || defined(M4_WATER_ECHO) || defined(M4_BUTTON_PIN) || defined(M4_BUZZER_PIN) || defined(M4_PINS_REVIEWED)
#error "Do not mix pin overrides with the documented candidate profile"
#endif
#if (defined(SERVO_DIAGNOSTIC_ENABLED) && SERVO_DIAGNOSTIC_ENABLED) || (defined(PUMP_DIAGNOSTIC_ENABLED) && PUMP_DIAGNOSTIC_ENABLED)
#error "Sensor profile forbids active servo/pump diagnostics"
#endif
#define M4_PINS_REVIEWED 1
#define M4_HX711_DOUT 4
#define M4_HX711_SCK 5
#define M4_FOOD_TRIG 6
#define M4_FOOD_ECHO 7
#define M4_I2C_SDA 8
#define M4_I2C_SCL 9
#define M4_WATER_TRIG 10
#define M4_WATER_ECHO 11
#define M4_BUTTON_PIN 12
#define M4_BUZZER_PIN 13
#define M4_RTC_CLK 16
#define M4_RTC_DAT 17
#define M4_RTC_CE 18
#define M4_BUTTON_PULL 1
#define M4_BUTTON_ACTIVE_LOW 1
#define M4_OLED_ADDRESS 0x3c
#define M4_ULTRASONIC_MIN_CM 1
#define M4_ULTRASONIC_MAX_CM 400
namespace m4_candidate {
constexpr int signals[] = {4,5,6,7,8,9,10,11,12,13,16,17,18};
constexpr bool validMapping() {
  for (unsigned i=0;i<13;++i) {
    if (!((signals[i]>=4 && signals[i]<=13) || (signals[i]>=16 && signals[i]<=18))) return false;
    for (unsigned j=0;j<i;++j) if (signals[i]==signals[j]) return false;
  }
  return true;
}
static_assert(validMapping(),"Unique sensor pins, no UART/USB/strap/actuator pins");
static_assert(pins::SERVO_PWM == -1 && pins::PUMP_MOSFET == -1 && ACTUATOR_OUTPUTS_ENABLED == 0,"Actuators stay disabled");
}
#endif
