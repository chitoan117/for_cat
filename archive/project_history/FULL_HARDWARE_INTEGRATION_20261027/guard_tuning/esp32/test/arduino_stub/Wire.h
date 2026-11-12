#pragma once
#include "Arduino.h"
#include <cstring>
class HostWire {
 public:
  bool begun=false;
  std::uint8_t address=0;
  void setTimeOut(std::uint16_t) {}
  bool begin(int sda,int scl,unsigned long) { begun=sda==8 && scl==9; return begun; }
  void beginTransmission(std::uint8_t next) { host_board::other_work(); address=next; }
  std::size_t write(std::uint8_t) { return 1; }
  std::size_t write(const std::uint8_t*,std::size_t count) { return count; }
  std::uint8_t endTransmission(bool) {
    ++host_board::oled_packets;
    return begun && address==0x3c && host_board::oled_connected ? 0 : 2;
  }
  std::size_t requestFrom(std::uint8_t,std::uint8_t,std::uint8_t) { return 0; }
  int available() const { return 0; }
  int read() { return -1; }
};
inline HostWire Wire;
