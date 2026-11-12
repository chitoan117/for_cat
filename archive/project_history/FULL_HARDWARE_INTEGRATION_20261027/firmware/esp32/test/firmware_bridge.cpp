// Bounded host process bridge. Control records are NOT a new device protocol.
#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#if defined(HOST_ASCII)
#define M4_SENSOR_BRINGUP 1
#define M4_DIAGNOSTIC_MODE 7
#ifndef HOST_HX_INSTALLED
#define HOST_HX_INSTALLED 1
#endif
#define M4_HX711_INSTALLED HOST_HX_INSTALLED
#include "../src/diagnostics.cpp"
#else
#define M4_DIAGNOSTIC_MODE 0
#include "../src/main.cpp"
#endif
#include <fstream>
#include <iostream>
#include <sstream>
#if defined(_WIN32)
#include <io.h>
#include <fcntl.h>
#endif

namespace bridge {
namespace hw=host_board;
std::string state_file;
constexpr std::size_t max_rpc=8192,max_reply=65536,max_blob=4096,max_file=131072;
void need(bool ok,const char* message) { if (!ok) throw std::runtime_error(message); }
std::uint32_t get32(const char* p) {
  std::uint32_t n=0; for (unsigned i=0;i<4;++i) n|=static_cast<std::uint32_t>(static_cast<unsigned char>(p[i]))<<(8*i); return n;
}
void put32(std::string& out,std::uint32_t n) { for (unsigned i=0;i<4;++i) out+=static_cast<char>(n>>(8*i)); }
std::string snapshot() {
  need(hw::nvs.size()<=16,"NVS key budget"); std::string out(1,static_cast<char>(hw::nvs.size()));
  for (const auto& item:hw::nvs) {
    need(item.first.size()<=96 && item.second.size()<=256,"NVS entry budget");
    out+=static_cast<char>(item.first.size()); out+=item.first;
    out+=static_cast<char>(item.second.size()); out+=static_cast<char>(item.second.size()>>8);
    out.append(reinterpret_cast<const char*>(item.second.data()),item.second.size());
  }
  need(out.size()<=max_blob,"NVS snapshot budget"); return out;
}
bool persist() {
  if (state_file.empty()) return true;
  const auto data=snapshot(); std::string record="NV3!"; put32(record,static_cast<std::uint32_t>(data.size())); record+=data;
  const auto crc=uart_v1::crc16(reinterpret_cast<const std::uint8_t*>(record.data()),record.size());
  record+=static_cast<char>(crc); record+=static_cast<char>(crc>>8);
  std::ifstream old(state_file,std::ios::binary|std::ios::ate);
  if (old && old.tellg()>static_cast<std::streamoff>(max_file-record.size())) return false;
  std::ofstream file(state_file,std::ios::binary|std::ios::app);
  const auto size=hw::nvs_crash_stage==3?record.size()/2:record.size();
  file.write(record.data(),static_cast<std::streamsize>(size)); file.flush();
  return bool(file);
}
void restore() {
  if (state_file.empty()) return;
  std::ifstream file(state_file,std::ios::binary|std::ios::ate); if (!file) return;
  need(file.tellg()>=0 && file.tellg()<=static_cast<std::streamoff>(max_file),"NVS file budget");
  const auto size=static_cast<std::size_t>(file.tellg()); std::string data(size,'\0'); file.seekg(0); file.read(&data[0],static_cast<std::streamsize>(size));
  std::size_t cursor=0;
  while (cursor+10<=data.size()) {
    if (data.compare(cursor,4,"NV3!")!=0) break;
    const auto n=get32(data.data()+cursor+4);
    if (n>max_blob || cursor+10+n>data.size()) break;
    const auto checksum=static_cast<std::uint16_t>(static_cast<unsigned char>(data[cursor+8+n]) |
        static_cast<unsigned>(static_cast<unsigned char>(data[cursor+9+n]))<<8);
    if (uart_v1::crc16(reinterpret_cast<const std::uint8_t*>(data.data()+cursor),8+n)!=checksum) break;
    const auto blob=data.substr(cursor+8,n); if (blob.empty()) break;
    const auto count=static_cast<unsigned char>(blob[0]); need(count<=16,"NVS key count");
    std::map<std::string,std::vector<std::uint8_t>> next; std::size_t pos=1;
    for (unsigned i=0;i<count;++i) {
      need(pos<blob.size(),"truncated NVS key"); const auto length=static_cast<unsigned char>(blob[pos++]);
      need(length<=96 && pos+length+2<=blob.size(),"NVS key length"); const auto key=blob.substr(pos,length); pos+=length;
      const auto bytes=static_cast<unsigned>(static_cast<unsigned char>(blob[pos])) |
          static_cast<unsigned>(static_cast<unsigned char>(blob[pos+1]))<<8; pos+=2;
      need(bytes<=256 && pos+bytes<=blob.size(),"NVS value length");
      next[key]=std::vector<std::uint8_t>(blob.begin()+static_cast<std::ptrdiff_t>(pos),blob.begin()+static_cast<std::ptrdiff_t>(pos+bytes)); pos+=bytes;
    }
    need(pos==blob.size(),"extra NVS snapshot bytes"); hw::nvs=next; cursor+=n+10;
  }
  // Ignore a torn trailing transaction; resume from the last complete host commit.
  if (cursor<data.size()) { std::ofstream clean(state_file,std::ios::binary|std::ios::trunc); clean.write(data.data(),static_cast<std::streamsize>(cursor)); }
}
void invariant() {
  need(hw::touches[6]==0 && hw::touches[7]==0,"ACTUATOR GPIO TOUCHED");
  need(Serial0.rx.size()<=4096 && Serial0.tx.size()<=262144,"serial memory budget");
  need(hw::nvs.size()<=16 && hw::adc_bits.size()<=4096,"fake hardware memory budget");
#if !defined(HOST_ASCII)
  need(!controller.feed.openRequested() && !controller.water.pumpRequested(),"ACTUATOR AUTHORIZATION");
  need(used<=MAX_FRAME,"firmware frame bound");
#endif
}
void tick(std::uint32_t ms) {
  need(ms<=10000,"advance budget"); const auto end=hw::now_us+static_cast<std::uint64_t>(ms)*1000;
  unsigned iterations=0;
  do {
    const auto before=hw::now_us; loop();
    if (hw::now_us==before) hw::now_us+=1000;
    need(++iterations<=2000000,"loop budget");
  } while (hw::now_us<end || !Serial0.rx.empty());
  invariant();
}
std::string stats() {
  invariant(); std::ostringstream out;
  out<<"{\"actuator_gpio_touches\":0,\"servo_enabled\":false,\"pump_enabled\":false,\"nvs_writes\":"<<hw::nvs_writes
     <<",\"nvs_keys\":"<<hw::nvs.size()<<",\"rx_bytes\":"<<Serial0.rx.size()<<",\"tx_bytes\":"<<Serial0.tx.size()
     <<",\"hx_gpio_touches\":"<<hw::touches[4]+hw::touches[5]
     <<",\"clock_ms\":"<<millis()<<",\"rpc_limit\":8192,\"rx_limit\":4096,\"tx_limit\":262144,\"reply_limit\":65536,\"nvs_file_limit\":131072}";
  return out.str();
}
void fault(const std::string& text) {
  std::istringstream in(text); std::string name; long value=0; in>>name>>value; need(bool(in),"fault syntax");
  if (name=="nvs_read") hw::nvs_read_failure=value!=0;
  else if (name=="nvs_write") hw::nvs_write_failure=value!=0;
  else if (name=="nvs_short") hw::nvs_short_write=value!=0;
  else if (name=="nvs_crash") { need(value>=0 && value<=3,"crash stage"); hw::nvs_crash_stage=static_cast<unsigned>(value); }
   else if (name=="nvs_corrupt") { auto& bytes=hw::nvs["m4-calibration/sensors-v2"]; if (bytes.empty()) bytes.resize(39); bytes[static_cast<std::size_t>(value)%bytes.size()]^=1; need(persist(),"persist corrupt fixture"); }
   else if (name=="nvs_old") { auto& bytes=hw::nvs["m4-calibration/sensors-v2"]; need(bytes.size()==39,"missing saved record"); bytes[3]=0; need(persist(),"persist old fixture"); }
  else if (name=="hx") { need(value>=-8388608 && value<=8388607,"ADC range"); hw::queue_adc(static_cast<std::int32_t>(value)); }
  else if (name=="rtc_missing") hw::rtc.connected=value==0;
  else if (name=="rtc_halt") { if (value) hw::rtc.regs[0]|=0x80; else hw::rtc.regs[0]&=0x7f; }
  else if (name=="rtc_invalid") hw::rtc.regs[3]=value?0x32:0x17;
  else if (name=="oled") hw::oled_connected=value!=0;
  else if (name=="button") hw::button_pressed=value!=0;
  else if (name=="food_missing") hw::food_echo.missing=value!=0;
  else if (name=="water_missing") hw::water_echo.missing=value!=0;
  else if (name=="food_stuck") hw::food_echo.stuck_high=value!=0;
  else if (name=="water_stuck") hw::water_echo.stuck_high=value!=0;
  else throw std::runtime_error("unknown fault");
}
void output(const std::string& data) {
  need(data.size()<=max_reply,"reply bound"); std::string header; put32(header,static_cast<std::uint32_t>(data.size()));
  std::cout.write(header.data(),4); std::cout.write(data.data(),static_cast<std::streamsize>(data.size())); std::cout.flush();
}
} // namespace bridge
#ifndef FIRMWARE_BRIDGE_NO_MAIN
int main(int argc,char** argv) {
  try {
#if defined(_WIN32)
    _setmode(_fileno(stdin),_O_BINARY); _setmode(_fileno(stdout),_O_BINARY);
#endif
    if (argc==2) bridge::state_file=argv[1]; else bridge::need(argc==1,"bridge takes optional owned NVS file only");
    bridge::restore(); host_board::nvs_commit=bridge::persist; host_board::oled_connected=true;
#if defined(HOST_ASCII)
    host_board::sensitive_acquisition=[] { return dual.busy(); };
#endif
    setup(); Serial0.tx.clear();
    for (;;) {
      char header[3]; std::cin.read(header,3); if (std::cin.eof() && std::cin.gcount()==0) break;
      bridge::need(std::cin.gcount()==3,"truncated RPC header");
      const auto n=static_cast<unsigned>(static_cast<unsigned char>(header[1])) | static_cast<unsigned>(static_cast<unsigned char>(header[2]))<<8;
      bridge::need(n<=bridge::max_rpc,"RPC bound"); std::string body(n,'\0'); if (n) std::cin.read(&body[0],n);
      bridge::need(bool(std::cin),"truncated RPC body"); std::string reply;
      if (header[0]==1) { bridge::need(n>=4 && n<=4100,"data RPC bound"); Serial0.input(body.substr(4)); bridge::tick(bridge::get32(body.data())); reply=Serial0.tx; Serial0.tx.clear(); }
      else if (header[0]==2) { bridge::need(n==4,"advance RPC"); bridge::tick(bridge::get32(body.data())); reply=Serial0.tx; Serial0.tx.clear(); }
      else if (header[0]==3) reply=bridge::stats();
      else if (header[0]==4) bridge::fault(body);
      else if (header[0]==5) { bridge::need(n==4,"partial reset clock"); host_board::now_us=static_cast<std::uint64_t>(bridge::get32(body.data()))*1000; }
      else throw std::runtime_error("unknown host RPC");
      bridge::invariant(); bridge::output(reply);
    }
    return 0;
  } catch (const std::exception& error) { std::cerr<<"HOST_BRIDGE_FAIL: "<<error.what()<<'\n'; return 1; }
}
#endif
