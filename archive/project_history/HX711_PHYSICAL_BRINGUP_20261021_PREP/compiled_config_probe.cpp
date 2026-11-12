#include <cstdio>
#include "m4/diagnostic_config.h"
#include "m4/actuator_interfaces.h"
static_assert(M4_HX711_DOUT==4 && M4_HX711_SCK==5,"wrong HX711 GPIO");
static_assert(M4_DIAGNOSTIC_MODE==1 && M4_HX711_INSTALLED==1,"wrong isolated mode");
static_assert(M4_SERVO_PWM==-1 && M4_PUMP_MOSFET==-1,"actuator pins assigned");
int main() {
  std::printf("{\"scope\":\"HOST_CONFIG_ONLY\",\"dout\":%d,\"sck\":%d,\"mode\":%d,\"actuator_outputs_enabled\":%d,\"servo_enabled\":%d,\"pump_enabled\":%d}\n",
    M4_HX711_DOUT,M4_HX711_SCK,M4_DIAGNOSTIC_MODE,ACTUATOR_OUTPUTS_ENABLED,SERVO_DIAGNOSTIC_ENABLED,PUMP_DIAGNOSTIC_ENABLED);
}
