#pragma once
#include <array>
#include "m4/ds1302.h"

// Pin-level DS1302 emulator: latch command/data on rising edges, push data on falling.
// This is fake I/O evidence, never a physical timing/accuracy PASS.
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
      if(output_mode[17]) ++contention; // catches too-late turnaround on last command falling edge
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

void ds1302Regression() {
  using namespace m4;
  CHECK(ds1302_register::SECONDS_WRITE==0x80 && ds1302_register::SECONDS_READ==0x81);
  CHECK(ds1302_register::MINUTES_WRITE==0x82 && ds1302_register::MINUTES_READ==0x83);
  CHECK(ds1302_register::HOURS_WRITE==0x84 && ds1302_register::HOURS_READ==0x85);
  CHECK(ds1302_register::DATE_WRITE==0x86 && ds1302_register::DATE_READ==0x87);
  CHECK(ds1302_register::MONTH_WRITE==0x88 && ds1302_register::MONTH_READ==0x89);
  CHECK(ds1302_register::WEEKDAY_WRITE==0x8a && ds1302_register::WEEKDAY_READ==0x8b);
  CHECK(ds1302_register::YEAR_WRITE==0x8c && ds1302_register::YEAR_READ==0x8d);
  CHECK(ds1302_register::CONTROL_WRITE==0x8e && ds1302_register::CONTROL_READ==0x8f);
  CHECK(ds1302_register::CLOCK_BURST_WRITE==0xbe && ds1302_register::CLOCK_BURST_READ==0xbf);
  for(uint8_t number=0;number<60;++number) { uint8_t result; CHECK(bcd(toBcd(number),0,59,result) && result==number); }
  uint8_t raw[8]; DateTime restored;
  CHECK(encodeDs1302({2026,10,9,14,35,57},raw)); CHECK(decodeDs1302(raw,restored)); CHECK(restored.year==2026 && restored.hour==14);
  CHECK(encodeDs1302({2024,2,29,23,59,59},raw)); CHECK(decodeDs1302(raw,restored));
  CHECK(!encodeDs1302({2025,2,29,0,0,0},raw)); CHECK(!encodeDs1302({2100,1,1,0,0,0},raw));
  const auto invalid=[&](unsigned index,uint8_t bad) {
    uint8_t data[8]; CHECK(encodeDs1302({2026,10,9,14,35,57},data)); data[index]=bad;
    DateTime unchanged{2020,1,1,0,0,0}; CHECK(!decodeDs1302(data,unchanged)); CHECK(unchanged.year==2020);
  };
  invalid(0,0x60); invalid(0,0x1a); invalid(1,0x60); invalid(1,0x80); invalid(2,0x24); invalid(2,0x40);
  invalid(3,0); invalid(3,0x32); invalid(4,0x13); invalid(4,0); invalid(5,0); invalid(5,8); invalid(6,0xfa); invalid(7,1);
  CHECK(encodeDs1302({2026,10,9,0,0,0},raw)); raw[2]=0x92; CHECK(decodeDs1302(raw,restored) && restored.hour==0); //12AM
  raw[2]=0xb2; CHECK(decodeDs1302(raw,restored) && restored.hour==12); //12PM
  raw[0]|=0x80; CHECK(!decodeDs1302(raw,restored)); //CH cannot produce valid time
  Ds1302Pins io; Ds1302 rtc(io);
  CHECK(!rtc.begin()); CHECK(!rtc.poll(100)); CHECK(io.operations==0);
  CHECK(!rtc.begin({{16,true},{16,true},{18,true}})); CHECK(io.operations==0);
  CHECK(!rtc.begin({{16,true},{17,false},{18,true}})); CHECK(io.operations==0);
  io.data_output_allowed=false; CHECK(!rtc.begin({{16,true},{17,true},{18,true}})); CHECK(io.operations==0);
  io.data_output_allowed=true;
  CHECK(rtc.begin({{16,true},{17,true},{18,true}})); CHECK(io.history.empty()); //begin writes noRTC registers
  CHECK(rtc.poll(100)); CHECK(rtc.time.valid && rtc.time.value.second==56 && rtc.write_protected);
  CHECK(io.history.size()==1 && io.history[0].command==0xbf && io.history[0].data.empty());
  CHECK(io.history[0].command_bits==std::vector<bool>({true,true,true,true,true,true,false,true}));
  CHECK(io.contention==0 && io.input_reads==64 && !io.output_mode[17] && !io.levels[16] && !io.levels[18] && io.bad_timing==0);
  const auto old=io.regs; CHECK(rtc.poll(101)); CHECK(io.regs==old); //normalpoll never clearsWP/CH
  io.regs[0]|=0x80; CHECK(!rtc.poll(102)); CHECK(rtc.status.reason==Reason::CLOCK_HALTED && !rtc.time.valid);
  const DateTime set_time{2026,10,9,15,42,13}; const size_t start=io.history.size();
  CHECK(rtc.set(set_time,103)); CHECK(rtc.time.valid && rtc.time.value.year==2026 && rtc.time.value.second==13 && rtc.write_protected);
  CHECK((io.regs[0]&0x80)==0 && io.regs[7]==0x80);
  CHECK(io.history[start].command==0x8f && io.history[start+1].command==0x8e && io.history[start+1].data==std::vector<uint8_t>({0}));
  CHECK(io.history[start+2].command==0x8f && io.history[start+3].command==0xbe && io.history[start+3].data.size()==8);
  CHECK(io.history[start+4].command==0x8e && io.history[start+4].data==std::vector<uint8_t>({0x80}) && io.history[start+5].command==0xbf);
  CHECK(io.contention==0 && !io.output_mode[17]);
  for(const auto& transaction:io.history) CHECK(transaction.command!=0x90 && transaction.command!=0x91); //nocharger
  io.regs[7]=0; CHECK(rtc.set({2024,2,29,0,0,0},104)); CHECK(!rtc.write_protected && io.regs[7]==0);
  io.regs[7]=0x80; io.stuck_wp=true;
  CHECK(!rtc.set(set_time,105)); CHECK(rtc.status.reason==Reason::WRITE_PROTECTED && !rtc.time.valid); io.stuck_wp=false;
  io.ignore_clock_write=true; CHECK(!rtc.set(set_time,106)); CHECK(rtc.status.reason==Reason::READBACK_MISMATCH && !rtc.time.valid);
  io.ignore_clock_write=false; io.regs[3]=0x32; CHECK(!rtc.poll(107)); CHECK(rtc.status.reason==Reason::RTC_INVALID_TIME);
  io.regs[7]=1; CHECK(!rtc.poll(108)); CHECK(rtc.status.reason==Reason::RTC_IO_ERROR);
  io.connected=false; CHECK(!rtc.poll(109)); CHECK(rtc.status.health==Health::NOT_CONNECTED && !rtc.time.valid);
  io.zero_bus=true; CHECK(!rtc.poll(110)); CHECK(!rtc.set(set_time,111)); CHECK(!rtc.time.valid);
  io.connected=true; io.zero_bus=false; io.regs[7]=0;
  CHECK(rtc.set(set_time,112));
  SensorSnapshot snapshot; snapshot.sampled_at_ms=112; snapshot.rtc=rtc.status; snapshot.rtc_time=rtc.time;
  snapshot.load_cell=snapshot.food={Health::HEALTHY,Reason::NONE}; snapshot.grams={true,10,112,true}; snapshot.food_percent={true,50,112,true};
  CHECK(feedInputs(snapshot).rtc_valid && feedInputs(snapshot).day==20261009 && feedInputs(snapshot).epoch_seconds==epoch(set_time));
  CounterStore store; safety::FeedController feed; feed.attachStore(store); safety::DailyRecord record; record.day=20261009;
  feed.boot(record); feed.tick(feedInputs(snapshot,true)); CHECK(feed.state()==safety::FeedState::IDLE);
  io.regs[0]|=0x80; CHECK(!rtc.poll(113)); snapshot.rtc=rtc.status; snapshot.rtc_time=rtc.time;
  CHECK(!feedInputs(snapshot).rtc_valid); CHECK(feed.request(99,10,feedInputs(snapshot,true)));
  CHECK(feed.reason()==safety::FeedReason::RTC_INVALID && !feed.openRequested());
}
