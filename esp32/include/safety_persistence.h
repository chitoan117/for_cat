#pragma once

#include <Preferences.h>
#include <cmath>
#include "safety_logic.h"
#include "safety_record_codec.h"

// Arduino ESP32 NVS adapter: no feed resumes from persistent state.
// Only daily counters/time/revision are stored, not a command or actuator state.
class NvsSafetyStore final : public safety::DailyStore {
 public:
  bool load(safety::DailyRecord& value) {
    Preferences prefs;
    if (!prefs.begin("cat-safety", true)) return false;
    uint8_t bytes[safety_record::SIZE];
    bool ok = (prefs.getBytesLength("daily-v3") == sizeof(bytes) &&
               prefs.getBytes("daily-v3", bytes, sizeof(bytes)) == sizeof(bytes) &&
               safety_record::decode(bytes, value));
    // Old/raw/missing/corrupt data is not silently replaced with zero counters.
    prefs.end();
    return ok;
  }

  bool save(const safety::DailyRecord& value) override {
    uint8_t bytes[safety_record::SIZE];
    if (!safety_record::encode(value, bytes)) return false;
    Preferences prefs;
    if (!prefs.begin("cat-safety", false)) return false;
    bool ok = prefs.putBytes("daily-v3", bytes, sizeof(bytes)) == sizeof(bytes);
    prefs.end();
    return ok;
  }
};
