#pragma once
#include "io.h"

namespace m4 {
struct DateTime {
  uint16_t year = 0;
  uint8_t month = 0, day = 0, hour = 0, minute = 0, second = 0;
};
inline bool leap(uint16_t year) { return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0); }
inline uint8_t monthDays(uint16_t year, uint8_t month) {
  const uint8_t days[] = {31,28,31,30,31,30,31,31,30,31,30,31};
  if (month < 1 || month > 12) return 0;
  return month == 2 && leap(year) ? 29 : days[month-1];
}
inline bool validDate(const DateTime& time) {
  return time.year >= 2000 && time.year <= 2199 && time.month >= 1 && time.month <= 12 &&
         time.day >= 1 && time.day <= monthDays(time.year, time.month) &&
         time.hour <= 23 && time.minute <= 59 && time.second <= 59;
}
inline bool bcd(uint8_t byte, uint8_t minimum, uint8_t maximum, uint8_t& value) {
  if ((byte & 15) > 9 || (byte >> 4) > 9) return false;
  value = (byte >> 4) * 10 + (byte & 15);
  return value >= minimum && value <= maximum;
}
inline uint8_t toBcd(uint8_t value) { return static_cast<uint8_t>((value / 10) << 4 | (value % 10)); }
inline bool decodeRtc(const uint8_t (&data)[7], DateTime& output) {
  DateTime time;
  uint8_t year;
  if ((data[0] & 0x80) || (data[1] & 0x80) || (data[2] & 0x80) ||
      (data[5] & 0x60) || !bcd(data[0], 0, 59, time.second) ||
      !bcd(data[1], 0, 59, time.minute) || data[3] < 1 || data[3] > 7 ||
      !bcd(data[4], 1, 31, time.day) || !bcd(data[5] & 0x1f, 1, 12, time.month) ||
      !bcd(data[6], 0, 99, year)) return false;
  if (data[2] & 0x40) {
    uint8_t hour12;
    if (!bcd(data[2] & 0x1f, 1, 12, hour12)) return false;
    time.hour = hour12 % 12 + ((data[2] & 0x20) ? 12 : 0);
  } else if (!bcd(data[2] & 0x3f, 0, 23, time.hour)) return false;
  time.year = 2000 + year + ((data[5] & 0x80) ? 100 : 0);
  if (!validDate(time)) return false;
  output = time; return true;
}
inline uint64_t epoch(const DateTime& time) {
  if (!validDate(time)) return 0;
  uint32_t days = 0;
  for (uint16_t year = 1970; year < time.year; ++year) days += leap(year) ? 366 : 365;
  for (uint8_t month = 1; month < time.month; ++month) days += monthDays(time.year, month);
  days += time.day - 1;
  return static_cast<uint64_t>(days) * 86400 + time.hour * 3600 + time.minute * 60 + time.second;
}
inline bool encodeRtc(const DateTime& time, uint8_t (&data)[7]) {
  if (!validDate(time)) return false;
  data[0] = toBcd(time.second); data[1] = toBcd(time.minute); data[2] = toBcd(time.hour);
  data[3] = static_cast<uint8_t>((epoch(time) / 86400 + 4) % 7 + 1);
  data[4] = toBcd(time.day); data[5] = toBcd(time.month) | (time.year >= 2100 ? 0x80 : 0);
  data[6] = toBcd(time.year % 100); return true;
}

class Ds3231 {
 public:
  explicit Ds3231(I2CBus& bus) : bus_(bus) {}
  bool begin() {
    time = {};
    if (!bus_.configured()) { status = {}; return false; }
    if (!bus_.ping(address)) { status = {Health::NOT_CONNECTED, Reason::BUS_ERROR}; return false; }
    status = {Health::INITIALIZING, Reason::NONE}; return true;
  }
  bool poll(uint32_t now) {
    time = {};
    if (!bus_.configured()) { status = {}; return false; }
    uint8_t raw[7], rtc_status;
    DateTime decoded;
    if (!bus_.readRegisters(address, 0, raw, 7) || !bus_.readRegisters(address, 0x0f, &rtc_status, 1)) {
      status = {Health::NOT_CONNECTED, Reason::BUS_ERROR}; return false;
    }
    if ((rtc_status & 0x80) || !decodeRtc(raw, decoded)) {
      status = {Health::FAULT, Reason::INVALID_DATA}; return false;
    }
    time = {true, decoded, now, true}; status = {Health::HEALTHY, Reason::NONE}; return true;
  }
  bool set(const DateTime& explicit_time) {
    time = {}; // failed writes must not leave an earlier reading usable
    uint8_t raw[7], rtc_status;
    if (!bus_.configured()) { status = {}; return false; }
    if (!encodeRtc(explicit_time, raw)) { status = {Health::FAULT, Reason::INVALID_DATA}; return false; }
    if (!bus_.readRegisters(address, 0x0f, &rtc_status, 1) || !bus_.writeRegisters(address, 0, raw, 7)) {
      status = {Health::FAULT, Reason::BUS_ERROR}; return false;
    }
    rtc_status &= ~0x80; // explicitly set valid time may clear oscillator-stop indication
    if (!bus_.writeRegisters(address, 0x0f, &rtc_status, 1)) {
      status = {Health::FAULT, Reason::BUS_ERROR}; return false;
    }
    time = {}; status = {Health::INITIALIZING, Reason::NONE}; return true; // must read back
  }
  static constexpr uint8_t address = 0x68;
  Status status{};
  Reading<DateTime> time{};
 private:
  I2CBus& bus_;
};

class I2CScanner {
 public:
  explicit I2CScanner(I2CBus& bus) : bus_(bus) {}
  bool start() { if (!bus_.configured()) return false; next_ = 8; return true; }
  bool tick(uint8_t& probed, bool& found) {
    if (!bus_.configured() || next_ > 0x77) return false;
    probed = next_++; found = bus_.ping(probed); return true; // one bounded probe per tick
  }
 private:
  I2CBus& bus_;
  uint8_t next_ = 0x78;
};
}  // namespace m4
