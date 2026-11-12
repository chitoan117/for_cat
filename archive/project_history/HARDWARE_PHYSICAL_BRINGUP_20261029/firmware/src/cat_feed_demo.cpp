#include <Arduino.h>
#include "m4/diagnostic_config.h"
#if defined(CAT_FEED_DEMO) && CAT_FEED_DEMO
#include <cstring>
#include <cstdio>
#include "serial_port.h"
#include "m4/arduino_io.h"
#include "m4/hx711.h"
#include "m4/ledc_servo.h"
#include "m4/cat_feed_demo.h"
static_assert(CAT_FEED_PHYSICAL_ENABLE==1 && ACTUATOR_OUTPUTS_ENABLED==0 && M4_HX711_DOUT==4 && M4_HX711_SCK==5,
              "Explicit isolated CAT food-only image; GPIO7 untouched");
namespace {
namespace cf=m4::cat_feed_demo;
class Journal final:public cf::Journal {
 public:
  enum Load { MISSING, INVALID, READY, PENDING };
  Load load(uint32_t& id) {
    Preferences p; id=0;
    if (!p.begin("cat-feed-demo",true)) return MISSING;
    if (!p.isKey("state-v1")) { p.end(); return MISSING; }
    uint8_t b[8]{};
    const bool ok=p.getBytesLength("state-v1")==8 && p.getBytes("state-v1",b,8)==8;
    p.end();
    if (!ok || b[0]!=1 || b[1]>1 || m4::calibration_record::get(b+6,2)!=uart_v1::crc16(b,6)) return INVALID;
    id=static_cast<uint32_t>(m4::calibration_record::get(b+2,4)); return b[1]?PENDING:READY;
  }
  bool write(bool pending,uint32_t id) override {
    uint8_t b[8]{1,static_cast<uint8_t>(pending?1:0)};
    m4::calibration_record::put(b+2,id,4); m4::calibration_record::put(b+6,uart_v1::crc16(b,6),2);
    Preferences p;
    if (!p.begin("cat-feed-demo",false)) return false;
    const bool ok=p.putBytes("state-v1",b,8)==8; p.end(); uint32_t got=0;
    return ok && load(got)==(pending?PENDING:READY) && got==id;
  }
};
Journal journal;
m4::ArduinoPins pins_io;
m4::Hx711 scale(pins_io);
m4::NvsCalibration calibration_store;
m4::CalibrationRecord calibration;
m4::LedcServoOutput pwm;
cf::Controller feed(pwm,journal);
Journal::Load journal_load=Journal::MISSING;
bool calibration_loaded=false;
uint32_t last_report=0;
char buffer[128]{};
unsigned used=0; bool discard=false;
uint16_t calibrationId() {
  if (!scale.calibration.valid()) return 0;
  uint8_t b[m4::calibration_record::SIZE];
  m4::CalibrationRecord r; r.hx711=scale.calibration;
  if (!m4::calibration_record::encode(r,b)) return 0;
  const auto value=uart_v1::crc16(b,sizeof(b)-2); return value?value:1;
}
cf::Sample sample(uint32_t now) {
  return {now,scale.signed_grams.sampled_at_ms,scale.signed_grams.valid && scale.calibration.valid(),
          scale.signed_grams.fresh,scale.signed_grams.value,calibrationId()};
}
void report() {
  auto& s=protocolSerial();
  s.printf("{\"mode\":\"CAT_FEED_35G\",\"monotonic_ms\":%lu,\"state\":\"%s\",\"reason\":\"%s\",\"id\":%lu,\"last_id\":%lu,\"journal_ready\":%s,\"pending\":%s,\"calibrated\":%s,\"calibration_id\":%u,\"measurement_grams\":",
    static_cast<unsigned long>(millis()),cf::name(feed.state()),cf::name(feed.reason()),
    static_cast<unsigned long>(feed.id()),static_cast<unsigned long>(feed.lastId()),feed.initialized()?"true":"false",
    feed.pending()?"true":"false",calibration_loaded?"true":"false",calibrationId());
  const auto now=millis();
  if (scale.signed_grams.valid && static_cast<uint32_t>(now-scale.signed_grams.sampled_at_ms)<600) s.printf("%.6f",static_cast<double>(scale.signed_grams.value)); else s.print("null");
  s.print(",\"offset\":");
  if (scale.calibration.valid()) s.printf("%.9f",scale.calibration.tare_counts); else s.print("null");
  s.print(",\"scale_factor\":");
  if (scale.calibration.valid()) s.printf("%.9f",1.0/scale.calibration.grams_per_count); else s.print("null");
  s.print(",\"baseline_grams\":"); if (feed.baselineValid()) s.printf("%.6f",static_cast<double>(feed.baseline())); else s.print("null");
  s.print(",\"added_grams\":"); if (feed.baselineValid()) s.printf("%.6f",static_cast<double>(feed.delta())); else s.print("null");
  s.printf(",\"target_grams\":35,\"close_degrees\":90,\"open_degrees\":45,\"pwm_attached\":%s,\"pump_locked\":true}\r\n",pwm.attached()?"true":"false");
}
void command(const char* text) {
  auto& s=protocolSerial(); unsigned id=0; char extra=0;
  if (std::strcmp(text,"status")==0) { report(); return; }
  if (std::strcmp(text,"journal init CONFIRM")==0) {
    s.println(journal_load==Journal::MISSING && feed.initializeJournal()?"JOURNAL_INITIALIZED":"REJECTED JOURNAL_EXISTS_OR_PENDING"); return;
  }
  if (std::strncmp(text,"calset ",7)==0) {
    double offset=0,factor=0; char save[8]{};
    if (feed.state()!=cf::State::IDLE || feed.pending() || std::sscanf(text,"calset %lf %lf %7s %c",&offset,&factor,save,&extra)!=3 ||
        std::strcmp(save,"SAVE")!=0 || !std::isfinite(factor) || factor==0) { s.println("REJECTED CALSET"); return; }
    m4::CalibrationRecord next=calibration; next.hx711={true,true,offset,1.0/factor};
    if (!next.hx711.valid() || !calibration_store.save(next)) { s.println("REJECTED CALSET_SAVE"); return; }
    m4::CalibrationRecord got;
    if (calibration_store.load(got)!=m4::CalibrationLoad::LOADED || got.hx711.tare_counts!=offset ||
        got.hx711.grams_per_count!=next.hx711.grams_per_count) { s.println("REJECTED CALSET_READBACK"); return; }
    calibration=got; scale.applyCalibration(got.hx711); calibration_loaded=true;
    s.println("CALIBRATION_SAVED_READBACK_OK NO_TARE NO_REFIT"); return;
  }
  if (std::sscanf(text,"feed %u %c",&id,&extra)==1) {
    s.println(feed.start(id,sample(millis()))?"FEED_ACCEPTED":"FEED_REJECTED"); return;
  }
  if (std::sscanf(text,"cat %u %c",&id,&extra)==1) { feed.catLease(id,millis()); return; }
  if (std::strcmp(text,"stop")==0) { feed.abort(millis(),cf::Reason::DOG_OR_CAT_LOST); return; }
  s.println("REJECTED UNKNOWN_COMMAND");
}
void serialCommands() {
  for (unsigned n=0;n<32 && protocolSerial().available();++n) {
    const char c=static_cast<char>(protocolSerial().read());
    if (c=='\r' || c=='\n') { if (!discard && used) { buffer[used]=0; command(buffer); } used=0; discard=false; }
    else if (c>=32 && c<=126 && !discard) { if (used<sizeof(buffer)-1) buffer[used++]=c; else { used=0; discard=true; } }
    else { used=0; discard=true; }
  }
}
} // namespace
void setup() {
  protocolSerial().begin(115200);
  uint32_t last=0; journal_load=journal.load(last);
  feed.boot(journal_load==Journal::READY || journal_load==Journal::PENDING,
            journal_load==Journal::PENDING || journal_load==Journal::INVALID,last);
  calibration_loaded=calibration_store.load(calibration)==m4::CalibrationLoad::LOADED && calibration.hx711.valid();
  scale.applyCalibration(calibration.hx711);
  scale.begin({{4,true},{5,true},500},millis());
  protocolSerial().println("CAT_FEED_35G IDLE: MG996R90->45->90; no auto tare; DOG never starts; pump GPIO7 untouched");
  report();
}
void loop() {
  const auto now=millis(); scale.poll(now); serialCommands();
  const auto before=feed.state(); feed.tick(sample(millis()));
  if (before!=feed.state() || static_cast<uint32_t>(now-last_report)>=250) { report(); last_report=now; }
  delay(1);
}
#endif
