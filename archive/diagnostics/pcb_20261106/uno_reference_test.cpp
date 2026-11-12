#include <assert.h>
#include <stdint.h>
#include <math.h>
#include <stdio.h>
#undef isfinite
namespace std { inline bool isfinite(double x){return __builtin_isfinite(x);} inline double fabs(double x){return __builtin_fabs(x);} }
template<class T> struct Reading { bool valid;T value;uint32_t sampled_at_ms;bool fresh; };
bool rawValid(double raw){return std::isfinite(raw)&&raw>=-8388608&&raw<=8388607;}
struct ScaleCalibration {double tare_counts=-668483,grams_per_count=1.0/-1064.4473;bool valid()const{return true;}};
class Hx711Median3 {
 public:
  void reset() {
    count_ = 0;
  }

  bool add(int32_t raw, int32_t& result) {
    values_[count_++] = raw;

    if (count_ != 3) return false;

    count_ = 0;

    int32_t a = values_[0];
    int32_t b = values_[1];
    int32_t c = values_[2];
    int32_t t;

    if (a > b) {
      t = a; a = b; b = t;
    }

    if (b > c) {
      t = b; b = c; c = t;
    }

    if (a > b) {
      t = a; a = b; b = t;
    }

    result = b;
    return true;
  }

 private:
  int32_t values_[3]{};
  uint8_t count_ = 0;
};
inline Reading<float> hx711SignedGrams(
    const ScaleCalibration& calibration,
    double raw,
    uint32_t now) {

  if (!calibration.valid() || !rawValid(raw)) return {};

  const double scale_factor =
    1.0 / calibration.grams_per_count;

  const double grams =
    (raw - calibration.tare_counts) / scale_factor;

  if (!std::isfinite(scale_factor)
      || scale_factor == 0
      || !std::isfinite(grams)
      || std::fabs(grams) > 100000) {
    return {};
  }

  return {true, static_cast<float>(grams), now, true};
}
class Hx711ReferenceDisplay {
 public:
  static constexpr float ZERO_DEADBAND = 0.20f;
  static constexpr float FAST_CHANGE_THRESHOLD = 1.0f;
  static constexpr float STABLE_ALPHA = 0.40f;

  void reset() {
    displayed_ = 0;
  }

  Reading<float> update(const Reading<float>& measurement) {
    if (!measurement.valid
        || !std::isfinite(measurement.value)) {
      reset();
      return {};
    }

    if (!measurement.fresh) return {};

    float current = measurement.value;

    if (current > -ZERO_DEADBAND && current < ZERO_DEADBAND) {
      current = 0;
    }

    if (current < 0 && current > -0.5f) current = 0;

    if (std::fabs(current - displayed_)
        >= FAST_CHANGE_THRESHOLD) {
      displayed_ = current;
    } else {
      displayed_ =
        STABLE_ALPHA * current
        + (1.0f - STABLE_ALPHA) * displayed_;
    }

    if (displayed_ > -ZERO_DEADBAND
        && displayed_ < ZERO_DEADBAND) {
      displayed_ = 0;
    }

    return {
      true,
      displayed_,
      measurement.sampled_at_ms,
      true
    };
  }

 private:
  float displayed_ = 0;
};
long median3(long a, long b, long c)
{
  if (a > b)
  {
    long t = a;
    a = b;
    b = t;
  }

  if (b > c)
  {
    long t = b;
    b = c;
    c = t;
  }

  if (a > b)
  {
    long t = a;
    a = b;
    b = t;
  }

  return b;
}
float unoDisplay(float currentWeight,float& displayedWeight){
const float ZERO_DEADBAND = 0.20;
const float FAST_CHANGE_THRESHOLD = 1.0;
const float STABLE_ALPHA = 0.40;
  if (currentWeight > -ZERO_DEADBAND &&
      currentWeight < ZERO_DEADBAND)
  {
    currentWeight = 0.0;
  }


  // Khong cho am nhe
  if (currentWeight < 0.0 &&
      currentWeight > -0.5)
  {
    currentWeight = 0.0;
  }


  // -------------------------------
  // PHAT HIEN THAY DOI LON
  // -------------------------------
  float difference =
      currentWeight - displayedWeight;

  if (difference < 0)
    difference = -difference;


  if (difference >= FAST_CHANGE_THRESHOLD)
  {
    // THAY DOI LON:
    // DAT / LAY VAT -> CAP NHAT NGAY
    displayedWeight = currentWeight;
  }
  else
  {
    // THAY DOI NHO:
    // Chi la nhieu -> loc nhe
    displayedWeight =
        STABLE_ALPHA * currentWeight +
        (1.0 - STABLE_ALPHA) * displayedWeight;
  }


  // Gan 0 thi ep ve 0
  if (displayedWeight > -ZERO_DEADBAND &&
      displayedWeight < ZERO_DEADBAND)
  {
    displayedWeight = 0.0;
  }


  // -------------------------------

return displayedWeight;
}
int main(){
 Hx711Median3 m;int32_t out=0;
 for(int a=-2;a<=2;a++)for(int b=-2;b<=2;b++)for(int c=-2;c<=2;c++){
   m.reset();assert(!m.add(a,out));assert(!m.add(b,out));assert(m.add(c,out));assert(out==median3(a,b,c));
 }
 ScaleCalibration cal;Hx711ReferenceDisplay d;float golden=0;
 float weights[]={0,0.19f,-0.19f,-0.49f,-0.51f,0.5f,0.8f,1.8f,38,38.2f,37.9f,20,0,-2,999,0};
 for(int repetition=0;repetition<100;repetition++)for(float g:weights){
   int32_t raw=(int32_t)(-668483.0+g*-1064.4473);
   float expected=((float)(raw-(-668483)))/-1064.4473f;
   auto measured=hx711SignedGrams(cal,raw,123);
   assert(measured.valid&&__builtin_fabsf(measured.value-expected)<0.001f);
   auto actual=d.update(measured);
   assert(actual.valid&&__builtin_fabsf(actual.value-unoDisplay(expected,golden))<0.002f);
 }
 assert(!d.update({false,0,0,true}).valid);
 assert(!d.update({true,NAN,0,true}).valid);
 assert(!d.update({true,10,0,false}).valid);
 puts("PASS: all median3 permutations;1600 signed conversion/display comparisons against actual UNO source; invalid/nonfresh sample rejection");
}
