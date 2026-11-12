#pragma once
#include <array>
#include <vector>
#include <stdexcept>
#include "m4/ds1302.h"

// Shared pin-level test emulator, not a physical timing/accuracy certification.
struct Ds1302Pins : m4::PinIO {
  struct Transaction { uint8_t command=0; std::vector<bool> command_bits; std::vector<uint8_t> data; };
  std::array<uint8_t,8> regs{{0x56,0x34,0x12,0x29,0x02,0x05,0x24,0x80}};
  std::vector<Transaction> history;
  bool output_mode[64]{}, levels[64]{};
  bool connected=true, zero_bus=false, ignore_clock_write=false, stuck_wp=false, data_output_allowed=true;
  unsigned operations=0, contention=0, input_reads=0, bad_timing=0;
  bool reading=false, prepared=false, device_driving=false, device_bit=false;
  unsigned command_count=0, write_bit=0, read_bit=0;
  uint8_t command=0, written=0;
  std::vector<uint8_t> receive;
  Transaction current;
  bool inputAllowed(int pin) const override { return pin>=0 && pin<32; }
  bool outputAllowed(int pin) const override { return inputAllowed(pin) && (pin!=17 || data_output_allowed); }
  void input(int pin,m4::Pull) override { ++operations; output_mode[pin]=false; }
  void output(int pin) override { ++operations; if(pin==17 && device_driving) ++contention; output_mode[pin]=true; }
  void pauseMicros(uint32_t delay) override { if(delay!=4) ++bad_timing; }
  void enterCritical() override {}
  void exitCritical() override {}
  bool read(int pin) override {
    ++operations;
    if(pin==17) {
      ++input_reads;
      if(output_mode[pin] || !device_driving || levels[16]) ++contention;
      return device_bit;
    }
    return levels[pin];
  }
  void commit() {
    if(!reading && connected && !zero_bus) {
      if(command==0x8e && current.data.size()==1 && !stuck_wp) regs[7]=static_cast<uint8_t>(current.data[0]&0x80);
      if(command==0xbe && current.data.size()==8 && !(regs[7]&0x80) && !ignore_clock_write)
        for(unsigned i=0;i<8;++i) regs[i]=current.data[i];
    }
    if (history.size()>=2048) throw std::runtime_error("test RTC history budget exceeded");
    history.push_back(current); device_driving=false;
  }
  void rising() {
    device_driving=false;
    if(command_count<8) {
      if(!output_mode[17]) ++contention;
      const bool bit=levels[17]; current.command_bits.push_back(bit);
      if(bit) command=static_cast<uint8_t>(command|(1u<<command_count));
      ++command_count;
      if(command_count==8) {
        current.command=command; reading=(command&1)!=0;
        if(reading) {
          receive.clear();
          if(command==0xbf) receive.assign(regs.begin(),regs.end());
          else if(command==0x8f) receive.push_back(regs[7]);
          else receive.push_back(0xff);
          if(!connected || zero_bus) for(auto& byte:receive) byte=zero_bus ? 0 : 0xff;
          prepared=false; read_bit=0;
        }
      }
    } else if(!reading) {
      if(!output_mode[17]) ++contention;
      if(levels[17]) written=static_cast<uint8_t>(written|(1u<<write_bit));
      if(++write_bit==8) { current.data.push_back(written); write_bit=0; written=0; }
    }
  }
  void falling() {
    if(reading && command_count==8) {
      if(output_mode[17]) ++contention;
      if(prepared) ++read_bit;
      prepared=true; device_driving=true;
      const unsigned index=(read_bit/8)%static_cast<unsigned>(receive.size());
      device_bit=(receive[index]&(1u<<(read_bit%8)))!=0;
    }
  }
  void write(int pin,bool high) override {
    ++operations;
    if(pin==17 && levels[18] && device_driving) ++contention;
    const bool previous=levels[pin]; levels[pin]=high;
    if(pin==18 && high && !previous) {
      if(levels[16]) ++contention;
      current={}; reading=false; command_count=write_bit=read_bit=0; command=written=0; device_driving=false;
    } else if(pin==18 && !high && previous) commit();
    else if(pin==16 && levels[18]) {
      if(high && !previous) rising();
      if(!high && previous) falling();
    }
  }
};
