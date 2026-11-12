#pragma once
#include <cstdint>

namespace m4 {
// Telemetry only: no species inference, feed requests, or output API.
// HC-SR501 warm-up is module/environment dependent; 60s is a conservative
// software starting point, not physical qualification of the installed module.
class PirTelemetry {
 public:
  void begin(bool raw, uint32_t now) {
    begun_=true; boot_=changed_=now; candidate_=stable_=raw; valid_=false;
  }
  void sample(bool raw, uint32_t now) {
    if (!begun_) { begin(raw,now); return; }
    if (raw!=candidate_) { candidate_=raw; changed_=now; valid_=false; }
    if (static_cast<uint32_t>(now-boot_)<60000 ||
        static_cast<uint32_t>(now-changed_)<100) return;
    stable_=candidate_; valid_=true;
  }
  bool warming(uint32_t now) const {
    return !begun_ || static_cast<uint32_t>(now-boot_)<60000;
  }
  bool valid() const { return valid_; }
  bool motion() const { return stable_; }
 private:
  uint32_t boot_=0,changed_=0;
  bool begun_=false,candidate_=false,stable_=false,valid_=false;
};
} // namespace m4
