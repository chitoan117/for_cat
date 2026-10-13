#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <deque>
#include <vector>
#include <limits>
#include "m4/hx711.h"
#include "m4/ultrasonic.h"
#include "m4/accessories.h"
#include "m4/oled.h"
#include "m4/calibration_record.h"
#include "m4/actuator_interfaces.h"
#include "safety_record_codec.h"
#include "command_dispatch.h"

static unsigned checks = 0;
#define CHECK(x) do { ++checks; if (!(x)) { std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); std::exit(1); } } while (0)
static bool near(double a, double b) { return std::fabs(a-b)<0.001; }
const float nan_value=std::numeric_limits<float>::quiet_NaN();
struct Pins : m4::PinIO {
  bool levels[64]{};
  std::deque<bool> bits;
  unsigned touches=0, highs=0, pauses=0, entries=0, exits=0;
  bool critical=false;
  bool inputAllowed(int p) const override { return p>=0 && p<32; }
  bool outputAllowed(int p) const override { return inputAllowed(p) && p!=31; }
  m4::Pull pulls[64]{};
  void input(int pin, m4::Pull pull) override { ++touches; pulls[pin]=pull; }
  void output(int) override { ++touches; }
  bool read(int p) override {
    ++touches;
    if (p==1 && !bits.empty()) { bool b=bits.front(); bits.pop_front(); return b; }
    return levels[p];
  }
  void write(int p,bool high) override { ++touches; levels[p]=high; if(high) ++highs; }
  void pauseMicros(uint32_t us) override { CHECK(critical && us<=2); ++pauses; }
  void enterCritical() override { critical=true; ++entries; }
  void exitCritical() override { critical=false; ++exits; }
  void sample(int32_t value) {
    bits.push_back(false); // ready
    for(int bit=23;bit>=0;--bit) bits.push_back((static_cast<uint32_t>(value)>>bit)&1);
  }
};
struct Bus : m4::I2CBus {
  bool ready=false, ok=true;
  uint8_t regs[256]{};
  unsigned calls=0, packets=0;
  size_t maximum=0;
  bool begin(m4::Pin a,m4::Pin b,uint16_t timeout) override {
    ready=a.reviewed && b.reviewed && a.number>=0 && b.number>=0 && a.number!=b.number && timeout>0;
    return ready;
  }
  bool configured() const override { return ready; }
  bool ping(uint8_t a) override { ++calls; return ok && (a==0x68 || a==0x3c); }
  bool readRegisters(uint8_t,uint8_t first,uint8_t* out,size_t n) override {
    ++calls; if(!ok) return false; std::memcpy(out,regs+first,n); return true;
  }
  bool writeRegisters(uint8_t,uint8_t first,const uint8_t* in,size_t n) override {
    ++calls; if(!ok) return false; std::memcpy(regs+first,in,n); return true;
  }
  bool packet(uint8_t,uint8_t,const uint8_t*,size_t n) override {
    ++calls; ++packets; if(n>maximum) maximum=n; return ok;
  }
};
void hx711() {
  Pins p; m4::Hx711 h(p);
  CHECK(!h.begin({},0)); h.poll(500); CHECK(p.touches==0);
  CHECK(!h.begin({{1,false},{2,true},500},0)); CHECK(p.touches==0);
  CHECK(!h.begin({{1,true},{31,true},500},0)); CHECK(p.touches==0);
  CHECK(!h.begin({{1,true},{1,true},500},0)); CHECK(p.touches==0);
  CHECK(h.begin({{1,true},{2,true},500},0));
  p.levels[1]=true; h.poll(499); CHECK(h.status.health==m4::Health::INITIALIZING);
  h.poll(500); CHECK(h.status.health==m4::Health::NOT_CONNECTED && !h.raw.valid);
  CHECK(h.startAverage(2)); p.sample(-100); h.poll(501);
  CHECK(h.raw.valid && h.raw.value==-100 && h.raw.fresh);
  CHECK(h.status.health==m4::Health::NOT_CALIBRATED && !h.grams.valid);
  CHECK(p.highs==25 && p.pauses==50 && p.entries==1 && p.exits==1 && !p.levels[2]);
  p.sample(100); h.poll(502); CHECK(h.averaged.valid && near(h.averaged.value,0));
  CHECK(h.tare()); CHECK(!h.calibration.valid());
  CHECK(!h.startAverage(0)); CHECK(!h.startAverage(65));
  CHECK(h.startAverage(1)); p.sample(1000); h.poll(503);
  CHECK(!h.calibrate(0)); CHECK(!h.calibrate(nan_value)); CHECK(h.calibrate(100));
  p.sample(500); h.poll(504); CHECK(h.grams.valid && near(h.grams.value,50));
  p.sample(-1); h.poll(505); CHECK(!h.grams.valid && h.status.health==m4::Health::DEGRADED);
  CHECK(h.startAverage(2)); p.sample(100); h.poll(506); h.poll(1006);
  CHECK(!h.averaged.valid && !h.grams.valid);
  p.sample(200); h.poll(1007); CHECK(!h.averaged.valid); // no pre-/post-timeout mixing
  p.sample(8388607); h.poll(1008); CHECK(h.status.health==m4::Health::FAULT && !h.grams.valid);
  CHECK(!h.raw.valid);
  CHECK(h.startAverage(1)); p.sample(500); h.poll(1009); CHECK(h.grams.valid);
  CHECK(h.tare()); CHECK(!h.grams.valid && !h.calibration.valid() && h.status.health==m4::Health::NOT_CALIBRATED);
  CHECK(h.startAverage(1)); p.sample(1000); h.poll(1010);
  CHECK(h.calibrate(50)); CHECK(!h.grams.valid && h.status.health==m4::Health::INITIALIZING);
  p.sample(750); h.poll(1011); CHECK(h.grams.valid && near(h.grams.value,25));
  h.applyCalibration({}); CHECK(!h.grams.valid && h.status.health==m4::Health::NOT_CALIBRATED);
  CHECK(h.begin({{1,true},{2,true},10},0xfffffff8u)); h.poll(2);
  CHECK(h.status.health==m4::Health::NOT_CONNECTED); // wrap-safe timeout
}
void calibration() {
  m4::RawAverage a; CHECK(!a.begin(0)); CHECK(!a.begin(65)); CHECK(a.begin(64));
  for(int i=0;i<64;++i) CHECK(a.add(8388607));
  CHECK(a.ready() && near(a.mean(),8388607)); CHECK(!a.add(0));
  m4::ScaleCalibration c; CHECK(!c.grams(0,0).valid); CHECK(!c.reference(10,100));
  CHECK(!c.tare(nan_value)); CHECK(c.tare(1000)); CHECK(!c.reference(1000,100));
  CHECK(c.reference(0,100)); CHECK(c.grams_per_count<0); CHECK(near(c.grams(500,1).value,50));
  CHECK(!c.grams(1001,1).valid); CHECK(!c.grams(8388608,1).valid);
  auto e=m4::compareMass(98,100); CHECK(e.valid && near(e.absolute_grams,2) && near(e.relative_percent,2));
  CHECK(!m4::compareMass(0,0).valid);
  m4::LevelCalibration level; CHECK(!level.percent({true,20,1,true},1,100).valid);
  CHECK(!level.set(0,20)); CHECK(!level.set(20,10)); CHECK(!level.set(nan_value,20)); CHECK(level.set(10,30));
  CHECK(near(level.percent({true,20,1,true},1,100).value,50));
  CHECK(near(level.percent({true,5,1,true},1,100).value,100));
  CHECK(near(level.percent({true,50,1,true},1,100).value,0));
  CHECK(!level.percent({true,0,1,true},1,100).valid);
  CHECK(!level.percent({true,20,1,true},nan_value,100).valid);
  m4::CalibrationRecord record; uint8_t bytes[m4::calibration_record::SIZE];
  CHECK(m4::calibration_record::encode(record,bytes));
  record.hx711=c; record.food=level; CHECK(record.water.set(5,25));
  CHECK(m4::calibration_record::encode(record,bytes));
  m4::CalibrationRecord copy; CHECK(m4::calibration_record::decode(bytes,copy));
  CHECK(copy.hx711.valid() && near(copy.hx711.grams_per_count,-0.1));
  CHECK(near(copy.food.empty_cm,30) && near(copy.water.empty_cm,25));
  for(size_t i=0;i<sizeof(bytes);++i) {
    bytes[i]^=1; CHECK(!m4::calibration_record::decode(bytes,copy)); bytes[i]^=1;
    CHECK(copy.hx711.valid()); // atomic decode retains previous destination
  }
  bytes[3]=2; m4::calibration_record::put(bytes+37,uart_v1::crc16(bytes,37),2);
  CHECK(!m4::calibration_record::decode(bytes,copy));
  record.hx711.grams_per_count=nan_value; CHECK(!m4::calibration_record::encode(record,bytes));
}
void rtc() {
  Bus b; m4::Ds3231 r(b); m4::I2CScanner scan(b);
  CHECK(!r.begin()); CHECK(!r.poll(0)); CHECK(!scan.start()); CHECK(b.calls==0);
  b.ready=true; b.ok=false; CHECK(!r.begin()); CHECK(r.status.health==m4::Health::NOT_CONNECTED);
  b.ok=true; CHECK(r.begin()); CHECK(!r.poll(0)); CHECK(!r.time.valid);
  m4::DateTime valid{2024,2,29,23,59,59}; uint8_t raw[7];
  CHECK(m4::encodeRtc(valid,raw)); std::memcpy(b.regs,raw,7);
  CHECK(r.poll(100)); CHECK(r.time.valid && r.time.value.day==29);
  CHECK(m4::epoch({2000,1,1,0,0,0})==946684800);
  CHECK(!m4::validDate({2100,2,29,0,0,0})); CHECK(m4::validDate({2000,2,29,0,0,0}));
  b.regs[0x0f]=0x80; CHECK(!r.poll(101)); CHECK(!r.time.valid);
  CHECK(r.set({2100,3,1,12,0,0})); CHECK(!r.time.valid); CHECK(r.poll(102)); CHECK(r.time.value.year==2100);
  b.regs[2]=0x72; CHECK(r.poll(103)); CHECK(r.time.value.hour==12); // 12 PM
  b.regs[2]=0x52; CHECK(r.poll(104)); CHECK(r.time.value.hour==0); // 12 AM
  b.regs[0]=0x6a; CHECK(!r.poll(105)); CHECK(!r.time.valid);
  CHECK(!r.set({2023,2,29,0,0,0}));
  CHECK(r.status.health==m4::Health::FAULT && !r.time.valid);
  CHECK(r.set(valid)); CHECK(r.poll(106)); b.ok=false; CHECK(!r.set(valid)); CHECK(!r.time.valid);
  b.ok=true; CHECK(scan.start()); unsigned count=0,found_count=0; uint8_t addr=0; bool found=false;
  while(scan.tick(addr,found)) { CHECK(addr>=8 && addr<=0x77); ++count; if(found) ++found_count; }
  CHECK(count==112 && found_count==2);
}
void echo(m4::Ultrasonic& u,Pins& p,uint32_t start,uint32_t width) {
  p.levels[4]=false; CHECK(u.trigger(start)); u.poll(start+2,1); CHECK(p.levels[3]);
  u.poll(start+12,1); CHECK(!p.levels[3]); p.levels[4]=true; u.poll(start+20,1);
  p.levels[4]=false; u.poll(start+20+width,2);
}
void ultrasonic() {
  Pins p; m4::LevelSensor l(p),water(p);
  CHECK(!l.distance.begin({})); CHECK(!l.distance.trigger(0)); CHECK(p.touches==0);
  CHECK(!l.distance.begin({{3,false},{4,true},1,100,30000,0.0343f})); CHECK(p.touches==0);
  CHECK(l.distance.begin({{3,true},{4,true},1,100,30000,0.0343f}));
  echo(l.distance,p,0,1000); CHECK(near(l.distance.raw.value,17.15)); l.update();
  CHECK(l.status.health==m4::Health::NOT_CALIBRATED && !l.percent.valid);
  CHECK(l.calibration.set(10,30)); l.update(); CHECK(l.percent.valid); CHECK(!water.calibration.valid());
  echo(l.distance,p,2000,1100); echo(l.distance,p,4000,5000); CHECK(near(l.distance.filtered.value,18.865));
  CHECK(l.distance.trigger(10000)); l.distance.poll(10002,10); CHECK(p.levels[3]);
  l.distance.poll(40000,40); l.update(); CHECK(!p.levels[3] && !l.percent.valid && !l.distance.busy());
  CHECK(l.status.health==m4::Health::NOT_CONNECTED);
  echo(l.distance,p,50000,1200); CHECK(near(l.distance.filtered.value,20.58)); // filter cleared on timeout
  echo(l.distance,p,60000,1); CHECK(l.distance.status.health==m4::Health::FAULT && !l.distance.filtered.valid);
  p.levels[4]=true; CHECK(!l.distance.trigger(70000)); CHECK(!l.distance.raw.valid);
  p.levels[4]=false; echo(l.distance,p,0xfffffff0u,1000); CHECK(l.distance.filtered.valid);
}
void accessories() {
  Pins p; m4::ManualButton button(p); m4::Buzzer buzzer(p);
  CHECK(!button.begin({},0)); CHECK(!button.poll(100)); CHECK(!buzzer.begin({}));
  CHECK(!buzzer.start(m4::BuzzerPattern::WARNING,0)); buzzer.tick(100); CHECK(p.touches==0);
  p.levels[5]=true; CHECK(button.begin({{5,true},m4::Pull::UP,true,40,1000},0));
  p.levels[5]=false; CHECK(!button.poll(10)); p.levels[5]=true; CHECK(!button.poll(20));
  p.levels[5]=false; CHECK(!button.poll(30)); CHECK(!button.poll(70));
  p.levels[5]=true; CHECK(!button.poll(100)); CHECK(button.poll(140)); CHECK(!button.poll(141));
  p.levels[5]=false; CHECK(!button.poll(200)); CHECK(!button.poll(240));
  p.levels[5]=true; CHECK(!button.poll(1400)); CHECK(!button.poll(1440)); // long press denied
  p.levels[5]=false; CHECK(button.begin({{5,true},m4::Pull::UP,true,40,1000},2000));
  p.levels[5]=true; CHECK(!button.poll(2010)); CHECK(!button.poll(2050)); // boot-held release denied
  p.levels[5]=false; CHECK(button.begin({{5,true},m4::Pull::DOWN,false,40,1000},3000));
  CHECK(p.pulls[5]==m4::Pull::DOWN);
  p.levels[5]=true; CHECK(!button.poll(3010)); CHECK(!button.poll(3050));
  p.levels[5]=false; CHECK(!button.poll(3100)); CHECK(button.poll(3140)); CHECK(!button.poll(3141));
  CHECK(buzzer.begin({6,true})); CHECK(!p.levels[6]);
  CHECK(buzzer.start(m4::BuzzerPattern::CONFIRMATION,0)); buzzer.tick(0); CHECK(p.levels[6]);
  buzzer.tick(100); CHECK(!p.levels[6]); buzzer.tick(200); CHECK(!buzzer.state.active());
  for(auto pattern : {m4::BuzzerPattern::WARNING,m4::BuzzerPattern::FAULT}) {
    CHECK(buzzer.start(pattern,0)); for(unsigned t=0;t<=2000;t+=100) buzzer.tick(t);
    CHECK(!buzzer.state.active() && !p.levels[6]);
  }
}
void snapshotsAndDisplay() {
  m4::SensorSnapshot s; CHECK(!m4::feedInputs(s).rtc_valid); CHECK(m4::feedInputs(s).scale==safety::Health::FAULT);
  CHECK(m4::shadowWaterInputs(s).sensor==safety::Health::FAULT);
  s.sampled_at_ms=100; s.rtc=s.load_cell=s.food=s.water={m4::Health::HEALTHY,m4::Reason::NONE};
  s.rtc_time={true,{2026,10,3,12,0,0},100,true}; s.grams={true,10,100,true};
  s.food_percent={true,50,100,true}; s.water_percent={true,10,100,true};
  auto inputs=m4::feedInputs(s); CHECK(inputs.rtc_valid && inputs.food_available && inputs.scale==safety::Health::OK);
  CHECK(inputs.servo==safety::Health::NOT_VALIDATED);
  safety::WaterController policy; policy.boot(); policy.tick(m4::shadowWaterInputs(s));
  s.water_percent.fresh=false;
  for(unsigned i=0;i<100;++i) m4::tickShadowWater(policy,s);
  CHECK(policy.state()==safety::WaterState::SAFE_BOOT && !policy.pumpRequested());
  s.water_percent.fresh=true;
  for(unsigned i=0;i<4;++i) { s.sampled_at_ms+=500; s.water_percent.sampled_at_ms=s.sampled_at_ms; m4::tickShadowWater(policy,s); }
  CHECK(policy.state()==safety::WaterState::FILLING && policy.pumpRequested());
  s.water_percent.fresh=false; s.sampled_at_ms+=5001;
  s.water_percent.sampled_at_ms=s.sampled_at_ms; // isolate filling timer from stale-data fault
  m4::tickShadowWater(policy,s); CHECK(policy.reason()==safety::WaterReason::NO_PROGRESS && !policy.pumpRequested());
  s.sampled_at_ms=100;
  CHECK(!s.physical_pump_on && !s.hardware_verified);
  s.water_percent.valid=false; policy.tick(m4::shadowWaterInputs(s)); CHECK(!policy.pumpRequested());
  s.grams.value=nan_value; CHECK(m4::feedInputs(s).scale==safety::Health::FAULT);
  s.sampled_at_ms=2101; CHECK(!m4::feedInputs(s).rtc_valid && !m4::feedInputs(s).food_available);
  Bus b; m4::Ssd1306 display(b); CHECK(!display.begin(0x3c,64)); CHECK(b.calls==0);
  b.ready=true; CHECK(!display.begin(0x30,64)); CHECK(!display.begin(0x3c,16)); CHECK(b.calls==0);
  CHECK(display.begin(0x3c,64)); display.statusLines(s);
  for(int i=0;i<65;++i) display.tick(); CHECK(display.status.health==m4::Health::HEALTHY);
  CHECK(b.maximum<=31 && b.packets==66);
  display.statusLines(s); b.ok=false; display.tick(); CHECK(display.status.health==m4::Health::FAULT);
  CHECK(!m4::feedInputs(s).rtc_valid); // display cannot manufacture sensor validity
  s.sampled_at_ms=100; s.grams.value=10; CHECK(m4::feedInputs(s).scale==safety::Health::OK); // failed display independent
  m4::DisabledServo servo; m4::DisabledPump pump;
  CHECK(!servo.initialize({7,true}) && !servo.requestClosed(0) && !servo.requestDispense(0));
  CHECK(!pump.initialize({8,true}) && !pump.requestOn(0,100)); pump.off(); servo.safeStop();
  CHECK(!servo.physicalOutput() && !pump.physicalOutput() && pump.state==m4::PumpState::OFF);
  for(unsigned flags=0;flags<16;++flags)
    CHECK(m4::futureOutputPermission(flags&1,flags&2,flags&4,flags&8)==(flags==15));
}
struct CounterStore : safety::DailyStore {
  unsigned writes=0;
  bool save(const safety::DailyRecord&) override { ++writes; return true; }
};
// Pure host policy: servo readiness below is hypothetical to isolate each sensor prerequisite.
// No GPIO, actuator adapter or production command dispatcher is enabled by these tests.
void denied(const m4::SensorSnapshot& healthy,const m4::SensorSnapshot& bad,safety::FeedReason reason) {
  CounterStore store; safety::FeedController feed; feed.attachStore(store);
  safety::DailyRecord record; record.day=m4::feedInputs(healthy).day; feed.boot(record);
  feed.tick(m4::feedInputs(healthy,true)); CHECK(feed.state()==safety::FeedState::IDLE);
  CHECK(feed.request(1,10,m4::feedInputs(bad,true)));
  CHECK(feed.state()==safety::FeedState::REJECTED && feed.reason()==reason);
  CHECK(!feed.openRequested() && store.writes==0);
}
void failSafeIntegration() {
  Pins pins; m4::Hx711 scale(pins); Bus bus; bus.ready=true; m4::Ds3231 rtc(bus);
  CHECK(scale.begin({{1,true},{2,true},500},100));
  CHECK(scale.calibration.tare(0)); CHECK(scale.calibration.reference(1000,100));
  pins.sample(100); scale.poll(100); CHECK(scale.status.health==m4::Health::HEALTHY);
  CHECK(rtc.begin()); CHECK(rtc.set({2026,10,3,12,0,0})); CHECK(rtc.poll(100));
  m4::SensorSnapshot healthy; healthy.sampled_at_ms=100;
  healthy.rtc=rtc.status; healthy.rtc_time=rtc.time; healthy.load_cell=scale.status; healthy.grams=scale.grams;
  healthy.food={m4::Health::HEALTHY,m4::Reason::NONE}; healthy.food_percent={true,50,100,true};
  m4::SensorSnapshot bad=healthy;
  pins.sample(8388607); scale.poll(101); bad.load_cell=scale.status; bad.grams=scale.grams;
  denied(healthy,bad,safety::FeedReason::HX711_FAULT);
  pins.levels[1]=true; scale.poll(601); bad.load_cell=scale.status; bad.grams=scale.grams;
  CHECK(scale.status.health==m4::Health::NOT_CONNECTED);
  denied(healthy,bad,safety::FeedReason::HX711_FAULT);
  bad=healthy; bad.grams.sampled_at_ms=0xfffff000u; denied(healthy,bad,safety::FeedReason::HX711_FAULT);
  bus.regs[0x0f]=0x80; CHECK(!rtc.poll(101)); bad=healthy; bad.rtc=rtc.status; bad.rtc_time=rtc.time;
  denied(healthy,bad,safety::FeedReason::RTC_INVALID);
  bad=healthy; bad.rtc_time.valid=false; denied(healthy,bad,safety::FeedReason::RTC_INVALID);
  bad=healthy; bad.food_percent.valid=false; denied(healthy,bad,safety::FeedReason::FOOD_EMPTY);

  m4::Ssd1306 oled(bus); CHECK(oled.begin(0x3c,64)); bus.ok=false; oled.tick();
  CHECK(oled.status.health==m4::Health::FAULT);
  CounterStore store; safety::FeedController feed; feed.attachStore(store);
  safety::DailyRecord record; record.day=m4::feedInputs(healthy).day; feed.boot(record);
  feed.tick(m4::feedInputs(healthy,true)); CHECK(feed.request(2,10,m4::feedInputs(healthy,true)));
  CHECK(feed.state()==safety::FeedState::PRECHECK && !feed.openRequested());
  feed.tick(m4::feedInputs(healthy,true));
  CHECK(feed.state()==safety::FeedState::DISPENSING && feed.openRequested() && store.writes==1);
  bad=healthy; bad.load_cell={m4::Health::FAULT,m4::Reason::INVALID_DATA}; bad.grams={};
  feed.tick(m4::feedInputs(bad,true));
  CHECK(feed.state()==safety::FeedState::FAULT && !feed.openRequested()); // display failure did not stop safety ticks
  m4::DisabledServo servo; CHECK(!servo.physicalOutput() && !healthy.hardware_verified);

  m4::SensorSnapshot water; water.water={m4::Health::HEALTHY,m4::Reason::NONE};
  safety::WaterController policy; policy.boot();
  const auto sample=[&](float value) {
    water.sampled_at_ms+=500; water.water_percent={true,value,water.sampled_at_ms,true};
    m4::tickShadowWater(policy,water);
  };
  for(unsigned i=0;i<5;++i) sample(10);
  CHECK(policy.state()==safety::WaterState::FILLING && policy.pumpRequested());
  sample(50); CHECK(policy.pumpRequested()); // hysteresis retains fill below high threshold
  sample(80); CHECK(policy.state()==safety::WaterState::NORMAL && !policy.pumpRequested());
  sample(50); CHECK(!policy.pumpRequested());
  for(unsigned i=0;i<3;++i) sample(10);
  CHECK(policy.pumpRequested());
  m4::LevelSensor level(pins); CHECK(level.distance.begin({{3,true},{4,true},1,100,30000,0.0343f}));
  CHECK(level.calibration.set(10,30)); echo(level.distance,pins,1000,1000); level.update();
  CHECK(level.percent.valid);
  CHECK(level.distance.trigger(10000)); level.distance.poll(40000,water.sampled_at_ms); level.update();
  water.water=level.status; water.water_percent=level.percent; m4::tickShadowWater(policy,water);
  CHECK(policy.reason()==safety::WaterReason::SENSOR_FAULT && !policy.pumpRequested());
  m4::DisabledPump pump; CHECK(!pump.physicalOutput() && !water.physical_pump_on);
}
void releaseProperties() {
  uint32_t state=0xF0CC1234u;
  const auto next=[&]() { state=state*1664525u+1013904223u; return state; };
  for(unsigned trial=0;trial<100;++trial) {
    m4::DateTime time{static_cast<uint16_t>(2000u+next()%200u),static_cast<uint8_t>(1u+next()%12u),1,
                     static_cast<uint8_t>(next()%24u),static_cast<uint8_t>(next()%60u),static_cast<uint8_t>(next()%60u)};
    time.day=static_cast<uint8_t>(1u+next()%m4::monthDays(time.year,time.month));
    uint8_t raw[7]; m4::DateTime restored;
    CHECK(m4::encodeRtc(time,raw)); CHECK(m4::decodeRtc(raw,restored)); CHECK(m4::epoch(time)==m4::epoch(restored));
    raw[4]=0; CHECK(!m4::decodeRtc(raw,restored));
    m4::CalibrationRecord c;
    CHECK(c.hx711.tare(static_cast<double>(next()%100000u)));
    CHECK(c.hx711.reference(c.hx711.tare_counts+1000,25));
    CHECK(c.food.set(5,50)); CHECK(c.water.set(10,100));
    uint8_t encoded[m4::calibration_record::SIZE]; CHECK(m4::calibration_record::encode(c,encoded));
    m4::CalibrationRecord decoded; CHECK(m4::calibration_record::decode(encoded,decoded));
    CHECK(near(decoded.hx711.grams_per_count,c.hx711.grams_per_count));
    const size_t byte=next()%sizeof(encoded); const uint8_t mask=static_cast<uint8_t>(1u<<(next()%8u));
    encoded[byte]^=mask; CHECK(!m4::calibration_record::decode(encoded,decoded)); CHECK(decoded.hx711.valid());
    m4::LevelCalibration geometry; CHECK(geometry.set(5,50));
    const float distance=static_cast<float>(1u+next()%100u);
    auto percent=geometry.percent({true,distance,1,true},1,100);
    CHECK(percent.valid && percent.value>=0 && percent.value<=100);
  }
  CHECK(!m4::validDate({2100,2,29,0,0,0}));
  CHECK(m4::epoch({2024,3,1,0,0,0})-m4::epoch({2024,2,29,23,59,59})==1);
  CHECK(m4::epoch({2027,1,1,0,0,0})-m4::epoch({2026,12,31,23,59,59})==1);
  safety::DailyRecord original; original.day=20261231; original.portions=2; original.grams=20; original.needs_inspection=true;
  uint8_t bytes[safety_record::SIZE]; CHECK(safety_record::encode(original,bytes));
  for(size_t offset=0;offset<sizeof(bytes);++offset) for(unsigned bit=0;bit<8;++bit) {
    const auto mask=static_cast<uint8_t>(1u<<bit); bytes[offset]^=mask;
    safety::DailyRecord destination=original; CHECK(!safety_record::decode(bytes,destination));
    CHECK(destination.day==original.day && destination.needs_inspection);
    bytes[offset]^=mask;
  }
  for(size_t length=0;length<sizeof(bytes);++length) {
    uint8_t truncated[safety_record::SIZE]{}; std::memcpy(truncated,bytes,length);
    safety::DailyRecord destination; CHECK(!safety_record::decode(truncated,destination));
  }
  for(uint8_t version : {uint8_t{1},uint8_t{2},uint8_t{4},uint8_t{255}}) {
    bytes[2]=version; const auto crc=uart_v1::crc16(bytes,sizeof(bytes)-2);
    bytes[23]=static_cast<uint8_t>(crc); bytes[24]=static_cast<uint8_t>(crc>>8);
    safety::DailyRecord destination; CHECK(!safety_record::decode(bytes,destination));
  }
  CounterStore store; safety::FeedController interrupted; interrupted.attachStore(store); interrupted.boot(original);
  safety::FeedInputs input; input.rtc_valid=true; input.day=20270101; input.epoch_seconds=1798761600;
  interrupted.tick(input); CHECK(interrupted.state()==safety::FeedState::SAFE_BOOT && !interrupted.openRequested());
  safety::DailyRecord yesterday; yesterday.day=20261231; yesterday.portions=4; yesterday.grams=150;
  safety::FeedController rollover; rollover.attachStore(store); rollover.boot(yesterday);
  input.rtc_valid=false; rollover.tick(input);
  CHECK(rollover.state()==safety::FeedState::SAFE_BOOT && rollover.record().portions==4);
  input.rtc_valid=true; rollover.tick(input);
  CHECK(rollover.state()==safety::FeedState::IDLE && rollover.record().day==20270101 && rollover.record().portions==0 && rollover.record().grams==0);
  dispatch::Controller disabled(false); dispatch::MemoryDailyStore memory;
  disabled.boot(memory,{},input);
  CHECK(disabled.command(0,uart_v1::FEED_REQUEST,input).command==uart_v1::NACK);
  CHECK(disabled.command(0xffffffffu,uart_v1::FEED_REQUEST,input).command==uart_v1::ACK);
  CHECK(disabled.command(0xffffffffu,uart_v1::FEED_REQUEST,input).command==uart_v1::ACK);
  CHECK(disabled.command(0xffffffffu,uart_v1::FEED_STATUS,input).value==2);
  CHECK(!disabled.feed.openRequested());
  m4::SensorSnapshot water; water.water={m4::Health::HEALTHY,m4::Reason::NONE};
  safety::WaterController fill; fill.boot();
  for(uint32_t i=0;i<5;++i) {
    water.sampled_at_ms=i*100; water.water_percent={true,10,water.sampled_at_ms,true}; m4::tickShadowWater(fill,water);
  }
  CHECK(fill.pumpRequested()); water.sampled_at_ms+=2001; water.water_percent.fresh=false;
  m4::tickShadowWater(fill,water); CHECK(!fill.pumpRequested() && fill.reason()==safety::WaterReason::SENSOR_FAULT);
}
int main() {
  hx711(); calibration(); rtc(); ultrasonic(); accessories(); snapshotsAndDisplay(); failSafeIntegration(); releaseProperties();
  std::printf("Native M4 drivers: %u assertions PASS (fake I/O; hardware NOT verified)\n",checks);
}
