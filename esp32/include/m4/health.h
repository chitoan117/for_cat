#pragma once
#include <cstdint>

namespace m4 {
constexpr int PIN_NOT_ASSIGNED = -1;
enum class Health : uint8_t {
  NOT_CONFIGURED, NOT_CONNECTED, NOT_CALIBRATED, INITIALIZING, HEALTHY, DEGRADED, FAULT
};
enum class Reason : uint8_t {
  NONE, CONFIGURATION_INVALID, TIMEOUT, BUS_ERROR, INVALID_DATA,
  NOT_CALIBRATED, GEOMETRY_INVALID, RANGE_INVALID, ACTUATORS_DISABLED
};
inline const char* name(Health health) {
  switch (health) {
    case Health::NOT_CONFIGURED: return "NOT_CONFIGURED";
    case Health::NOT_CONNECTED: return "NOT_CONNECTED";
    case Health::NOT_CALIBRATED: return "NOT_CALIBRATED";
    case Health::INITIALIZING: return "INITIALIZING";
    case Health::HEALTHY: return "HEALTHY";
    case Health::DEGRADED: return "DEGRADED";
    default: return "FAULT";
  }
}
inline const char* name(Reason reason) {
  switch (reason) {
    case Reason::NONE: return "NONE";
    case Reason::CONFIGURATION_INVALID: return "CONFIGURATION_INVALID";
    case Reason::TIMEOUT: return "TIMEOUT";
    case Reason::BUS_ERROR: return "BUS_ERROR";
    case Reason::INVALID_DATA: return "INVALID_DATA";
    case Reason::NOT_CALIBRATED: return "NOT_CALIBRATED";
    case Reason::GEOMETRY_INVALID: return "GEOMETRY_INVALID";
    case Reason::RANGE_INVALID: return "RANGE_INVALID";
    default: return "ACTUATORS_DISABLED";
  }
}
template<class T> struct Reading {
  bool valid = false;
  T value{}; // must never be emitted as a measured value unless valid=true
  uint32_t sampled_at_ms = 0;
  bool fresh = false;
};
struct Status {
  Health health = Health::NOT_CONFIGURED;
  Reason reason = Reason::CONFIGURATION_INVALID;
};
struct Pin {
  int number = PIN_NOT_ASSIGNED;
  bool reviewed = false; // configuration attestation; not a hardware-test result
};
}  // namespace m4
