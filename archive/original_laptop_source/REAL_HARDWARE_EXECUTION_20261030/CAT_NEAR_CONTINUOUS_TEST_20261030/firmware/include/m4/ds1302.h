#pragma once
#include "rtc.h"

// Restored from the previously tested Windows DS1302 implementation.
// ADI/Maxim DS1302 datasheet Rev3/15. Serial reads have no hardware ACK.
namespace m4 {
namespace ds1302_register {
constexpr uint8_t SECONDS_WRITE=0x80, SECONDS_READ=0x81;
constexpr uint8_t MINUTES_WRITE=0x82, MINUTES_READ=0x83;
constexpr uint8_t HOURS_WRITE=0x84, HOURS_READ=0x85;
constexpr uint8_t DATE_WRITE=0x86, DATE_READ=0x87;
constexpr uint8_t MONTH_WRITE=0x88, MONTH_READ=0x89;
constexpr uint8_t WEEKDAY_WRITE=0x8a, WEEKDAY_READ=0x8b;
constexpr uint8_t YEAR_WRITE=0x8c, YEAR_READ=0x8d;
constexpr uint8_t CONTROL_WRITE=0x8e, CONTROL_READ=0x8f;
constexpr uint8_t CLOCK_BURST_WRITE=0xbe, CLOCK_BURST_READ=0xbf;
constexpr uint8_t CH=0x80, WP=0x80;
}
inline bool decodeDs1302(const uint8_t (&raw)[8], DateTime& output) {
  DateTime time; uint8_t year;
  if ((raw[0]&0x80) || (raw[1]&0x80) || (raw[2]&0x40) || (raw[3]&0xc0) ||
      (raw[4]&0xe0) || (raw[5]&0xf8) || (raw[7]&0x7f) ||
      !bcd(raw[0],0,59,time.second) || !bcd(raw[1],0,59,time.minute) ||
      !bcd(raw[3],1,31,time.day) || !bcd(raw[4],1,12,time.month) ||
      raw[5]<1 || raw[5]>7 || !bcd(raw[6],0,99,year)) return false;
  if (raw[2]&0x80) {
    uint8_t hour12;
    if (!bcd(raw[2]&0x1f,1,12,hour12)) return false;
    time.hour=static_cast<uint8_t>(hour12%12+((raw[2]&0x20) ? 12 : 0));
  } else if (!bcd(raw[2]&0x3f,0,23,time.hour)) return false;
  time.year=static_cast<uint16_t>(2000+year);
  if (!validDate(time)) return false;
  output=time; return true;
}
inline bool encodeDs1302(const DateTime& time, uint8_t (&raw)[8]) {
  if (!validDate(time) || time.year>2099) return false;
  raw[0]=toBcd(time.second); raw[1]=toBcd(time.minute); raw[2]=toBcd(time.hour);
  raw[3]=toBcd(time.day); raw[4]=toBcd(time.month);
  raw[5]=static_cast<uint8_t>((epoch(time)/86400+4)%7+1);
  raw[6]=toBcd(static_cast<uint8_t>(time.year-2000)); raw[7]=0; return true;
}
struct Ds1302Config { Pin clk{}, dat{}, ce{}; };
class Ds1302 {
 public:
  explicit Ds1302(PinIO& io) : io_(io) {}
  bool begin(Ds1302Config config={}) {
    active_=false; time={}; write_protected=false; clock_halted=false; config_=config;
    if (!outputValid(io_,config.clk) || !outputValid(io_,config.ce) ||
        !inputValid(io_,config.dat) || !outputValid(io_,config.dat) ||
        config.clk.number==config.dat.number || config.clk.number==config.ce.number || config.dat.number==config.ce.number) {
      status={}; return false;
    }
    io_.output(config.clk.number); io_.write(config.clk.number,false);
    io_.output(config.ce.number); io_.write(config.ce.number,false);
    io_.input(config.dat.number,Pull::NONE);
    active_=true; status={Health::INITIALIZING,Reason::NONE}; return true;
  }
  bool poll(uint32_t now) {
    time={}; write_protected=clock_halted=false;
    if (!active_) { status={}; return false; }
    uint8_t raw[8]; readBytes(ds1302_register::CLOCK_BURST_READ,raw,8);
    bool zeros=true, ones=true;
    for (uint8_t value : raw) { zeros=zeros && value==0; ones=ones && value==0xff; }
    if (zeros || ones) { status={Health::NOT_CONNECTED,Reason::NO_RESPONSE}; return false; }
    write_protected=(raw[7]&ds1302_register::WP)!=0; clock_halted=(raw[0]&ds1302_register::CH)!=0;
    if (raw[7]&0x7f) { status={Health::FAULT,Reason::RTC_IO_ERROR}; return false; }
    if (clock_halted) { status={Health::FAULT,Reason::CLOCK_HALTED}; return false; }
    DateTime decoded;
    if (!decodeDs1302(raw,decoded)) { status={Health::FAULT,Reason::RTC_INVALID_TIME}; return false; }
    time={true,decoded,now,true}; status={Health::HEALTHY,Reason::NONE}; return true;
  }
  bool set(const DateTime& explicit_time, uint32_t now=0) {
    time={};
    if (!active_) { status={}; return false; }
    uint8_t raw[8];
    if (!encodeDs1302(explicit_time,raw)) { status={Health::FAULT,Reason::RTC_INVALID_TIME}; return false; }
    uint8_t previous; readBytes(ds1302_register::CONTROL_READ,&previous,1);
    if (previous&0x7f) { status={Health::FAULT,Reason::RTC_IO_ERROR}; return false; }
    const uint8_t unprotected=0;
    writeBytes(ds1302_register::CONTROL_WRITE,&unprotected,1);
    uint8_t check; readBytes(ds1302_register::CONTROL_READ,&check,1);
    if (check!=0) { status={Health::FAULT,Reason::WRITE_PROTECTED}; return false; }
    writeBytes(ds1302_register::CLOCK_BURST_WRITE,raw,8);
    const uint8_t restored=static_cast<uint8_t>(previous&ds1302_register::WP);
    writeBytes(ds1302_register::CONTROL_WRITE,&restored,1);
    if (!poll(now)) return false;
    const uint64_t wanted=epoch(explicit_time), actual=epoch(time.value);
    if (actual<wanted || actual-wanted>1 || write_protected!=(restored!=0)) {
      time={}; status={Health::FAULT,Reason::READBACK_MISMATCH}; return false;
    }
    return true;
  }
  Status status{};
  Reading<DateTime> time{};
  bool write_protected=false, clock_halted=false;
 private:
  void pause() { io_.pauseMicros(4); }
  void start() {
    io_.write(config_.ce.number,false); io_.write(config_.clk.number,false);
    io_.output(config_.dat.number); pause(); io_.write(config_.ce.number,true); pause();
  }
  void finish() {
    io_.write(config_.ce.number,false); pause();
    io_.write(config_.clk.number,false); io_.input(config_.dat.number,Pull::NONE);
  }
  void transmit(uint8_t value, bool read_turnaround=false) {
    for (unsigned bit=0;bit<8;++bit) {
      io_.write(config_.dat.number,(value&(1u<<bit))!=0); pause();
      io_.write(config_.clk.number,true); pause();
      if (bit==7 && read_turnaround) io_.input(config_.dat.number,Pull::NONE);
      io_.write(config_.clk.number,false); pause();
    }
  }
  void readBytes(uint8_t command, uint8_t* output, unsigned count) {
    start(); transmit(command,true);
    for (unsigned byte=0;byte<count;++byte) {
      uint8_t value=0;
      for (unsigned bit=0;bit<8;++bit) {
        if (io_.read(config_.dat.number)) value=static_cast<uint8_t>(value|(1u<<bit));
        io_.write(config_.clk.number,true); pause();
        io_.write(config_.clk.number,false); pause();
      }
      output[byte]=value;
    }
    finish();
  }
  void writeBytes(uint8_t command, const uint8_t* values, unsigned count) {
    start(); transmit(command);
    for (unsigned index=0;index<count;++index) transmit(values[index]);
    finish();
  }
  PinIO& io_;
  Ds1302Config config_{};
  bool active_=false;
};
} // namespace m4
