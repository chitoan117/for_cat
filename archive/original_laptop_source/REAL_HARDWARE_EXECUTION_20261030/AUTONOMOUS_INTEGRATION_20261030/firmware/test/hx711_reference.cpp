#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <limits>
#include "m4/hx711.h"
#include "m4/calibration_record.h"

static unsigned checks=0;
#define CHECK(x) do { ++checks; if (!(x)) { std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); std::exit(1); } } while (0)
static bool near(double a,double b,double tolerance=0.0001) { return std::fabs(a-b)<=tolerance; }
struct Pins final : m4::PinIO {
  std::deque<bool> bits;
  bool critical=false,high=false;
  unsigned clocks=0,entries=0,exits=0;
  bool inputAllowed(int p) const override { return p==4 || p==5; }
  bool outputAllowed(int p) const override { return p==5; }
  void input(int p,m4::Pull pull) override { CHECK(p==4 && pull==m4::Pull::NONE); }
  void output(int p) override { CHECK(p==5); }
  bool read(int p) override {
    CHECK(p==4);
    if (bits.empty()) { CHECK(!critical); return true; }
    const bool b=bits.front(); bits.pop_front(); return b;
  }
  void write(int p,bool v) override { CHECK(p==5); high=v; if (v) { CHECK(critical); ++clocks; } }
  void pauseMicros(uint32_t us) override { CHECK(critical && us==2); }
  void enterCritical() override { CHECK(!critical); critical=true; ++entries; }
  void exitCritical() override { CHECK(critical && !high); critical=false; ++exits; }
  void sample(int32_t raw) {
    CHECK(bits.empty()); bits.push_back(false);
    for (int bit=23;bit>=0;--bit) bits.push_back((static_cast<uint32_t>(raw)>>bit)&1u);
  }
};
const m4::ScaleCalibration reference{true,true,-668483.0,1.0/-1064.4473};
void conversion() {
  Pins p; m4::Hx711 h(p);
  CHECK(!h.begin({},0)); CHECK(h.begin({{4,true},{5,true},500},0));
  h.applyCalibration(reference);
  uint32_t now=0;
  for (int32_t value : {-8388607,-704443,-668483,-2,1,0x123456,8388606}) {
    p.sample(value); h.poll(++now);
    CHECK(h.raw.valid && h.raw.value==value && h.raw.fresh && p.bits.empty());
    CHECK(!p.high && !p.critical && p.entries==p.exits);
  }
  CHECK(p.clocks==7*25); // exactly channel A / gain 128
  for (int32_t value : {0,-1,-8388608,8388607}) {
    p.sample(value); h.poll(++now);
    CHECK(!h.raw.valid && h.raw.value==value && !h.grams.valid);
    CHECK(!h.signed_grams.valid && !h.display_grams.valid && !h.median_raw.valid);
    CHECK(h.status.health==m4::Health::FAULT && h.status.reason==m4::Reason::INVALID_DATA);
  }
}
void medianAndMass() {
  m4::Hx711Median3 median;
  int32_t values[]={-900000,-700000,-600000},result=0;
  do {
    CHECK(!median.add(values[0],result)); CHECK(!median.add(values[1],result));
    CHECK(median.add(values[2],result) && result==-700000);
  } while (std::next_permutation(values,values+3));
  CHECK(!median.add(1,result)); median.reset();
  CHECK(!median.add(2,result)); CHECK(!median.add(3,result)); CHECK(median.add(4,result) && result==3);
  Pins p; m4::Hx711 h(p); CHECK(h.begin({{4,true},{5,true},500},0)); h.applyCalibration(reference);
  uint32_t now=0;
  for (double grams : {0.,5.,10.,20.,35.,38.,0.,-2.37}) {
    const auto raw=static_cast<int32_t>(std::llround(reference.tare_counts+grams*(-1064.4473)));
    // One large outlier in each independent triplet must not become the mass.
    p.sample(raw); h.poll(++now); CHECK(!h.median_raw.fresh);
    p.sample(raw-100000); h.poll(++now); CHECK(!h.median_raw.fresh);
    p.sample(raw); h.poll(++now);
    CHECK(h.median_raw.valid && h.median_raw.fresh && h.median_raw.value==raw);
    CHECK(h.signed_grams.valid && h.display_grams.valid);
    CHECK(near(h.signed_grams.value,grams,0.0006));
    if (grams>=0) CHECK(h.grams.valid && near(h.grams.value,h.signed_grams.value));
    else CHECK(!h.grams.valid && h.signed_grams.value<0); // drift remains visible, not fake zero
  }
  const auto timestamp=h.signed_grams.sampled_at_ms;
  h.poll(++now); CHECK(!h.display_grams.fresh && h.signed_grams.sampled_at_ms==timestamp);
  auto c=reference;
  c.grams_per_count=-0.01; CHECK(near(m4::hx711SignedGrams(c,c.tare_counts-500,now).value,5));
  c.grams_per_count=0.01; CHECK(near(m4::hx711SignedGrams(c,c.tare_counts+500,now).value,5));
  c.grams_per_count=0; CHECK(!m4::hx711SignedGrams(c,100,now).valid);
}
void display() {
  m4::Hx711ReferenceDisplay f;
  const auto update=[&](float x) { return f.update({true,x,1,true}).value; };
  CHECK(near(update(0.19f),0));
  CHECK(near(update(5),5)); CHECK(near(update(5.5f),5.2));
  CHECK(near(update(20),20)); CHECK(near(update(35),35)); CHECK(near(update(38),38));
  CHECK(near(update(0),0)); // removal >=1g is immediate on next complete triplet
  CHECK(near(update(-0.3f),0)); // display clamp only
  CHECK(near(update(-2.37f),-2.37));
  f.reset(); CHECK(near(update(1),1)); // inclusive threshold
  CHECK(near(update(2),2)); CHECK(near(update(1.5),1.8));
  f.reset(); CHECK(near(update(0.20f),0)); // alpha ->0.08 ->deadband
  CHECK(!f.update({}).valid);
  CHECK(!f.update({true,std::numeric_limits<float>::quiet_NaN(),0,true}).valid);
  CHECK(!f.update({true,5,0,false}).valid);
  // Fresh small updates converge, rather than freezing a real sub-1g mass.
  for (int i=0;i<20;++i) update(0.97f);
  CHECK(near(update(0.97f),0.97,0.001));
}
void faultAndTare() {
  Pins p; m4::Hx711 h(p); CHECK(h.begin({{4,true},{5,true},500},0)); h.applyCalibration(reference);
  uint32_t now=0;
  auto sample=[&](int32_t v) { p.sample(v); h.poll(++now); };
  sample(-700000); sample(-700000);
  CHECK(h.startAverage(15)); sample(-700000);
  CHECK(h.signed_grams.valid); const auto calibration=h.calibration;
  now+=499; h.poll(now); CHECK(h.signed_grams.valid && !h.signed_grams.fresh);
  ++now; h.poll(now); CHECK(!h.signed_grams.valid && !h.averaged.valid);
  CHECK(!h.tarePreservingFactor() && h.calibration.tare_counts==calibration.tare_counts);
  CHECK(h.status.reason==m4::Reason::TIMEOUT);
  sample(-680000); sample(-680000); CHECK(!h.median_raw.valid && !h.averaged.valid);
  sample(-680000); CHECK(h.median_raw.value==-680000 && h.signed_grams.valid);
  CHECK(h.startAverage(15));
  for (int i=0;i<14;++i) { sample(-669000); CHECK(!h.averaged.valid); }
  sample(-669015); CHECK(h.averaged.valid && near(h.averaged.value,-669001));
  const auto slope=h.calibration.grams_per_count;
  CHECK(h.tarePreservingFactor()); CHECK(h.calibration.valid() && h.calibration.grams_per_count==slope);
  CHECK(near(h.calibration.tare_counts,-669001) && !h.display_grams.valid && !h.median_raw.valid);
  sample(-669001); sample(-669001); CHECK(!h.display_grams.valid);
  sample(-669001); CHECK(h.display_grams.valid && near(h.display_grams.value,0));
  CHECK(h.startAverage(15)); sample(-700000); sample(0);
  CHECK(!h.averaged.valid && !h.tarePreservingFactor());
  CHECK(near(h.calibration.tare_counts,-669001));
  // No data or filter operation ever alters calibration without explicit tare.
  for (int i=0;i<30;++i) sample(-700000);
  CHECK(h.calibration.grams_per_count==slope && near(h.calibration.tare_counts,-669001));
  CHECK(h.begin({{4,true},{5,true},10},0xfffffff8u)); h.poll(2);
  CHECK(h.status.reason==m4::Reason::TIMEOUT && !h.display_grams.valid);
  // Existing safety-oriented calibration tare remains supported and invalidates slope.
  CHECK(h.startAverage(1)); sample(-669000); CHECK(h.tare()); CHECK(!h.calibration.valid());
}
void persistenceCodec() {
  m4::CalibrationRecord record;
  record.hx711={true,true,-667023.6666666666,-0.0009349817237534743};
  record.water={true,10,40};
  uint8_t bytes[m4::calibration_record::SIZE];
  CHECK(m4::calibration_record::encode(record,bytes));
  m4::CalibrationRecord restored; CHECK(m4::calibration_record::decode(bytes,restored));
  CHECK(restored.hx711.tare_counts==record.hx711.tare_counts);
  CHECK(restored.hx711.grams_per_count==record.hx711.grams_per_count && restored.water.empty_cm==40);
  bytes[13]^=1; CHECK(!m4::calibration_record::decode(bytes,restored));
}
int main() {
  conversion(); medianAndMass(); display(); faultAndTare(); persistenceCodec();
  std::printf("HX711_REFERENCE_SOFTWARE_PASS assertions=%u physical=NOT_TESTED\n",checks);
}
