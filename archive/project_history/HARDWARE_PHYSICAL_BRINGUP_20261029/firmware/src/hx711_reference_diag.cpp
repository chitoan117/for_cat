#include <Arduino.h>
#include "m4/diagnostic_config.h"
#if defined(M4_HX711_REFERENCE_DIAG) && M4_HX711_REFERENCE_DIAG
#include <Arduino.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "serial_port.h"
#include "m4/arduino_io.h"
#include "m4/hx711.h"
#if defined(M4_HX711_INOX) && M4_HX711_INOX
#include "m4/inox_mount_binding.h"
#ifndef INOX_TEST_BOOT_NONCE
#include <esp_system.h>
#endif
#endif

static_assert(M4_HX711_DOUT==4 && M4_HX711_SCK==5,"Owner HX711 pin authority");
static_assert(ACTUATOR_OUTPUTS_ENABLED==0 && SERVO_DIAGNOSTIC_ENABLED==0 && PUMP_DIAGNOSTIC_ENABLED==0,
              "HX711-only diagnostic; actuators LOCKED");
namespace hx_reference_diag {
m4::ArduinoPins pins_io;
m4::Hx711 scale(pins_io);
m4::NvsCalibration store;
m4::CalibrationRecord stored;
const char* calibration_source="NONE";
bool tare_pending=false;
uint32_t last_report=0;
char buffer[96]{};
size_t used=0;
bool discard=false;
#if defined(M4_HX711_INOX) && M4_HX711_INOX
char current_mount[m4::inox_mount::ID_SIZE+1]{};
bool mount_match=false,fresh_import=false;
uint32_t inox_boot_nonce=0;
m4::CalibrationLoad stored_state=m4::CalibrationLoad::MISSING;
bool bindingMatches(const char* id,const m4::ScaleCalibration& c){
  Preferences p;if(!p.begin("m4-calibration",true))return false;
  uint8_t bytes[m4::inox_mount::SIZE];const bool read=p.getBytesLength("hx-mount-v1")==sizeof(bytes)&&p.getBytes("hx-mount-v1",bytes,sizeof(bytes))==sizeof(bytes);
  p.end();return read&&m4::inox_mount::matches(bytes,id,c);
}
bool saveBinding(){
  uint8_t bytes[m4::inox_mount::SIZE];if(!m4::inox_mount::encode(current_mount,scale.calibration,bytes))return false;
  Preferences p;if(!p.begin("m4-calibration",false))return false;
  const bool ok=p.putBytes("hx-mount-v1",bytes,sizeof(bytes))==sizeof(bytes);p.end();
  return ok&&bindingMatches(current_mount,scale.calibration);
}
#endif

template<class T> void number(const m4::Reading<T>& r) {
  if (r.valid) protocolSerial().printf("%.6f",static_cast<double>(r.value));
  else protocolSerial().print("null");
}
void report(uint32_t now,bool full=true) {
  auto& s=protocolSerial();
  if (!full) {
    // Fit comfortably within UART0 115200 even at 80 SPS / 3: do not block
    // acquisition with a full calibration/status object on every triplet.
    s.printf("{\"mode\":\"HX711_REFERENCE\",\"monotonic_ms\":%lu,\"raw\":",static_cast<unsigned long>(now)); number(scale.raw);
    s.print(",\"median_raw\":"); number(scale.median_raw);
    s.print(",\"measurement_grams\":"); number(scale.signed_grams);
    s.print(",\"display_grams\":"); number(scale.display_grams);
    s.printf(",\"valid\":%s}\r\n",scale.signed_grams.valid?"true":"false");
    if (scale.display_grams.valid) s.printf("KHOI LUONG = %.2f g\r\n",static_cast<double>(scale.display_grams.value));
    else s.println("KHOI LUONG = INVALID (not 0g)");
    return;
  }
  s.printf("{\"mode\":\"HX711_REFERENCE\",\"monotonic_ms\":%lu,\"physical_result\":\"NOT_TESTED\","
           "\"calibration_source\":\"%s\",\"nvs_key\":\"%s\",\"offset\":",static_cast<unsigned long>(now),calibration_source,m4::NvsCalibration::key());
  if (scale.calibration.tared) s.printf("%.9f",scale.calibration.tare_counts); else s.print("null");
  s.print(",\"scale_factor_counts_per_gram\":");
  if (scale.calibration.valid()) s.printf("%.9f",1.0/scale.calibration.grams_per_count); else s.print("null");
  s.printf(",\"health\":\"%s\",\"reason\":\"%s\",\"raw\":",m4::name(scale.status.health),m4::name(scale.status.reason));
  number(scale.raw); s.print(",\"median_raw\":"); number(scale.median_raw);
  s.print(",\"measurement_grams\":"); number(scale.signed_grams);
  s.print(",\"display_grams\":"); number(scale.display_grams);
  s.print(",\"valid\":"); s.print(scale.signed_grams.valid ? "true":"false");
  s.print(",\"sample_age_ms\":");
  if (scale.signed_grams.valid) s.printf("%lu",static_cast<unsigned long>(now-scale.signed_grams.sampled_at_ms)); else s.print("null");
  s.printf(",\"tare_pending\":%s,\"auto_tare\":false,\"servo_locked\":true,\"pump_locked\":true,\"actuator_outputs_enabled\":0",tare_pending?"true":"false");
#if defined(M4_HX711_INOX) && M4_HX711_INOX
  s.printf(",\"profile\":\"INOX_GROSS_DIAGNOSTIC\",\"mount_id\":\"%s\",\"boot_nonce\":%lu,\"mount_binding_match\":%s,\"fresh_operator_calibration\":%s,\"physical_validated\":false,\"tare_allowed\":false,\"gross_origin\":\"CALIBRATED_SCALE_ORIGIN_NOT_ASSUMED_BOWL_MASS\"",current_mount,static_cast<unsigned long>(inox_boot_nonce),mount_match?"true":"false",fresh_import?"true":"false");
#endif
  s.println("}");
  if (scale.display_grams.valid) s.printf("KHOI LUONG = %.2f g\r\n",static_cast<double>(scale.display_grams.value));
  else s.println("KHOI LUONG = INVALID (not 0g)");
}
void load() {
  const auto state=store.load(stored);
#if defined(M4_HX711_INOX) && M4_HX711_INOX
  stored_state=state;fresh_import=false;
  mount_match=current_mount[0]&&state==m4::CalibrationLoad::LOADED&&bindingMatches(current_mount,stored.hx711);
  scale.applyCalibration(mount_match?stored.hx711:m4::ScaleCalibration{});
  calibration_source=mount_match?"ESP32_NVS_CURRENT_MOUNT_PENDING":"NONE";
#else
  scale.applyCalibration(stored.hx711);
  calibration_source=state==m4::CalibrationLoad::LOADED && stored.hx711.valid()?"ESP32_NVS":"NONE";
#endif
  tare_pending=false;
  protocolSerial().printf("CALIBRATION_LOAD code=%u SOURCE=%s NO_TARE NO_WRITE\r\n",static_cast<unsigned>(state),calibration_source);
}
void command(const char* text) {
  auto& s=protocolSerial();
#if defined(M4_HX711_INOX) && M4_HX711_INOX
  char mount[m4::inox_mount::ID_SIZE+1]{},confirm[8]{},extra=0;
  if(std::strncmp(text,"mount ",6)==0){
    if(std::sscanf(text,"mount %40s %7s %c",mount,confirm,&extra)!=2||std::strcmp(confirm,"CONFIRM")||!m4::inox_mount::validId(mount)){s.println("REJECTED_MOUNT_ID");return;}
    std::strcpy(current_mount,mount);load();s.println("MOUNT_DECLARED_NO_TARE_NO_NVS_WRITE");return;
  }
  if(std::strncmp(text,"cal-save ",9)==0){
    if(std::sscanf(text,"cal-save %40s %7s %c",mount,confirm,&extra)!=2||std::strcmp(confirm,"CONFIRM")||
       std::strcmp(mount,current_mount)||!current_mount[0]||!fresh_import||!scale.calibration.valid()||stored_state==m4::CalibrationLoad::INVALID){s.println("REJECTED_CAL_SAVE_CURRENT_MOUNT_FRESH_IMPORT_REQUIRED");return;}
    m4::CalibrationRecord next=stored;next.hx711=scale.calibration;
    if(!store.save(next)||!saveBinding()){mount_match=false;s.println("CAL_SAVE_ERROR_BINDING_NOT_TRUSTED");return;}
    m4::CalibrationRecord got;const auto state=store.load(got);
    mount_match=state==m4::CalibrationLoad::LOADED&&bindingMatches(current_mount,got.hx711);
    if(mount_match){stored=got;stored_state=state;calibration_source="ESP32_NVS_CURRENT_MOUNT_PENDING";}
    s.println(mount_match?"CAL_SAVED_READBACK_OK_PHYSICAL_VALIDATION_STILL_PENDING":"CAL_SAVE_ERROR_READBACK");return;
  }
  if(std::strcmp(text,"reference CONFIRM")==0){s.println("REJECTED_HISTORICAL_REFERENCE_NEW_MOUNT_REQUIRES_FRESH_CALIBRATION");return;}
  if(std::strcmp(text,"t")==0||std::strcmp(text,"T")==0){s.println("REJECTED_INOX_NO_TARE_USE_GROSS_BASELINE");return;}
#endif
  if (std::strcmp(text,"help")==0) {
#if defined(M4_HX711_INOX) && M4_HX711_INOX
    s.println("INOX: status; mount MOUNT_ID CONFIRM; load; esp32-cal NEW_OFFSET NEW_COUNTS_PER_G CONFIRM; cal-save MOUNT_ID CONFIRM. NO TARE, NO HISTORICAL FALLBACK, NO ACTUATORS.");
#else
    s.println("status; load; reference CONFIRM; esp32-cal OFFSET COUNTS_PER_GRAM CONFIRM; t (empty only, 15 raw, RAM only)");
    s.println("No cal/refit/save/actuator commands. Boot uses ESP32 NVS sensors-v2. reference is DIAGNOSTIC_ONLY.");
#endif
  } else if (std::strcmp(text,"status")==0) report(millis());
  else if (std::strcmp(text,"load")==0) load();
  else if (std::strcmp(text,"reference CONFIRM")==0) {
    scale.applyCalibration({true,true,-668483.0,1.0/-1064.4473});
    calibration_source="ARDUINO_REFERENCE_RAM_ONLY"; tare_pending=false;
    s.println("REFERENCE_ONLY offset=-668483 scale=-1064.4473 NOT_ESP32_PHYSICAL_CALIBRATION NO_WRITE");
  } else if (std::strncmp(text,"esp32-cal ",10)==0) {
#if defined(M4_HX711_INOX) && M4_HX711_INOX
    if(!current_mount[0]){s.println("REJECTED_DECLARE_CURRENT_MOUNT_FIRST");return;}
#endif
    double offset=0,factor=0; char confirm[8]{},extra=0;
    const int count=std::sscanf(text,"esp32-cal %lf %lf %7s %c",&offset,&factor,confirm,&extra);
    m4::ScaleCalibration next{true,true,offset,1.0};
    if (count==3 && std::strcmp(confirm,"CONFIRM")==0 && std::isfinite(factor) && factor!=0) {
      next.grams_per_count=1.0/factor;
      if (next.valid()) {
        scale.applyCalibration(next); calibration_source="OPERATOR_ESP32_RAM_ONLY"; tare_pending=false;
#if defined(M4_HX711_INOX) && M4_HX711_INOX
        fresh_import=true;mount_match=false;
#endif
        s.println("OPERATOR_CALIBRATION_LOADED NO_REFIT NO_WRITE NOT_PHYSICAL_PASS"); return;
      }
    }
    s.println("REJECTED INVALID_CALIBRATION");
  } else if (std::strcmp(text,"t")==0 || std::strcmp(text,"T")==0) {
    if (tare_pending || !scale.calibration.valid() || !scale.startAverage(15)) s.println("TARE_REJECTED busy_or_no_valid_scale_factor");
    else { tare_pending=true; s.println("EXPLICIT_EMPTY_TARE_STARTED 15 raw; slope unchanged; RAM_ONLY"); }
  } else s.println("REJECTED UNKNOWN_HX711_COMMAND");
}
void serialCommands() {
  for (unsigned count=0;count<32 && protocolSerial().available();++count) {
    const char c=static_cast<char>(protocolSerial().read());
    if (c=='\r' || c=='\n') {
      if (!discard && used) { buffer[used]=0; command(buffer); }
      used=0; discard=false;
    } else if (c>=32 && c<=126 && !discard) {
      if (used<sizeof(buffer)-1) buffer[used++]=c;
      else { used=0; discard=true; }
    } else { used=0; discard=true; }
  }
}
}  // namespace hx_reference_diag

void setup() {
  using namespace hx_reference_diag;
#if defined(M4_HX711_INOX) && M4_HX711_INOX
  current_mount[0]=0;mount_match=fresh_import=false;
#ifdef INOX_TEST_BOOT_NONCE
  inox_boot_nonce=INOX_TEST_BOOT_NONCE;
#else
  const auto nonce=esp_random();inox_boot_nonce=nonce?nonce:1;
#endif
#endif
  protocolSerial().begin(115200);
  protocolSerial().println("PHYSICAL_VALIDATED_ARDUINO_HX711_REFERENCE PORT; ESP32_PHYSICAL=NOT_TESTED; DOUT4 SCK5 A128; board supply owner=5V; SERVO/PUMP LOCKED");
  load();
  scale.begin({m4::diagnosticPin(4),m4::diagnosticPin(5),500},millis());
#if defined(M4_HX711_INOX) && M4_HX711_INOX
  protocolSerial().println("INOX BOWL STAYS ON SCALE: declare CURRENT mount; RAW baseline30s; bowl+5/10/20/35/38g with returns. NO TARE. New mounting requires fresh coefficients; explicit persistence never marks PHYSICAL_PASS.");
#else
  protocolSerial().println("TEST: empty before tare; t ONCE if appropriate; 0/5/0/10/0/20/0/35/0/38/0. Do not tare between weights. Enter help.");
#endif
}
void loop() {
  using namespace hx_reference_diag;
  const auto now=millis();
  scale.poll(now);
  if (tare_pending && (scale.status.health==m4::Health::FAULT || scale.status.health==m4::Health::NOT_CONNECTED)) {
    tare_pending=false; protocolSerial().println("TARE_ABORTED sensor_fault_or_timeout; OFFSET_UNCHANGED");
  }
  if (tare_pending && scale.averaged.valid && scale.averaged.fresh) {
    const bool ok=scale.tarePreservingFactor(); tare_pending=false;
    if (ok) {
      calibration_source="EXPLICIT_TARE_RAM_ONLY";
      protocolSerial().printf("TARE_OK OFFSET=%.9f scale_factor=%.9f NO_REFIT NO_WRITE\r\n",scale.calibration.tare_counts,1.0/scale.calibration.grams_per_count);
    } else protocolSerial().println("TARE_ERROR OFFSET_UNCHANGED");
  }
  // One output for each completed triplet (about 300ms at 10 SPS), plus a
  // heartbeat during missing/invalid data. Never print old values as fresh.
  if (scale.median_raw.fresh || static_cast<uint32_t>(now-last_report)>=500) {
    report(now,!scale.median_raw.fresh); last_report=now;
  }
  serialCommands(); delay(1);
}
#endif
