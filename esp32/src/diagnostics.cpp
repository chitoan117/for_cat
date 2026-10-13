#include <Arduino.h>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include "m4/diagnostic_config.h"

#if M4_DIAGNOSTIC_MODE != 0
#include "serial_port.h"
#include "m4/arduino_io.h"
#include "m4/hx711.h"
#include "m4/rtc.h"
#include "m4/ultrasonic.h"
#include "m4/accessories.h"
#include "m4/oled.h"
#include "m4/actuator_interfaces.h"
#include "m4/snapshot.h"

namespace {
m4::ArduinoPins pins_io;
m4::ArduinoI2C bus(pins_io);
m4::Hx711 scale(pins_io);
m4::Ds3231 rtc(bus);
m4::I2CScanner scanner(bus);
m4::LevelSensor food(pins_io), water(pins_io);
m4::ManualButton button(pins_io);
m4::Buzzer buzzer(pins_io);
m4::Ssd1306 oled(bus);
m4::DisabledServo servo;
m4::DisabledPump pump;
safety::WaterController shadow_water;
m4::NvsCalibration calibration_store;
m4::CalibrationRecord calibration;
m4::SensorSnapshot snapshot;
char command_buffer[96]{};
size_t command_size=0;
bool discard_command=false;
uint32_t last_report=0, last_measure=0, last_rtc=0;
enum class AverageAction { NONE, RAW, TARE, CALIBRATE, VALIDATE };
AverageAction average_action=AverageAction::NONE;
double reference_mass=0;

template<class T> void number(const m4::Reading<T>& value) {
  if (value.valid) protocolSerial().printf("%.6f",static_cast<double>(value.value));
  else protocolSerial().print("null");
}
void report() {
  auto& serial=protocolSerial();
  serial.printf("{\"mode\":\"%s\",\"monotonic_ms\":%lu,\"hardware_verified\":false,",
                m4::diagnosticName(),static_cast<unsigned long>(snapshot.sampled_at_ms));
  serial.printf("\"rtc_health\":\"%s\",\"rtc_epoch\":",m4::name(snapshot.rtc.health));
  if (snapshot.rtc_time.valid) serial.printf("%llu",static_cast<unsigned long long>(m4::epoch(snapshot.rtc_time.value)));
  else serial.print("null");
  serial.printf(",\"weight_health\":\"%s\",\"weight_reason\":\"%s\",\"raw_counts\":",
                m4::name(snapshot.load_cell.health),m4::name(snapshot.load_cell.reason)); number(snapshot.raw_weight);
  serial.print(",\"grams\":"); number(snapshot.grams);
  serial.printf(",\"food_health\":\"%s\",\"food_reason\":\"%s\",\"food_distance_cm\":",
                 m4::name(snapshot.food.health),m4::name(snapshot.food.reason)); number(snapshot.food_distance_cm);
  serial.print(",\"food_raw_distance_cm\":"); number(snapshot.food_raw_distance_cm);
  serial.print(",\"food_filtered_distance_cm\":"); number(snapshot.food_distance_cm);
  serial.print(",\"food_percent\":"); number(snapshot.food_percent);
  serial.printf(",\"water_health\":\"%s\",\"water_reason\":\"%s\",\"water_distance_cm\":",
                 m4::name(snapshot.water.health),m4::name(snapshot.water.reason)); number(snapshot.water_distance_cm);
  serial.print(",\"water_raw_distance_cm\":"); number(snapshot.water_raw_distance_cm);
  serial.print(",\"water_filtered_distance_cm\":"); number(snapshot.water_distance_cm);
  serial.print(",\"water_percent\":"); number(snapshot.water_percent);
  serial.printf(",\"water_state_code\":%u,\"water_reason_code\":%u,\"would_request_pump\":%s,\"hypothetical_pump_ready\":true,"
                "\"physical_pump_on\":false,\"actuator_outputs_enabled\":0,\"oled_health\":\"%s\","
                "\"button_health\":\"%s\",\"buzzer_health\":\"%s\"}\r\n",
                 static_cast<unsigned>(snapshot.water_state),static_cast<unsigned>(shadow_water.reason()),snapshot.would_request_pump ? "true":"false",
                m4::name(oled.status.health),m4::name(button.status.health),m4::name(buzzer.status.health));
}
void copyCalibration() {
  scale.applyCalibration(calibration.hx711); food.calibration=calibration.food; water.calibration=calibration.water;
  average_action=AverageAction::NONE;
  snapshot.load_cell=scale.status; snapshot.grams=scale.grams;
  food.update(); water.update(); snapshot.food=food.status; snapshot.food_percent=food.percent;
  snapshot.water=water.status; snapshot.water_percent=water.percent;
  snapshot.water_percent.fresh=false; // recalculating geometry is not a new physical echo
#if M4_DIAGNOSTIC_MODE == 5
  m4::tickShadowWater(shadow_water,snapshot);
  snapshot.water_state=shadow_water.state(); snapshot.would_request_pump=shadow_water.pumpRequested();
#endif
}
void command(const char* text) {
  auto& serial=protocolSerial();
  unsigned count=0; double mass=0; float full=0,empty=0; char extra=0;
  if (std::strcmp(text,"help")==0) {
    serial.println("M4 ASCII ONLY: status; avg N; tare N; cal GRAMS N; validate GRAMS N; "
                   "food-geometry FULL_CM EMPTY_CM; water-geometry FULL_CM EMPTY_CM; load; save YES; "
                   "scan; set-utc YYYY-MM-DDTHH:MM:SSZ CONFIRM; buzz confirm|warning|fault. NO FEED/SERVO/PUMP commands.");
  } else if (std::strcmp(text,"status")==0) { report();
  } else if (M4_DIAGNOSTIC_MODE==1 && std::sscanf(text,"avg %2u %c",&count,&extra)==1) {
    if (count>=1 && count<=64 && scale.startAverage(count)) average_action=AverageAction::RAW;
    else serial.println("REJECTED CONFIGURATION_INVALID");
  } else if (M4_DIAGNOSTIC_MODE==1 && std::sscanf(text,"tare %2u %c",&count,&extra)==1) {
    if (count>=1 && count<=64 && scale.startAverage(count)) average_action=AverageAction::TARE;
    else serial.println("REJECTED CONFIGURATION_INVALID");
  } else if (M4_DIAGNOSTIC_MODE==1 && std::sscanf(text,"cal %lf %2u %c",&mass,&count,&extra)==2) {
    if (std::isfinite(mass) && mass>0 && count>=1 && count<=64 && scale.startAverage(count)) {
      reference_mass=mass; average_action=AverageAction::CALIBRATE;
    } else serial.println("REJECTED INVALID_CALIBRATION");
  } else if (M4_DIAGNOSTIC_MODE==1 && std::sscanf(text,"validate %lf %2u %c",&mass,&count,&extra)==2) {
    if (std::isfinite(mass) && mass>0 && count>=1 && count<=64 && scale.startAverage(count)) {
      reference_mass=mass; average_action=AverageAction::VALIDATE;
    } else serial.println("REJECTED INVALID_REFERENCE");
  } else if (M4_DIAGNOSTIC_MODE==4 && std::sscanf(text,"food-geometry %f %f %c",&full,&empty,&extra)==2) {
    if (calibration.food.set(full,empty)) { copyCalibration(); serial.println("MEASURED_GEOMETRY_ACCEPTED not yet saved"); }
    else serial.println("REJECTED GEOMETRY_INVALID");
  } else if (M4_DIAGNOSTIC_MODE==5 && std::sscanf(text,"water-geometry %f %f %c",&full,&empty,&extra)==2) {
    if (calibration.water.set(full,empty)) { copyCalibration(); serial.println("MEASURED_GEOMETRY_ACCEPTED not yet saved"); }
    else serial.println("REJECTED GEOMETRY_INVALID");
  } else if (std::strcmp(text,"load")==0) {
    const auto loaded=calibration_store.load(calibration); copyCalibration();
    serial.printf("CALIBRATION_LOAD code=%u (0=MISSING 1=INVALID 2=LOADED); NOT NVS HARDWARE VERIFIED\r\n",static_cast<unsigned>(loaded));
  } else if (std::strcmp(text,"save YES")==0) {
    calibration.hx711=scale.calibration;
    const bool measured=calibration.hx711.valid() || calibration.food.valid() || calibration.water.valid();
    serial.println(measured && calibration_store.save(calibration) ? "CALIBRATION_SAVED not safety counters" : "REJECTED NOT_CALIBRATED_OR_NVS_ERROR");
  } else if (M4_DIAGNOSTIC_MODE==3 && std::strcmp(text,"scan")==0) {
    serial.println(scanner.start() ? "I2C_SCAN_STARTED" : "CONFIGURATION_INVALID no I2C touched");
  } else if (M4_DIAGNOSTIC_MODE==2 && std::strncmp(text,"set-utc ",8)==0) {
    unsigned year,month,day,hour,minute,second; char confirm[8]{};
    const int fields=std::sscanf(text,"set-utc %4u-%2u-%2uT%2u:%2u:%2uZ %7s %c",&year,&month,&day,&hour,&minute,&second,confirm,&extra);
    if (fields==7 && std::strcmp(confirm,"CONFIRM")==0 && year<=2199 && month<=12 && day<=31 &&
        hour<=23 && minute<=59 && second<=59 && rtc.set({static_cast<uint16_t>(year),static_cast<uint8_t>(month),
        static_cast<uint8_t>(day),static_cast<uint8_t>(hour),static_cast<uint8_t>(minute),static_cast<uint8_t>(second)}))
      serial.println("RTC_EXPLICIT_SET read back to validate (UTC)");
    else serial.println("REJECTED RTC_INVALID_OR_BUS_ERROR");
  } else if (M4_DIAGNOSTIC_MODE==6 && std::strncmp(text,"buzz ",5)==0) {
    const char* pattern=text+5;
    bool valid=std::strcmp(pattern,"confirm")==0 || std::strcmp(pattern,"warning")==0 || std::strcmp(pattern,"fault")==0;
    auto selected=std::strcmp(pattern,"confirm")==0 ? m4::BuzzerPattern::CONFIRMATION :
                  std::strcmp(pattern,"warning")==0 ? m4::BuzzerPattern::WARNING : m4::BuzzerPattern::FAULT;
    serial.println(valid && buzzer.start(selected,millis()) ? "BUZZER_SCHEDULED" : "CONFIGURATION_INVALID");
  } else serial.println("REJECTED UNKNOWN_DIAGNOSTIC_COMMAND; no actuator commands exist");
}
void serialCommands() {
  size_t processed=0;
  while (processed++<32 && protocolSerial().available()>0) {
    const char byte=static_cast<char>(protocolSerial().read());
    if (byte=='\n' || byte=='\r') {
      if (!discard_command && command_size) { command_buffer[command_size]=0; command(command_buffer); }
      command_size=0; discard_command=false;
    } else if (byte>=32 && byte<=126 && !discard_command) {
      if (command_size<sizeof(command_buffer)-1) command_buffer[command_size++]=byte;
      else { discard_command=true; command_size=0; }
    } else { discard_command=true; command_size=0; }
  }
}
}  // namespace

void setup() {
  protocolSerial().begin(115200);
  protocolSerial().printf("FORR_CAT M4 mode=%s HW_SAFE actuator=0 servo=0 pump=0 pins_reviewed=%u "
                          "NOT_HARDWARE_VERIFIED; ASCII diagnostics, NOT UART v1\r\n",m4::diagnosticName(),M4_PINS_REVIEWED);
  const auto loaded=calibration_store.load(calibration); copyCalibration();
  protocolSerial().printf("CALIBRATION_LOAD code=%u; missing/invalid=NOT_CALIBRATED\r\n",static_cast<unsigned>(loaded));
  const auto now=millis();
#if M4_DIAGNOSTIC_MODE == 1
  scale.begin({m4::diagnosticPin(M4_HX711_DOUT),m4::diagnosticPin(M4_HX711_SCK),500},now);
#elif M4_DIAGNOSTIC_MODE == 2 || M4_DIAGNOSTIC_MODE == 3 || M4_DIAGNOSTIC_MODE == 6
  bus.begin(m4::diagnosticPin(M4_I2C_SDA),m4::diagnosticPin(M4_I2C_SCL),25);
#if M4_DIAGNOSTIC_MODE == 2
  rtc.begin();
#elif M4_DIAGNOSTIC_MODE == 3
  scanner.start();
#else
  oled.begin(M4_OLED_ADDRESS,M4_OLED_HEIGHT);
  button.begin({m4::diagnosticPin(M4_BUTTON_PIN),static_cast<m4::Pull>(M4_BUTTON_PULL),M4_BUTTON_ACTIVE_LOW!=0,40,1000},now);
  buzzer.begin(m4::diagnosticPin(M4_BUZZER_PIN));
#endif
#elif M4_DIAGNOSTIC_MODE == 4
  food.distance.begin({m4::diagnosticPin(M4_FOOD_TRIG),m4::diagnosticPin(M4_FOOD_ECHO),
                       M4_ULTRASONIC_MIN_CM,M4_ULTRASONIC_MAX_CM,30000,0.0343f});
#elif M4_DIAGNOSTIC_MODE == 5
  water.distance.begin({m4::diagnosticPin(M4_WATER_TRIG),m4::diagnosticPin(M4_WATER_ECHO),
                        M4_ULTRASONIC_MIN_CM,M4_ULTRASONIC_MAX_CM,30000,0.0343f});
#endif
  servo.safeStop(); pump.off(); shadow_water.boot();
}
void loop() {
  const auto now=millis(); snapshot.sampled_at_ms=now;
#if M4_DIAGNOSTIC_MODE == 1
  scale.poll(now); snapshot.load_cell=scale.status; snapshot.raw_weight=scale.raw; snapshot.grams=scale.grams;
  if (average_action!=AverageAction::NONE && (scale.status.health==m4::Health::FAULT || scale.status.health==m4::Health::NOT_CONNECTED)) {
    average_action=AverageAction::NONE; protocolSerial().println("AVERAGE_ABORTED SENSOR_FAULT_OR_TIMEOUT");
  }
  if (scale.averaged.valid && scale.averaged.fresh && average_action!=AverageAction::NONE) {
    protocolSerial().printf("AVERAGE raw=%.6f\r\n",scale.averaged.value);
    if (average_action==AverageAction::TARE) protocolSerial().println(scale.tare() ? "TARE_CAPTURED factor remains NOT_CALIBRATED" : "TARE_INVALID");
    if (average_action==AverageAction::CALIBRATE) {
      bool ok=scale.calibrate(reference_mass);
      if (ok) protocolSerial().printf("CALIBRATION result=CALCULATED grams_per_count=%.12g NOT_HARDWARE_VERIFIED\r\n",scale.calibration.grams_per_count);
      else protocolSerial().println("CALIBRATION result=INVALID grams_per_count=null");
    }
    if (average_action==AverageAction::VALIDATE) {
      const auto measured=scale.calibration.grams(scale.averaged.value,now);
      const auto error=measured.valid ? m4::compareMass(measured.value,reference_mass) : m4::CalibrationError{};
      if (error.valid) protocolSerial().printf("VALIDATION measured=%.6f reference=%.6f absolute_error=%.6f relative_percent=%.6f PASS_TOLERANCE_NOT_ASSIGNED\r\n",measured.value,reference_mass,error.absolute_grams,error.relative_percent);
      else protocolSerial().println("VALIDATION NOT_CALIBRATED_OR_INVALID");
    }
    average_action=AverageAction::NONE;
    snapshot.load_cell=scale.status; snapshot.grams=scale.grams;
  }
#elif M4_DIAGNOSTIC_MODE == 2
  if (static_cast<uint32_t>(now-last_rtc)>=1000) { last_rtc=now; rtc.poll(now); }
  snapshot.rtc=rtc.status; snapshot.rtc_time=rtc.time;
#elif M4_DIAGNOSTIC_MODE == 3
  uint8_t address; bool found;
  if (scanner.tick(address,found) && found) protocolSerial().printf("I2C_ACK address=0x%02X identity NOT_VERIFIED\r\n",address);
#elif M4_DIAGNOSTIC_MODE == 4 || M4_DIAGNOSTIC_MODE == 5
  auto& selected=M4_DIAGNOSTIC_MODE==4 ? food : water;
  if (!selected.distance.busy() && static_cast<uint32_t>(now-last_measure)>=500) {
    last_measure=now; selected.distance.trigger(micros());
  }
  selected.distance.poll(micros(),now); selected.update();
  if (M4_DIAGNOSTIC_MODE==4) {
    snapshot.food=food.status; snapshot.food_distance_cm=food.distance.filtered; snapshot.food_percent=food.percent;
    snapshot.food_raw_distance_cm=food.distance.raw;
  } else {
    snapshot.water=water.status; snapshot.water_distance_cm=water.distance.filtered; snapshot.water_percent=water.percent;
    snapshot.water_raw_distance_cm=water.distance.raw;
    m4::tickShadowWater(shadow_water,snapshot);
    snapshot.water_state=shadow_water.state(); snapshot.would_request_pump=shadow_water.pumpRequested();
  }
  if (selected.distance.busy()) { yield(); return; } // avoid serial/report latency during edge capture
#elif M4_DIAGNOSTIC_MODE == 6
  if (button.poll(now)) protocolSerial().println("FEED_INTENT REJECTED SAFE_BUILD_ACTUATORS_DISABLED (no servo call)");
  buzzer.tick(now); oled.tick();
#endif
  if (static_cast<uint32_t>(now-last_report)>=1000) {
    last_report=now;
#if M4_DIAGNOSTIC_MODE == 6
    oled.statusLines(snapshot);
#endif
    report();
  }
  serialCommands();
  delay(1); // brief scheduler yield only; drivers have no long delay-based wait
}
#endif
