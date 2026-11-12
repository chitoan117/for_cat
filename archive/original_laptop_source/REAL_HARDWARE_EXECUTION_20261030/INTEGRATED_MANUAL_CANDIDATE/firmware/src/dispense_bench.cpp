#include <Arduino.h>
#include <Preferences.h>
#include <cmath>
#include <cstdio>
#include <cstring>
#include "board_config.h"
#include "current_hardware.h"
#include "serial_port.h"
#include "m4/arduino_io.h"
#include "m4/hx711.h"
#include "m4/ledc_servo.h"
#include "m4/dispense_bench.h"
#include "uart_v1.h"

#if DISPENSE_BENCH_MODE
static_assert(current_hardware::HX711_DOUT==4 && current_hardware::HX711_SCK==5 &&
              current_hardware::SERVO_SIGNAL==6 && current_hardware::PUMP_CONTROL==7,
              "Current food-only GPIO contract");
namespace {
enum class RecordState { MISSING, INVALID, READY, PENDING };
class BenchJournal final : public m4::dispense_bench::Journal {
 public:
  RecordState load(uint32_t& id) {
    id=0;
    Preferences prefs;
    if (!prefs.begin("dispense-bench",true)) return RecordState::MISSING;
    if (!prefs.isKey("state-v1")) { prefs.end(); return RecordState::MISSING; }
    uint8_t bytes[7]{};
    const bool ok=prefs.getBytesLength("state-v1")==sizeof(bytes) &&
                  prefs.getBytes("state-v1",bytes,sizeof(bytes))==sizeof(bytes);
    prefs.end();
    if (!ok || bytes[0]!=1 || bytes[1]>1 ||
        uart_v1::crc16(bytes,5)!=(static_cast<uint16_t>(bytes[5]) |
                               static_cast<uint16_t>(bytes[6])<<8)) return RecordState::INVALID;
    id=static_cast<uint32_t>(bytes[2]) | static_cast<uint32_t>(bytes[3])<<8 |
       static_cast<uint32_t>(bytes[4])<<16;
    // Bench ID budget explicitly limited to 24bits, no unchecked wrap/reuse.
    return bytes[1]?RecordState::PENDING:RecordState::READY;
  }
  bool write(bool pending,uint32_t id) override {
    if (id>0xffffffu) return false;
    uint8_t bytes[7]={1,static_cast<uint8_t>(pending?1:0),
      static_cast<uint8_t>(id),static_cast<uint8_t>(id>>8),static_cast<uint8_t>(id>>16),0,0};
    const auto crc=uart_v1::crc16(bytes,5);
    bytes[5]=static_cast<uint8_t>(crc); bytes[6]=static_cast<uint8_t>(crc>>8);
    Preferences prefs;
    if (!prefs.begin("dispense-bench",false)) return false;
    const bool saved=prefs.putBytes("state-v1",bytes,sizeof(bytes))==sizeof(bytes);
    prefs.end();
    uint32_t got=0;
    return saved && load(got)==(pending?RecordState::PENDING:RecordState::READY) && got==id;
  }
};
BenchJournal journal;
m4::ArduinoPins pins_io;
m4::Hx711 scale(pins_io);
m4::NvsCalibration calibration_store;
m4::CalibrationRecord calibration;
m4::LedcServoOutput pwm;
m4::dispense_bench::Controller dispenser(pwm,journal);
bool journal_corrupt=false;
char line[224]{};
size_t used=0;
bool discard_line=false;
uint32_t sequence=0;

uint16_t calibrationId() {
  if (!scale.calibration.valid()) return 0;
  uint8_t bytes[17]{1}; uint64_t bits=0;
  std::memcpy(&bits,&scale.calibration.tare_counts,8);
  m4::calibration_record::put(bytes+1,bits,8);
  std::memcpy(&bits,&scale.calibration.grams_per_count,8);
  m4::calibration_record::put(bytes+9,bits,8);
  const uint16_t crc=uart_v1::crc16(bytes,sizeof(bytes));
  return crc?crc:1;
}
m4::dispense_bench::Observation observation(uint32_t now) {
  m4::dispense_bench::Observation out{};
  out.now_ms=now;
  out.calibrated=scale.calibration.valid();
  out.calibration_id=calibrationId();
  out.healthy=scale.status.health==m4::Health::HEALTHY && scale.grams.valid;
  out.fresh=scale.grams.fresh;
  out.grams=scale.grams.valid?scale.grams.value:0;
  out.sample_at_ms=scale.grams.sampled_at_ms;
  return out;
}
void printEvent(m4::dispense_bench::Event event,uint32_t now) {
  using m4::dispense_bench::name;
  if (event==m4::dispense_bench::Event::NONE) return;
  auto& serial=protocolSerial();
  serial.printf("DISPENSE seq=%lu event=%s state=%s reason=%s request_id=%lu "
                "pulse_count=%u pulse_ms=%u elapsed_ms=%lu target_g=%.3f ",
      static_cast<unsigned long>(++sequence),name(event),name(dispenser.state()),name(dispenser.reason()),
      static_cast<unsigned long>(dispenser.id()),dispenser.pulses(),dispenser.pulseMs(),
      static_cast<unsigned long>(dispenser.elapsed(now)),static_cast<double>(dispenser.target()));
  if (dispenser.baselineValid())
    serial.printf("baseline_g=%.3f after_g=%.3f dispensed_g=%.3f remaining_g=%.3f ",
      static_cast<double>(dispenser.baseline()),static_cast<double>(dispenser.measured()),
      static_cast<double>(dispenser.dispensed()),
      static_cast<double>(dispenser.target()-dispenser.dispensed()));
  else serial.print("baseline_g=null after_g=null dispensed_g=null remaining_g=null ");
  serial.printf("servo=COMMAND_ONLY_CLOSE_PHYSICAL_UNVERIFIED servo_pwm_attached=%u "
                "pump=OFF physical_validated=false\r\n",pwm.attached()?1u:0u);
}
void response(const char* action,m4::dispense_bench::Reason reason) {
  protocolSerial().printf("DISPENSE_COMMAND seq=%lu action=%s result=%s state=%s "
                          "servo_close_physical=UNVERIFIED\r\n",
      static_cast<unsigned long>(++sequence),action,
      reason==m4::dispense_bench::Reason::NONE?"ACCEPTED":m4::dispense_bench::name(reason),
      m4::dispense_bench::name(dispenser.state()));
}
void status() {
  const auto now=millis();
  const auto settings=dispenser.settings();
  protocolSerial().printf("DISPENSE_STATUS state=%s reason=%s configured=%u "
      "inspection_required=%u hx_health=%s hx_reason=%s calibrated=%u calibration_id=%u raw=",
      m4::dispense_bench::name(dispenser.state()),m4::dispense_bench::name(dispenser.reason()),
      dispenser.configured()?1u:0u,dispenser.locked()?1u:0u,
      m4::name(scale.status.health),m4::name(scale.status.reason),scale.calibration.valid()?1u:0u,
      calibrationId());
  if (scale.raw.valid) protocolSerial().printf("%ld",static_cast<long>(scale.raw.value));
  else protocolSerial().print("null");
  protocolSerial().print(" grams=");
  if (scale.grams.valid && static_cast<uint32_t>(now-scale.grams.sampled_at_ms)<=1500)
    protocolSerial().printf("%.3f",static_cast<double>(scale.grams.value));
  else protocolSerial().print("null");
  protocolSerial().printf(" request_id=%lu pulse_count=%u servo_pwm_attached=%u "
                          "safe_min_us=%u safe_max_us=%u close_candidate_us=%u open_candidate_us=%u "
                          "coarse_ms=%u fine_ms=%u "
                          "settle_ms=%u max_pulses=%u tolerance_g=%.3f stable_range_g=%.3f "
                          "fine_threshold_g=%.3f max_target_g=%.3f max_dispensed_g=%.3f "
                          "pump=OFF cat_auto=OFF web=OFF physical_validated=false\r\n",
      static_cast<unsigned long>(dispenser.id()),dispenser.pulses(),pwm.attached()?1u:0u,
      settings.safe_min_us,settings.safe_max_us,settings.close_us,settings.open_us,
      settings.coarse_ms,settings.fine_ms,
      settings.settle_ms,settings.max_pulses,static_cast<double>(settings.tolerance_g),
      static_cast<double>(settings.stable_range_g),static_cast<double>(settings.fine_threshold_g),
      static_cast<double>(settings.max_target_g),static_cast<double>(settings.max_dispensed_g));
}
void command(const char* text) {
  const auto now=millis();
  if (strcmp(text,"dispense status")==0) { status(); return; }
  if (strcmp(text,"help")==0) {
    protocolSerial().println("BENCH ONLY: dispense status; dispense inspect YES; "
      "dispense configure MIN_US MAX_US CLOSE_US OPEN_US COARSE_MS FINE_MS SETTLE_MS "
      "MAX_PULSES FINE_THRESHOLD_G TOLERANCE_G STABLE_RANGE_G MAX_TARGET_G MAX_MEASURED_G CONFIRM; "
      "dispense arm YES; dispense test TARGET_G REQUEST_ID; dispense abort; dispense disarm. "
      "NO CAT/WEB/SCHEDULE/PUMP. Factory flash ERASES calibration; use matching application-only upgrade.");
    return;
  }
  if (strcmp(text,"dispense inspect YES")==0) {
    if (journal_corrupt) response("INSPECT",m4::dispense_bench::Reason::PERSISTENCE_FAULT);
    else response("INSPECT",dispenser.inspect(now)?m4::dispense_bench::Reason::NONE:
                                         m4::dispense_bench::Reason::PERSISTENCE_FAULT);
    return;
  }
  unsigned a=0,b=0,c=0,d=0,e=0,f=0,g=0,h=0;float i=0,j=0,k=0,l=0,m=0;
  char confirm[8]{};char extra=0;
  if (strncmp(text,"dispense configure",18)==0) {
    const int count=sscanf(text,"dispense configure %u %u %u %u %u %u %u %u %f %f %f %f %f %7s %c",
        &a,&b,&c,&d,&e,&f,&g,&h,&i,&j,&k,&l,&m,confirm,&extra);
    if (count!=14 || strcmp(confirm,"CONFIRM")!=0 ||
        a>65535 || b>65535 || c>65535 || d>65535 || e>65535 || f>65535 ||
        g>65535 || h>255) {
      response("CONFIGURE",m4::dispense_bench::Reason::INVALID_CONFIG); return;
    }
    m4::dispense_bench::Settings settings{};
    settings.safe_min_us=static_cast<uint16_t>(a); settings.safe_max_us=static_cast<uint16_t>(b);
    settings.close_us=static_cast<uint16_t>(c); settings.open_us=static_cast<uint16_t>(d);
    settings.coarse_ms=static_cast<uint16_t>(e); settings.fine_ms=static_cast<uint16_t>(f);
    settings.settle_ms=static_cast<uint16_t>(g); settings.max_pulses=static_cast<uint8_t>(h);
    settings.fine_threshold_g=i;settings.tolerance_g=j;settings.stable_range_g=k;
    settings.max_target_g=l;settings.max_dispensed_g=m;
    const bool configured=dispenser.configure(settings);
    response("CONFIGURE",configured?m4::dispense_bench::Reason::NONE:
                        m4::dispense_bench::Reason::INVALID_CONFIG);
    if (configured) status();
    return;
  }
  if (strcmp(text,"dispense arm YES")==0) { response("ARM",dispenser.arm(observation(now))); return; }
  if (strncmp(text,"dispense test",13)==0) {
    float target=0;unsigned id=0;
    if (sscanf(text,"dispense test %f %u %c",&target,&id,&extra)!=2 || id>0xffffffu || !id) {
      response("TEST",m4::dispense_bench::Reason::INVALID_ID); return;
    }
    const auto code=dispenser.start(id,target,observation(now)); response("TEST",code);
    if (code==m4::dispense_bench::Reason::NONE) printEvent(m4::dispense_bench::Event::START,now);
    return;
  }
  if (strcmp(text,"dispense abort")==0) {
    const auto reason=dispenser.abort(now);
    response("ABORT",reason);
    if (reason==m4::dispense_bench::Reason::ABORTED)
      printEvent(m4::dispense_bench::Event::FAULT,now);
    return;
  }
  if (strcmp(text,"dispense disarm")==0) {
    const bool was_active=dispenser.active() || dispenser.state()==m4::dispense_bench::State::ARMED;
    dispenser.disarm(now);
    if (was_active) printEvent(m4::dispense_bench::Event::FAULT,now);
    status();return;
  }
  response("UNKNOWN",m4::dispense_bench::Reason::INVALID_CONFIG);
}
void serialCommands() {
  unsigned processed=0;
  while (processed++<32 && protocolSerial().available()>0) {
    const int byte=protocolSerial().read();
    if (byte=='\n' || byte=='\r') {
      if (!discard_line && used) { line[used]=0;command(line); }
      used=0;discard_line=false;
    } else if (byte>=32 && byte<=126 && !discard_line) {
      if (used+1<sizeof(line)) line[used++]=static_cast<char>(byte);
      else { used=0;discard_line=true; }
    } else { used=0;discard_line=true; }
  }
}
} // namespace
void setup() {
  pwm.off();
  protocolSerial().begin(115200);
  uint32_t last_id=0;
  const auto recorded=journal.load(last_id);
  journal_corrupt=recorded==RecordState::INVALID;
  dispenser.boot(recorded==RecordState::READY || recorded==RecordState::PENDING,
                 recorded!=RecordState::READY,last_id);
  const auto loaded=calibration_store.load(calibration);
  scale.applyCalibration(calibration.hx711);
  scale.begin({{current_hardware::HX711_DOUT,true},{current_hardware::HX711_SCK,true},500},millis());
  protocolSerial().printf("DISPENSE BENCH ONLY DISARMED GPIO4/5 HX711 GPIO6 SERVO "
      "GPIO7 PUMP OFF NO CAT/WEB/SCHEDULE. CALIBRATION_LOAD code=%u "
      "JOURNAL code=%u. INSPECT bowl/gate before arming. CLOSE PHYSICAL UNVERIFIED\r\n",
      static_cast<unsigned>(loaded),static_cast<unsigned>(recorded));
  status();
}
void loop() {
  const auto now=millis();
  scale.poll(now);
  const auto sample=observation(now);
  const auto event=dispenser.tick(sample);
  printEvent(event,now);
  if (event==m4::dispense_bench::Event::NONE && dispenser.pulsePending())
    printEvent(dispenser.launchPulse(sample),now);
  serialCommands();
  delay(1);
}
#endif
