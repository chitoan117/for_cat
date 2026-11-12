#pragma once
// Host-only Arduino surface for compiling the ACTUAL diagnostics.cpp setup/loop.
// This directory is never in the PlatformIO firmware include path.
#include <array>
#include <cmath>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
#include "../ds1302_fake_pins.h"

constexpr int INPUT=0, OUTPUT=1, INPUT_PULLUP=2, INPUT_PULLDOWN=3, HIGH=1, LOW=0;
using portMUX_TYPE=int;
constexpr int portMUX_INITIALIZER_UNLOCKED=0;
namespace host_board {
inline std::uint64_t now_us=0;
inline Ds1302Pins rtc;
inline std::array<bool,64> levels{};
inline std::array<unsigned,64> touches{},high_writes{};
inline std::array<std::uint64_t,64> high_at{};
inline std::deque<bool> adc_bits;
inline bool button_pressed=false, oled_connected=false,nvs_available=true;
inline bool ledc_attached=false, ledc_fail_attach=false, ledc_fail_write=false,ledc_fail_detach=false;
inline unsigned ledc_attaches=0,ledc_writes=0,ledc_detaches=0;
inline std::uint32_t ledc_duty=0;
inline bool nvs_read_failure=false,nvs_write_failure=false,nvs_short_write=false;
inline unsigned nvs_crash_stage=0;
inline bool (*nvs_commit)()=nullptr;
inline unsigned critical_depth=0,critical_errors=0,overlaps=0,other_work_during_echo=0,oled_packets=0,nvs_writes=0;
inline bool (*sensitive_acquisition)()=nullptr;
struct Echo {
  bool missing=false,stuck_high=false;
  double distance_cm=30;
  std::uint64_t rise=0,fall=0,pending_until=0;
  unsigned pulses=0;
};
inline Echo food_echo,water_echo;
inline bool pending_echo() { return now_us<food_echo.pending_until || now_us<water_echo.pending_until; }
inline void other_work() { if (sensitive_acquisition && sensitive_acquisition()) ++other_work_during_echo; }
inline std::map<std::string,std::vector<std::uint8_t>> nvs;
inline void queue_adc(std::int32_t raw) {
  if (adc_bits.size()+25>4096) throw std::runtime_error("test ADC queue budget exceeded");
  adc_bits.push_back(false);
  for (int bit=23;bit>=0;--bit) adc_bits.push_back((static_cast<std::uint32_t>(raw) >> bit & 1u)!=0);
}
inline void enter() { if (critical_depth!=0) ++critical_errors; ++critical_depth; }
inline void leave() { if (critical_depth!=1) ++critical_errors; if (critical_depth) --critical_depth; }
class SerialPort {
 public:
  std::deque<unsigned char> rx;
  std::string tx;
  void begin(unsigned long) {}
  int available() const { return static_cast<int>(rx.size()); }
  int read() { if (rx.empty()) return -1; const int b=rx.front(); rx.pop_front(); return b; }
  void append(const std::string& value) {
    other_work();
    if (tx.size()+value.size()>262144) throw std::runtime_error("test serial budget exceeded");
    tx+=value;
  }
  void print(const char* text) { append(text); }
  std::size_t write(const std::uint8_t* bytes,std::size_t count) {
    append(std::string(reinterpret_cast<const char*>(bytes),count)); return count;
  }
  void println(const char* text) { append(std::string(text)+"\r\n"); }
  void printf(const char* format,...) {
    char text[4096]; va_list args; va_start(args,format);
    const int n=std::vsnprintf(text,sizeof(text),format,args); va_end(args);
    if (n<0 || static_cast<std::size_t>(n)>=sizeof(text)) throw std::runtime_error("test printf budget exceeded");
    append(text);
  }
  void input(const std::string& text) {
    if (rx.size()+text.size()>4096) throw std::runtime_error("test serial RX budget exceeded");
    for (char c:text) rx.push_back(static_cast<unsigned char>(c));
  }
};
} // namespace host_board
inline host_board::SerialPort Serial0,Serial;
inline std::uint32_t micros() { return static_cast<std::uint32_t>(host_board::now_us); }
inline std::uint32_t millis() { return static_cast<std::uint32_t>(host_board::now_us/1000); }
inline void delay(unsigned long ms) { host_board::now_us+=ms*1000ULL; }
inline void delayMicroseconds(std::uint32_t us) {
  if (us>10) throw std::runtime_error("unbounded driver delay in host test");
  host_board::now_us+=us;
}
inline void yield() { ++host_board::now_us; }
inline void pinMode(int pin,int mode) {
  using namespace host_board;
  if (pin<0 || pin>=64) throw std::runtime_error("invalid host GPIO");
  ++touches[static_cast<std::size_t>(pin)];
  if (pin>=16 && pin<=18) {
    other_work();
    if (mode==OUTPUT) rtc.output(pin); else rtc.input(pin,m4::Pull::NONE);
  }
}
inline int digitalRead(int pin) {
  using namespace host_board;
  if (pin<0 || pin>=64) throw std::runtime_error("invalid host GPIO");
  ++touches[static_cast<std::size_t>(pin)];
  if (pin>=16 && pin<=18) { other_work(); return rtc.read(pin)?HIGH:LOW; }
  if (pin==4) {
    other_work();
    if (adc_bits.empty()) return HIGH;
    const bool bit=adc_bits.front(); adc_bits.pop_front(); return bit?HIGH:LOW;
  }
  if (pin==11) { other_work(); return levels[11]?HIGH:LOW; }
  if (pin==13 || pin==15) {
    const auto& echo=pin==13 ? food_echo : water_echo;
    return (echo.stuck_high || (!echo.missing && now_us>=echo.rise && now_us<echo.fall))?HIGH:LOW;
  }
  return levels[static_cast<std::size_t>(pin)]?HIGH:LOW;
}
inline void digitalWrite(int pin,int value) {
  using namespace host_board;
  if (pin<0 || pin>=64) throw std::runtime_error("invalid host GPIO");
  const auto index=static_cast<std::size_t>(pin);
  ++touches[index];
  if (value==HIGH) ++high_writes[index];
  if (pin>=16 && pin<=18) { other_work(); rtc.write(pin,value==HIGH); }
  if (pin==5) other_work();
  const bool previous=levels[index]; levels[index]=value==HIGH;
  if (value==HIGH && !previous) high_at[index]=now_us;
  if ((pin==12 || pin==14) && previous && value==LOW && now_us-high_at[index]>=10) {
    auto& echo=pin==12 ? food_echo : water_echo;
    if (pending_echo()) ++overlaps;
    ++echo.pulses; echo.rise=now_us+150;
    echo.fall=echo.rise+static_cast<std::uint64_t>(std::llround(echo.distance_cm*2/0.0343));
    echo.pending_until=echo.missing?now_us+30000:echo.fall;
  }
}
inline bool ledcAttach(std::uint8_t pin,std::uint32_t hz,std::uint8_t resolution) {
  if (pin!=6 || hz!=50 || resolution!=16 || host_board::ledc_attached)
    throw std::runtime_error("unexpected LEDC pin/timer/configuration");
  ++host_board::ledc_attaches;
  if (host_board::ledc_fail_attach) return false;
  host_board::ledc_attached=true; return true;
}
inline bool ledcWrite(std::uint8_t pin,std::uint32_t duty) {
  if (pin!=6 || !host_board::ledc_attached || duty>65535)
    throw std::runtime_error("LEDC without isolated attached servo pin");
  ++host_board::ledc_writes;
  if (host_board::ledc_fail_write) return false;
  host_board::ledc_duty=duty; return true;
}
inline bool ledcDetach(std::uint8_t pin) {
  if (pin!=6 || !host_board::ledc_attached)
    throw std::runtime_error("LEDC unexpected detach");
  ++host_board::ledc_detaches; host_board::ledc_attached=false;
  if (host_board::ledc_fail_detach) { host_board::ledc_attached=true; return false; }
  host_board::ledc_duty=0; return true;
}
#define portENTER_CRITICAL(mux) do { (void)(mux); host_board::enter(); } while (0)
#define portEXIT_CRITICAL(mux) do { (void)(mux); host_board::leave(); } while (0)
