#pragma once

// Owner-approved wiring contract, 2026-10-21. Declaration is NOT physical PASS.
// These constants do not attach PWM, set pin modes or grant actuator permission.
namespace current_hardware {
constexpr int UNASSIGNED = -1;
constexpr int HX711_DOUT = 4, HX711_SCK = 5;
constexpr int SERVO_SIGNAL = 6, PUMP_CONTROL = 7;
constexpr int OLED_SDA = 8, OLED_SCL = 9;
#if defined(M4_QUAD_ULTRASONIC) && M4_QUAD_ULTRASONIC
constexpr int OPTIONAL_WATER_INPUT = -1, PIR_OUT = 11;
constexpr int HC2_TRIG=16,HC2_ECHO=17,JSN2_TRIG=18,JSN2_ECHO=10;
#else
constexpr int OPTIONAL_WATER_INPUT = 10, PIR_OUT = 11;
#endif
constexpr int APPROACH_TRIG = 12, APPROACH_ECHO = 13;
constexpr int WATER_OPERATIONAL_TRIG = 14, WATER_OPERATIONAL_ECHO = 15;
#if defined(M4_QUAD_ULTRASONIC) && M4_QUAD_ULTRASONIC
constexpr int RTC_CLK=-1,RTC_DAT=-1,RTC_CE=-1;
#else
constexpr int RTC_CLK = 16, RTC_DAT = 17, RTC_CE = 18;
#endif
constexpr int FOOD_RESERVOIR_TRIG = UNASSIGNED, FOOD_RESERVOIR_ECHO = UNASSIGNED;
constexpr int WATER_RESERVOIR_TRIG = UNASSIGNED, WATER_RESERVOIR_ECHO = UNASSIGNED;
#if defined(M4_QUAD_ULTRASONIC) && M4_QUAD_ULTRASONIC
constexpr int signals[]={4,5,6,7,8,9,10,11,12,13,14,15,16,17,18};
#else
constexpr int signals[] = {HX711_DOUT,HX711_SCK,SERVO_SIGNAL,PUMP_CONTROL,OLED_SDA,
    OLED_SCL,OPTIONAL_WATER_INPUT,PIR_OUT,APPROACH_TRIG,APPROACH_ECHO,
    WATER_OPERATIONAL_TRIG,WATER_OPERATIONAL_ECHO,RTC_CLK,RTC_DAT,RTC_CE};
#endif
constexpr bool unique() {
  for (unsigned i=0;i<sizeof(signals)/sizeof(signals[0]);++i) {
    if (signals[i]<4 || signals[i]>18) return false;
    for (unsigned j=0;j<i;++j) if (signals[i]==signals[j]) return false;
  }
  return true;
}
static_assert(unique(),"Current wiring conflicts or touches excluded USB/UART/strap pins");
static_assert(FOOD_RESERVOIR_TRIG==-1 && FOOD_RESERVOIR_ECHO==-1 &&
              WATER_RESERVOIR_TRIG==-1 && WATER_RESERVOIR_ECHO==-1,
              "Additional inventory sensor pins require owner approval");
} // namespace current_hardware
