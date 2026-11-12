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
#include "m4/ds1302.h"
#include "m4/dual_level_sampler.h"
#if M4_QUAD_ULTRASONIC
#include "m4/quad_level_sampler.h"
#endif
#include "m4/ultrasonic.h"
#include "m4/accessories.h"
#include "m4/oled.h"
#include "m4/actuator_interfaces.h"
#include "m4/snapshot.h"

namespace {
m4::ArduinoPins pins_io;
m4::ArduinoI2C bus(pins_io);
m4::Hx711 scale(pins_io);
m4::Ds1302 rtc(pins_io);
m4::I2CScanner scanner(bus);
m4::LevelSensor approach(pins_io), water(pins_io);
m4::ManualButton button(pins_io);
m4::Buzzer buzzer(pins_io);
m4::Ssd1306 oled(bus);
m4::DisabledServo servo;
m4::DisabledPump pump;
safety::WaterController shadow_water;
m4::NvsCalibration calibration_store;
m4::CalibrationRecord calibration;
m4::SensorSnapshot snapshot;
#if M4_DIAGNOSTIC_MODE == 7
#if M4_QUAD_ULTRASONIC
m4::LevelSensor hc2(pins_io),jsn2(pins_io);
m4::QuadLevelSampler dual(approach,water,hc2,jsn2);
#else
m4::DualLevelSampler dual(approach,water); // generic channel FOOD slot now samples approach, never inventory
#endif
#endif
bool food_echo_ack=false,water_echo_ack=false,buzzer_ack=false,scanner_running=false;
bool pir_configured=false,pir_motion=false;
bool pir_transition_seen=false,weight_stability_configured=false;
uint32_t pir_transition_at=0,pir_transitions=0;
float weight_stability_max_range_g=0,weight_recent_values[4]{};
uint8_t weight_recent_count=0,weight_recent_next=0;
unsigned scan_probes=0,scan_found=0;
float food_min=M4_ULTRASONIC_MIN_CM,food_max=M4_ULTRASONIC_MAX_CM;
float water_min=M4_ULTRASONIC_MIN_CM,water_max=M4_ULTRASONIC_MAX_CM;

bool beginLevel(bool food_selected) {
  const m4::UltrasonicConfig config{
    m4::diagnosticPin(food_selected ? M4_APPROACH_TRIG : M4_WATER_TRIG),
    m4::diagnosticPin(food_selected ? M4_APPROACH_ECHO : M4_WATER_ECHO),
    food_selected ? food_min : water_min,food_selected ? food_max : water_max,30000,0.0343f};
#if M4_DIAGNOSTIC_MODE == 7
#if M4_QUAD_ULTRASONIC
  return dual.selectOnly(food_selected?0u:1u,config);
#else
  return dual.enable(food_selected ? m4::DualLevelSampler::Channel::FOOD : m4::DualLevelSampler::Channel::WATER,config);
#endif
#else
  return (food_selected ? approach : water).distance.begin(config);
#endif
}
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
#if M4_QUAD_ULTRASONIC
  // Preserve the existing two-channel bridge contract while channels are switched.
  food_echo_ack=dual.enabled(0);water_echo_ack=dual.enabled(1);
  snapshot.approach=approach.status;snapshot.water=water.status;
  snapshot.approach_distance_cm=food_echo_ack?approach.distance.filtered:m4::Reading<float>{};
  snapshot.approach_raw_distance_cm=food_echo_ack?approach.distance.raw:m4::Reading<float>{};
  snapshot.water_distance_cm=water_echo_ack?water.distance.filtered:m4::Reading<float>{};
  snapshot.water_raw_distance_cm=water_echo_ack?water.distance.raw:m4::Reading<float>{};
  serial.print("\"pin_mapping_status\":\"PROPOSED_NOT_PHYSICAL_VERIFIED\",\"ultrasonic4\":[");
  const m4::LevelSensor* channels[]={&approach,&water,&hc2,&jsn2};
  const char* ids[]={"hc_sr04_1","jsn_sr04t_1","hc_sr04_2","jsn_sr04t_2"};
  const char* types[]={"HC-SR04","JSN-SR04T","HC-SR04","JSN-SR04T"};
  const char* roles[]={"CAT_APPROACH","WATER_LEVEL","TBD","TBD"};
  const int triggers[]={12,14,16,18},echoes[]={13,15,17,10};
  for (unsigned i=0;i<4;++i) {
    const auto& distance=channels[i]->distance;
    const auto& reading=distance.filtered;
    const bool enabled=dual.enabled(i);
    const bool stale=enabled && reading.valid && static_cast<uint32_t>(snapshot.sampled_at_ms-reading.sampled_at_ms)>2000;
    const bool timeout=enabled && distance.status.reason==m4::Reason::TIMEOUT;
    const bool valid=enabled && !stale && reading.valid && distance.status.health==m4::Health::HEALTHY;
    const char* state=!enabled?"NOT_CONFIGURED":stale?"STALE":timeout?"TIMEOUT":valid?"HEALTHY":"UNKNOWN";
    if (i) serial.print(",");
    serial.printf("{\"sensor_id\":\"%s\",\"type\":\"%s\",\"role\":\"%s\",\"trigger_gpio\":%d,\"echo_gpio\":%d,\"wired\":null,\"physical_verification\":\"NOT_TESTED\",\"configured\":%s,\"enabled\":%s,\"valid\":%s,\"timeout\":%s,\"stale\":%s,\"state\":\"%s\",\"distance_cm\":",
      ids[i],types[i],roles[i],triggers[i],echoes[i],enabled?"true":"false",enabled?"true":"false",valid?"true":"false",timeout?"true":"false",stale?"true":"false",state);
    if (valid) serial.printf("%.4f",static_cast<double>(reading.value));else serial.print("null");
    serial.print(",\"age_seconds\":");
    if(enabled && reading.valid) serial.printf("%.3f",static_cast<double>(static_cast<uint32_t>(snapshot.sampled_at_ms-reading.sampled_at_ms))/1000);else serial.print("null");
    serial.printf(",\"timeout_count\":%lu}",static_cast<unsigned long>(distance.timeoutCount()));
  }
  serial.print("],");
#endif
  serial.printf("\"telemetry_schema_version\":2,\"hx711_installed\":%s,",M4_HX711_INSTALLED?"true":"false");
  serial.print("\"pin_contract\":\"2026-10-21\",\"distance_roles\":{\"channel_1\":\"APPROACH\",\"channel_2\":\"WATER_OPERATIONAL\"},");
  serial.printf("\"approach_echo_ack\":%s,\"motion_input_configured\":%s,\"motion\":",
                food_echo_ack?"true":"false",pir_configured?"true":"false");
  if (pir_configured) serial.print(pir_motion?"true":"false"); else serial.print("null");
  serial.printf(",\"approach_health\":\"%s\",\"approach_distance_cm\":",m4::name(snapshot.approach.health));
  number(snapshot.approach_distance_cm);
  serial.print(",\"food_reservoir_percent\":null,\"water_reservoir_percent\":null,");
  const bool weight_valid=M4_HX711_INSTALLED && snapshot.load_cell.health==m4::Health::HEALTHY &&
      m4::recent(snapshot.grams,snapshot.sampled_at_ms) && std::isfinite(snapshot.grams.value);
  const char* quality=!M4_HX711_INSTALLED?"NOT_INSTALLED":weight_valid?"VALID":
      snapshot.load_cell.health==m4::Health::NOT_CALIBRATED?"NOT_CALIBRATED":
      snapshot.load_cell.health==m4::Health::NOT_CONNECTED?"UNAVAILABLE":
      snapshot.grams.valid?"STALE":"INVALID";
  serial.printf("\"weight\":{\"installed\":%s,\"valid\":%s,\"quality\":\"%s\",\"value_grams\":",
                M4_HX711_INSTALLED?"true":"false",weight_valid?"true":"false",quality);
  if (weight_valid) serial.printf("%.6f",static_cast<double>(snapshot.grams.value)); else serial.print("null");
  serial.print(",\"sampled_at_ms\":");
  if (weight_valid) serial.printf("%lu",static_cast<unsigned long>(snapshot.grams.sampled_at_ms)); else serial.print("null");
  serial.print(",\"calibration_version\":1,\"calibration_id\":");
  if (scale.calibration.valid()) {
    uint8_t bytes[17]{}; bytes[0]=1; uint64_t bits;
    std::memcpy(&bits,&scale.calibration.tare_counts,8); m4::calibration_record::put(bytes+1,bits,8);
    std::memcpy(&bits,&scale.calibration.grams_per_count,8); m4::calibration_record::put(bytes+9,bits,8);
    serial.printf("\"hx-v1-%04x\"",uart_v1::crc16(bytes,sizeof(bytes)));
  } else serial.print("null");
  serial.print("},\"consumed_grams\":null,");
#if M4_CURRENT_HARDWARE_PROFILE
  serial.print("\"current_hardware\":{");
  serial.printf("\"rtc_detected\":%s,\"oled_address\":\"0x%02x\",\"oled_initialized\":%s,",
                snapshot.rtc.health==m4::Health::HEALTHY?"true":"false",
                M4_OLED_ADDRESS,oled.status.health==m4::Health::HEALTHY?"true":"false");
  serial.printf("\"pir_transition_count\":%lu,\"pir_last_transition_ms\":",
                static_cast<unsigned long>(pir_transitions));
  if (pir_transition_seen) serial.printf("%lu",static_cast<unsigned long>(pir_transition_at));
  else serial.print("null");
  serial.printf(",\"weight_calibrated\":%s,\"weight_stability_threshold_grams\":",
                scale.calibration.valid()?"true":"false");
  if (weight_stability_configured) serial.printf("%.6f",static_cast<double>(weight_stability_max_range_g));
  else serial.print("null");
  serial.printf(",\"weight_window_samples\":%u,\"weight_window_range_grams\":",
                static_cast<unsigned>(weight_recent_count));
  float smallest=0,largest=0;
  if (weight_recent_count==4) {
    smallest=largest=weight_recent_values[0];
    for (float value:weight_recent_values) {
      if (value<smallest) smallest=value;
      if (value>largest) largest=value;
    }
    serial.printf("%.6f",static_cast<double>(largest-smallest));
  } else serial.print("null");
  serial.print(",\"weight_stable\":");
  if (weight_stability_configured && weight_recent_count==4 &&
      snapshot.load_cell.health==m4::Health::HEALTHY && m4::recent(snapshot.grams,snapshot.sampled_at_ms))
    serial.print(largest-smallest<=weight_stability_max_range_g?"true":"false");
  else serial.print("null");
  serial.printf(",\"approach_timeout_count\":%lu,\"operational_water_timeout_count\":%lu,",
                static_cast<unsigned long>(approach.distance.timeoutCount()),
                static_cast<unsigned long>(water.distance.timeoutCount()));
  serial.printf("\"approach_distance_valid\":%s,\"operational_water_distance_valid\":%s,",
                snapshot.approach_distance_cm.valid?"true":"false",
                snapshot.water_distance_cm.valid?"true":"false");
  serial.print("\"servo_armed\":false,\"servo_state\":\"PWM_NOT_ATTACHED_CLOSE_PHYSICAL_UNVERIFIED\",");
  serial.print("\"pump_armed\":false,\"pump_state\":\"OUTPUT_NOT_ENABLED_PHYSICAL_OFF_UNVERIFIED\",");
  serial.print("\"auto_feed\":false,\"auto_water\":false,");
  serial.printf("\"button_raw_level\":%u,\"button_debounced_level\":%u,\"button_pressed\":%s,",
                button.raw_level?1u:0u,button.debounced_level?1u:0u,button.button_pressed?"true":"false");
  serial.printf("\"button_press_count\":%lu,\"manual_button_request_count\":%lu,\"button_last_press_ms\":",
                static_cast<unsigned long>(button.press_count),static_cast<unsigned long>(button.press_count));
  if (button.press_count) serial.printf("%lu",static_cast<unsigned long>(button.last_press_ms));
  else serial.print("null");
  serial.print(",\"button_gpio\":21,\"button_debounce_ms\":40,\"button_actuator_blocked\":true,");
  serial.print("\"food_reservoir_sensor\":\"NOT_WIRED\",\"water_reservoir_sensor\":\"NOT_WIRED\"},");
#endif
  serial.printf("\"food_echo_ack\":false,\"water_echo_ack\":%s,\"buzzer_driver_ack\":%s,",
                water_echo_ack ? "true":"false",buzzer_ack ? "true":"false");
  serial.printf("\"rtc_health\":\"%s\",\"rtc_epoch\":",m4::name(snapshot.rtc.health));
  if (snapshot.rtc_time.valid) serial.printf("%llu",static_cast<unsigned long long>(m4::epoch(snapshot.rtc_time.value)));
  else serial.print("null");
  serial.printf(",\"rtc_type\":\"%s\",\"rtc_reason\":\"%s\",\"rtc_utc\":",M4_QUAD_ULTRASONIC?"NONE":"DS1302",m4::name(snapshot.rtc.reason));
  if (snapshot.rtc_time.valid) {
    const auto& t=snapshot.rtc_time.value;
    serial.printf("\"%04u-%02u-%02uT%02u:%02u:%02uZ\"",t.year,t.month,t.day,t.hour,t.minute,t.second);
  } else serial.print("null");
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
  calibration.food={}; // inventory sensor #2 is TBD; approach has no percentage geometry
  scale.applyCalibration(calibration.hx711); approach.calibration={}; water.calibration=calibration.water;
  average_action=AverageAction::NONE;
  weight_recent_count=weight_recent_next=0;
  snapshot.load_cell=scale.status; snapshot.grams=scale.grams;
  approach.update(); water.update(); snapshot.approach=approach.status;
  snapshot.food={}; snapshot.food_percent={}; snapshot.food_distance_cm={}; snapshot.food_raw_distance_cm={};
  snapshot.water=water.status; snapshot.water_percent=water.percent;
  snapshot.water_percent.fresh=false; // recalculating geometry is not a new physical echo
#if M4_DIAGNOSTIC_MODE == 5 || M4_DIAGNOSTIC_MODE == 7
  m4::tickShadowWater(shadow_water,snapshot);
  snapshot.water_state=shadow_water.state(); snapshot.would_request_pump=shadow_water.pumpRequested();
#endif
}
void command(const char* text) {
  auto& serial=protocolSerial();
  unsigned count=0; double mass=0; float full=0,empty=0; char extra=0;
  if (std::strcmp(text,"help")==0) {
#if M4_QUAD_ULTRASONIC
    serial.println("QUAD DIAGNOSTIC ONLY: ultra-select hc1|jsn1|hc2|jsn2 CONFIRM; ultra-off CONFIRM; ultra-multiplex CONFIRM (all channels individually reviewed first). RTC DISABLED. NO ACTUATORS.");
  } else if (std::strcmp(text,"ultra-off CONFIRM")==0) {
    serial.println(dual.disableAll()?"ULTRA_OFF":"REJECTED ACQUISITION_BUSY");
  } else if (std::strcmp(text,"ultra-multiplex CONFIRM")==0) {
    serial.println(dual.selectAllReviewed()?"ULTRA_SEQUENTIAL_REVIEWED_80MS_QUIET":"REJECTED ALL_CHANNELS_MUST_BE_REVIEWED_OR_BUSY");
  } else if (std::strncmp(text,"ultra-select ",13)==0) {
    unsigned channel=4;
    if(std::strcmp(text,"ultra-select hc1 CONFIRM")==0)channel=0;
    if(std::strcmp(text,"ultra-select jsn1 CONFIRM")==0)channel=1;
    if(std::strcmp(text,"ultra-select hc2 CONFIRM")==0)channel=2;
    if(std::strcmp(text,"ultra-select jsn2 CONFIRM")==0)channel=3;
    const int trigs[]={12,14,16,18},echoes[]={13,15,17,10};
    const bool ok=channel<4 && dual.selectOnly(channel,{m4::diagnosticPin(trigs[channel]),m4::diagnosticPin(echoes[channel]),M4_ULTRASONIC_MIN_CM,M4_ULTRASONIC_MAX_CM,30000,0.0343f});
    serial.println(ok?"ULTRA_SINGLE_ACQUISITION_ENABLED_NOT_PHYSICAL_PASS":"REJECTED CHANNEL_OR_BUSY");
#else
    serial.println("M4 ASCII ONLY: status; avg N; tare N; cal GRAMS N; validate GRAMS N; "
                   "water-geometry FULL_CM EMPTY_CM; load; save YES; "
                    "scan; set-utc YYYY-MM-DDTHH:MM:SSZ CONFIRM; "
                     "echo-approach-3v3 CONFIRM; echo-water-3v3 CONFIRM; echo-3v3 CONFIRM; "
                     "approach-range MIN MAX; water-range MIN MAX; buzzer-driver ACTIVE_HIGH CONFIRM; "
                     "buzz confirm|warning|fault. NO FEED/SERVO/PUMP commands.");
#endif
  } else if (std::strcmp(text,"status")==0) { report();
#if M4_CURRENT_HARDWARE_PROFILE
  } else if (std::strncmp(text,"weight-stability ",17)==0) {
    char confirm[8]{};
    const int fields=std::sscanf(text,"weight-stability %f %7s %c",&full,confirm,&extra);
    if (fields==2 && std::strcmp(confirm,"CONFIRM")==0 &&
        std::isfinite(full) && full>0 && full<=10) {
      weight_stability_max_range_g=full;weight_stability_configured=true;
      weight_recent_count=weight_recent_next=0;
      serial.println("WEIGHT_STABILITY_RANGE_SET for 4 fresh grams; NOT physical tolerance PASS");
    } else serial.println("REJECTED WEIGHT_STABILITY_INVALID");
#endif
  } else if ((M4_DIAGNOSTIC_MODE==1 || M4_DIAGNOSTIC_MODE==7) && std::sscanf(text,"avg %2u %c",&count,&extra)==1) {
    if (count>=1 && count<=64 && scale.startAverage(count)) average_action=AverageAction::RAW;
    else serial.println("REJECTED CONFIGURATION_INVALID");
  } else if ((M4_DIAGNOSTIC_MODE==1 || M4_DIAGNOSTIC_MODE==7) && std::sscanf(text,"tare %2u %c",&count,&extra)==1) {
    if (count>=1 && count<=64 && scale.startAverage(count)) average_action=AverageAction::TARE;
    else serial.println("REJECTED CONFIGURATION_INVALID");
  } else if ((M4_DIAGNOSTIC_MODE==1 || M4_DIAGNOSTIC_MODE==7) && std::sscanf(text,"cal %lf %2u %c",&mass,&count,&extra)==2) {
    if (std::isfinite(mass) && mass>0 && count>=1 && count<=64 && scale.startAverage(count)) {
      reference_mass=mass; average_action=AverageAction::CALIBRATE;
    } else serial.println("REJECTED INVALID_CALIBRATION");
  } else if ((M4_DIAGNOSTIC_MODE==1 || M4_DIAGNOSTIC_MODE==7) && std::sscanf(text,"validate %lf %2u %c",&mass,&count,&extra)==2) {
    if (std::isfinite(mass) && mass>0 && count>=1 && count<=64 && scale.startAverage(count)) {
      reference_mass=mass; average_action=AverageAction::VALIDATE;
    } else serial.println("REJECTED INVALID_REFERENCE");
  } else if (std::strncmp(text,"food-geometry",13)==0 || std::strncmp(text,"echo-food-",10)==0 || std::strncmp(text,"food-range",10)==0) {
    serial.println("REJECTED LEGACY_FOOD_CHANNEL; HC-SR04 #1 is APPROACH, inventory #2 GPIO TBD");
  } else if ((M4_DIAGNOSTIC_MODE==5 || M4_DIAGNOSTIC_MODE==7) && std::sscanf(text,"water-geometry %f %f %c",&full,&empty,&extra)==2) {
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
    scanner_running=scanner.start(); scan_probes=scan_found=0;
    serial.println(scanner_running ? "I2C_SCAN_STARTED" : "CONFIGURATION_INVALID no I2C touched");
  } else if (M4_SENSOR_BRINGUP && (M4_DIAGNOSTIC_MODE==4 || M4_DIAGNOSTIC_MODE==7) &&
              (std::strcmp(text,"echo-approach-3v3 CONFIRM")==0 || (M4_DIAGNOSTIC_MODE==4 && std::strcmp(text,"echo-3v3 CONFIRM")==0))) {
    food_echo_ack=beginLevel(true);
     serial.println(food_echo_ack ? "APPROACH_ECHO_REVIEW_ACK acquisition enabled, not measured voltage PASS" : "REJECTED CONFIGURATION_INVALID");
  } else if (M4_SENSOR_BRINGUP && (M4_DIAGNOSTIC_MODE==5 || M4_DIAGNOSTIC_MODE==7) &&
             (std::strcmp(text,"echo-water-3v3 CONFIRM")==0 || (M4_DIAGNOSTIC_MODE==5 && std::strcmp(text,"echo-3v3 CONFIRM")==0))) {
    water_echo_ack=beginLevel(false);
    serial.println(water_echo_ack ? "WATER_ECHO_REVIEW_ACK acquisition enabled, not measured voltage PASS" : "REJECTED CONFIGURATION_INVALID");
   } else if ((M4_DIAGNOSTIC_MODE==4 || M4_DIAGNOSTIC_MODE==7) && std::sscanf(text,"approach-range %f %f %c",&full,&empty,&extra)==2) {
    if (std::isfinite(full) && std::isfinite(empty) && full>0 && empty>full && empty<=400) {
      food_min=full; food_max=empty; if (food_echo_ack) food_echo_ack=beginLevel(true);
       serial.println("APPROACH_RANGE_CONFIGURED not a calibrated near threshold");
    } else serial.println("REJECTED RANGE_INVALID");
  } else if ((M4_DIAGNOSTIC_MODE==5 || M4_DIAGNOSTIC_MODE==7) && std::sscanf(text,"water-range %f %f %c",&full,&empty,&extra)==2) {
    if (std::isfinite(full) && std::isfinite(empty) && full>0 && empty>full && empty<=400) {
      water_min=full; water_max=empty; if (water_echo_ack) water_echo_ack=beginLevel(false);
      serial.println("WATER_RANGE_CONFIGURED not physical calibration PASS");
    } else serial.println("REJECTED RANGE_INVALID");
  } else if ((M4_DIAGNOSTIC_MODE==6 || M4_DIAGNOSTIC_MODE==7) && M4_SENSOR_BRINGUP && std::strcmp(text,"buzzer-driver ACTIVE_HIGH CONFIRM")==0) {
    buzzer_ack=buzzer.begin(m4::diagnosticPin(M4_BUZZER_PIN),true);
    serial.println(buzzer_ack ? "BUZZER_DRIVER_ACKNOWLEDGED no sound until buzz command" : "REJECTED CONFIGURATION_INVALID");
  } else if (!M4_QUAD_ULTRASONIC && (M4_DIAGNOSTIC_MODE==2 || M4_DIAGNOSTIC_MODE==7) && std::strncmp(text,"set-utc ",8)==0) {
    unsigned year,month,day,hour,minute,second; char confirm[8]{};
    const int fields=std::sscanf(text,"set-utc %4u-%2u-%2uT%2u:%2u:%2uZ %7s %c",&year,&month,&day,&hour,&minute,&second,confirm,&extra);
    if (fields==7 && std::strcmp(confirm,"CONFIRM")==0 && year<=2199 && month<=12 && day<=31 &&
        hour<=23 && minute<=59 && second<=59 && rtc.set({static_cast<uint16_t>(year),static_cast<uint8_t>(month),
        static_cast<uint8_t>(day),static_cast<uint8_t>(hour),static_cast<uint8_t>(minute),static_cast<uint8_t>(second)},millis()))
      serial.println("RTC_DS1302_EXPLICIT_SET READBACK_VALID UTC; original write protect restored");
    else serial.println("REJECTED RTC_INVALID_OR_BUS_ERROR");
    snapshot.rtc=rtc.status; snapshot.rtc_time=rtc.time;
  } else if ((M4_DIAGNOSTIC_MODE==6 || M4_DIAGNOSTIC_MODE==7) && std::strncmp(text,"buzz ",5)==0) {
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
  if (M4_HX711_INSTALLED) scale.begin({m4::diagnosticPin(M4_HX711_DOUT),m4::diagnosticPin(M4_HX711_SCK),500},now);
#elif M4_DIAGNOSTIC_MODE == 2
  rtc.begin({m4::diagnosticPin(M4_RTC_CLK),m4::diagnosticPin(M4_RTC_DAT),m4::diagnosticPin(M4_RTC_CE)});
  rtc.poll(now); snapshot.rtc=rtc.status; snapshot.rtc_time=rtc.time;
#elif M4_DIAGNOSTIC_MODE == 3 || M4_DIAGNOSTIC_MODE == 6
  bus.begin(m4::diagnosticPin(M4_I2C_SDA),m4::diagnosticPin(M4_I2C_SCL),25);
#if M4_DIAGNOSTIC_MODE == 3
  scanner_running=scanner.start();
#else
  oled.begin(M4_OLED_ADDRESS,M4_OLED_HEIGHT);
  button.begin({m4::diagnosticPin(M4_BUTTON_PIN),static_cast<m4::Pull>(M4_BUTTON_PULL),M4_BUTTON_ACTIVE_LOW!=0,40,1000},now);
  if (!M4_SENSOR_BRINGUP) buzzer.begin(m4::diagnosticPin(M4_BUZZER_PIN));
#endif
#elif M4_DIAGNOSTIC_MODE == 4
  if (!M4_SENSOR_BRINGUP) beginLevel(true);
#elif M4_DIAGNOSTIC_MODE == 5
  if (!M4_SENSOR_BRINGUP) beginLevel(false);
#elif M4_DIAGNOSTIC_MODE == 7
  if (M4_HX711_INSTALLED) scale.begin({m4::diagnosticPin(M4_HX711_DOUT),m4::diagnosticPin(M4_HX711_SCK),500},now);
#if !M4_QUAD_ULTRASONIC
  rtc.begin({m4::diagnosticPin(M4_RTC_CLK),m4::diagnosticPin(M4_RTC_DAT),m4::diagnosticPin(M4_RTC_CE)});
  rtc.poll(now); snapshot.rtc=rtc.status; snapshot.rtc_time=rtc.time;
#endif
  bus.begin(m4::diagnosticPin(M4_I2C_SDA),m4::diagnosticPin(M4_I2C_SCL),25);
  oled.begin(M4_OLED_ADDRESS,M4_OLED_HEIGHT);
  button.begin({m4::diagnosticPin(M4_BUTTON_PIN),static_cast<m4::Pull>(M4_BUTTON_PULL),M4_BUTTON_ACTIVE_LOW!=0,40,1000,M4_CURRENT_HARDWARE_PROFILE!=0},now);
   pir_configured=m4::inputValid(pins_io,m4::diagnosticPin(M4_PIR_PIN));
   if (pir_configured) {
     pins_io.input(M4_PIR_PIN,m4::Pull::NONE);
     pir_motion=pins_io.read(M4_PIR_PIN); // boot level is not a transition
   }
#if M4_QUAD_ULTRASONIC
    protocolSerial().println("PROPOSED 2026-10-27: HX4/5 OLED8/9 PIR11 BUTTON21 HC1 12/13 JSN1 14/15 HC2 16/17 JSN2 18/10. RTC OFF. ECHO REVIEW REQUIRED PER CHANNEL; ALL OFF AT BOOT. SERVO6/PUMP7 UNTOUCHED.");
#else
    protocolSerial().println("CURRENT 2026-10-21: HX4/5 OLED8/9 PIR11 APPROACH12/13 WATER_OPERATIONAL14/15 RTC16/17/18. ECHO13/15 <=3.3V: echo-approach-3v3 / echo-water-3v3 CONFIRM. SERVO6/PUMP7 UNTOUCHED. INVENTORY SENSORS TBD. NO ACTUATORS.");
#endif
#endif
  servo.safeStop(); pump.off(); shadow_water.boot();
}
void loop() {
  const auto now=millis(); snapshot.sampled_at_ms=now;
#if M4_DIAGNOSTIC_MODE == 7
  if (dual.poll(micros(),now)) { yield(); return; }
#endif
#if M4_DIAGNOSTIC_MODE == 1 || M4_DIAGNOSTIC_MODE == 7
  scale.poll(now); snapshot.load_cell=scale.status; snapshot.raw_weight=scale.raw; snapshot.grams=scale.grams;
#if M4_CURRENT_HARDWARE_PROFILE
  if (snapshot.load_cell.health!=m4::Health::HEALTHY || !snapshot.grams.valid) {
    weight_recent_count=weight_recent_next=0;
  } else if (snapshot.grams.fresh) {
    weight_recent_values[weight_recent_next]=snapshot.grams.value;
    weight_recent_next=static_cast<uint8_t>((weight_recent_next+1)%4);
    if (weight_recent_count<4) ++weight_recent_count;
  }
#endif
  if (average_action!=AverageAction::NONE && (scale.status.health==m4::Health::FAULT || scale.status.health==m4::Health::NOT_CONNECTED)) {
    average_action=AverageAction::NONE; protocolSerial().println("AVERAGE_ABORTED SENSOR_FAULT_OR_TIMEOUT");
  }
  if (scale.averaged.valid && scale.averaged.fresh && average_action!=AverageAction::NONE) {
    protocolSerial().printf("AVERAGE raw=%.6f\r\n",scale.averaged.value);
    if (average_action==AverageAction::TARE) {
      const bool ok=scale.tare();
      if (ok) calibration.hx711=scale.calibration;
      protocolSerial().println(ok ? "TARE_CAPTURED factor remains NOT_CALIBRATED" : "TARE_INVALID");
    }
    if (average_action==AverageAction::CALIBRATE) {
      bool ok=scale.calibrate(reference_mass);
      if (ok) calibration.hx711=scale.calibration;
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
  if (scanner_running) {
    if (scanner.tick(address,found)) {
      ++scan_probes;
      if (found) { ++scan_found; protocolSerial().printf("I2C_ACK address=0x%02X identity NOT_VERIFIED\r\n",address); }
    } else {
      scanner_running=false;
      protocolSerial().printf("I2C_SCAN_COMPLETE probes=%u responding=%u (ACK is not module identity)\r\n",scan_probes,scan_found);
    }
  }
#elif M4_DIAGNOSTIC_MODE == 4 || M4_DIAGNOSTIC_MODE == 5
   auto& selected=M4_DIAGNOSTIC_MODE==4 ? approach : water;
  if (!selected.distance.busy() && static_cast<uint32_t>(now-last_measure)>=500) {
    last_measure=now; selected.distance.trigger(micros());
  }
  selected.distance.poll(micros(),now); selected.update();
  if (M4_DIAGNOSTIC_MODE==4) {
     snapshot.approach=approach.status; snapshot.approach_distance_cm=approach.distance.filtered;
     snapshot.approach_raw_distance_cm=approach.distance.raw;
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
#if M4_DIAGNOSTIC_MODE == 7
#if !M4_QUAD_ULTRASONIC
  if (static_cast<uint32_t>(now-last_rtc)>=1000) { last_rtc=now; rtc.poll(now); }
  snapshot.rtc=rtc.status; snapshot.rtc_time=rtc.time;
#endif
   snapshot.approach=approach.status; snapshot.approach_distance_cm=approach.distance.filtered;
   snapshot.approach_raw_distance_cm=approach.distance.raw;
   if (pir_configured) {
     const bool observed=pins_io.read(M4_PIR_PIN);
     if (observed!=pir_motion) {
       pir_motion=observed;pir_transition_at=now;pir_transition_seen=true;
       if (pir_transitions!=UINT32_MAX) ++pir_transitions;
     }
   }
  snapshot.water=water.status; snapshot.water_distance_cm=water.distance.filtered;
  snapshot.water_raw_distance_cm=water.distance.raw; snapshot.water_percent=water.percent;
  m4::tickShadowWater(shadow_water,snapshot);
   snapshot.water_state=shadow_water.state(); snapshot.would_request_pump=shadow_water.pumpRequested();
   if (button.poll(now)) {
#if M4_CURRENT_HARDWARE_PROFILE
     protocolSerial().printf("MANUAL_BUTTON_FEED_REQUEST count=%lu monotonic_ms=%lu actuator_blocked=true\r\n",
                             static_cast<unsigned long>(button.press_count),static_cast<unsigned long>(button.last_press_ms));
#else
     protocolSerial().println("FEED_INTENT REJECTED SAFE_BUILD_ACTUATORS_DISABLED (no servo call)");
#endif
   }
  buzzer.tick(now); oled.tick();
#endif
  if (static_cast<uint32_t>(now-last_report)>=1000) {
    last_report=now;
#if M4_DIAGNOSTIC_MODE == 6 || M4_DIAGNOSTIC_MODE == 7
    oled.statusLines(snapshot);
#endif
    report();
  }
  serialCommands();
  delay(1); // brief scheduler yield only; drivers have no long delay-based wait
#if M4_DIAGNOSTIC_MODE == 7
  // Start only AFTER serial/RTC/HX711/OLED work and scheduler yield are complete.
  dual.start(micros(),millis());
#endif
}
#endif
