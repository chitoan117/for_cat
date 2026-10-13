#pragma once
#include <cstring>
#include "io.h"
#include "snapshot.h"

namespace m4 {
class Ssd1306 {
 public:
  explicit Ssd1306(I2CBus& bus) : bus_(bus) {}
  bool begin(uint8_t address, uint8_t height) {
    ready_ = false;
    if (!bus_.configured() || (address != 0x3c && address != 0x3d) || (height != 32 && height != 64)) {
      status = {}; return false;
    }
    address_ = address; height_ = height;
    if (!bus_.ping(address)) { status = {Health::NOT_CONNECTED, Reason::BUS_ERROR}; return false; }
    const uint8_t init[] = {0xae,0xd5,0x80,0xa8,static_cast<uint8_t>(height-1),0xd3,0x00,0x40,
                           0x8d,0x14,0x20,0x00,0xa1,0xc8,0xda,static_cast<uint8_t>(height==64 ? 0x12 : 0x02),
                           0x81,0x7f,0xd9,0xf1,0xdb,0x40,0xa4,0xa6,0xaf};
    if (!bus_.packet(address_, 0, init, sizeof(init))) { fail(); return false; }
    ready_ = true; status = {Health::INITIALIZING, Reason::NONE};
    clear(); return true;
  }
  void clear() { std::memset(buffer_, 0, sizeof(buffer_)); cursor_ = 0; dirty_ = true; window_ = false; }
  void line(uint8_t page, const char* text) {
    if (!ready_ || page >= height_/8 || !text) return;
    uint8_t column = 0;
    for (size_t i = 0; text[i] && column + 6 <= 128; ++i) {
      uint8_t glyph[5]{}; font(text[i], glyph);
      for (uint8_t x = 0; x < 5; ++x) buffer_[page*128 + column++] = glyph[x];
      buffer_[page*128 + column++] = 0;
    }
  }
  void statusLines(const SensorSnapshot& snapshot) {
    if (!ready_) return;
    clear(); line(0, "FORR_CAT HW_SAFE");
    textStatus(1, "RTC ", snapshot.rtc.health);
    textStatus(2, "WEIGHT ", snapshot.load_cell.health);
    textStatus(3, "FOOD ", snapshot.food.health);
    if (height_ == 64) textStatus(4, "WATER ", snapshot.water.health);
  }
  void tick() {
    if (!ready_ || !dirty_) return;
    if (!window_) {
      const uint8_t window[] = {0x21,0,127,0x22,0,static_cast<uint8_t>(height_/8-1)};
      if (!bus_.packet(address_, 0, window, sizeof(window))) { fail(); return; }
      window_ = true; return;
    }
    const size_t remaining = height_ * 16 - cursor_;
    const size_t chunk = remaining > 16 ? 16 : remaining;
    if (!bus_.packet(address_, 0x40, buffer_ + cursor_, chunk)) { fail(); return; }
    cursor_ += chunk;
    if (cursor_ == height_ * 16) { dirty_ = false; status = {Health::HEALTHY, Reason::NONE}; }
  }
  Status status{}; // panel fault is NOT consumed by feed/water safety prerequisites
 private:
  static void font(char value, uint8_t (&glyph)[5]) {
    const char* alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    static const uint8_t table[][5] = {
      {0x3e,0x51,0x49,0x45,0x3e},{0,0x42,0x7f,0x40,0},{0x42,0x61,0x51,0x49,0x46},
      {0x21,0x41,0x45,0x4b,0x31},{0x18,0x14,0x12,0x7f,0x10},{0x27,0x45,0x45,0x45,0x39},
      {0x3c,0x4a,0x49,0x49,0x30},{1,0x71,9,5,3},{0x36,0x49,0x49,0x49,0x36},{6,0x49,0x49,0x29,0x1e},
      {0x7e,0x11,0x11,0x11,0x7e},{0x7f,0x49,0x49,0x49,0x36},{0x3e,0x41,0x41,0x41,0x22},
      {0x7f,0x41,0x41,0x22,0x1c},{0x7f,0x49,0x49,0x49,0x41},{0x7f,9,9,9,1},
      {0x3e,0x41,0x49,0x49,0x7a},{0x7f,8,8,8,0x7f},{0,0x41,0x7f,0x41,0},{0x20,0x40,0x41,0x3f,1},
      {0x7f,8,0x14,0x22,0x41},{0x7f,0x40,0x40,0x40,0x40},{0x7f,2,0x0c,2,0x7f},
      {0x7f,4,8,0x10,0x7f},{0x3e,0x41,0x41,0x41,0x3e},{0x7f,9,9,9,6},
      {0x3e,0x41,0x51,0x21,0x5e},{0x7f,9,0x19,0x29,0x46},{0x46,0x49,0x49,0x49,0x31},
      {1,1,0x7f,1,1},{0x3f,0x40,0x40,0x40,0x3f},{0x1f,0x20,0x40,0x20,0x1f},
      {0x3f,0x40,0x38,0x40,0x3f},{0x63,0x14,8,0x14,0x63},{7,8,0x70,8,7},{0x61,0x51,0x49,0x45,0x43}};
    for (size_t i = 0; alphabet[i]; ++i) if (alphabet[i] == value) { std::memcpy(glyph, table[i], 5); return; }
    if (value == '_') for (auto& column : glyph) column = 0x40;
  }
  void textStatus(uint8_t page, const char* prefix, Health health) {
    char text[32]; std::strncpy(text, prefix, sizeof(text)-1); text[sizeof(text)-1] = 0;
    std::strncat(text, name(health), sizeof(text)-std::strlen(text)-1); line(page, text);
  }
  void fail() { status = {Health::FAULT, Reason::BUS_ERROR}; ready_ = dirty_ = false; }
  I2CBus& bus_;
  uint8_t address_ = 0, height_ = 0;
  uint8_t buffer_[1024]{};
  size_t cursor_ = 0;
  bool ready_ = false, dirty_ = false, window_ = false;
};
}  // namespace m4
