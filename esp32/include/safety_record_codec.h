#pragma once
#include <cstring>
#include "safety_logic.h"
#include "uart_v1.h"

// Portable NVS envelope (NOT UART). Explicit v3, CRC, no compiler struct padding.
namespace safety_record {
constexpr size_t SIZE = 25;
inline bool valid(const safety::DailyRecord& r) {
  return r.revision == 2 && std::isfinite(r.grams) && r.grams >= 0 &&
         !(r.day == 0 && (r.portions != 0 || r.grams != 0 || r.last_feed_epoch != 0));
}
inline bool encode(const safety::DailyRecord& r, uint8_t (&out)[SIZE]) {
  if (!valid(r)) return false;
  static_assert(sizeof(float) == 4, "safety record expects 32-bit grams");
  out[0] = 'C'; out[1] = 'S'; out[2] = 3;
  for (size_t i = 0; i < 4; ++i) out[3+i] = static_cast<uint8_t>(r.day >> (8*i));
  out[7] = static_cast<uint8_t>(r.portions); out[8] = static_cast<uint8_t>(r.portions >> 8);
  uint32_t bits; std::memcpy(&bits, &r.grams, 4);
  for (size_t i = 0; i < 4; ++i) out[9+i] = static_cast<uint8_t>(bits >> (8*i));
  for (size_t i = 0; i < 8; ++i) out[13+i] = static_cast<uint8_t>(r.last_feed_epoch >> (8*i));
  out[21] = r.needs_inspection ? 1 : 0; out[22] = 0;
  const auto crc = uart_v1::crc16(out, SIZE-2);
  out[23] = static_cast<uint8_t>(crc); out[24] = static_cast<uint8_t>(crc >> 8);
  return true;
}
inline bool decode(const uint8_t (&bytes)[SIZE], safety::DailyRecord& r) {
  if (bytes[0] != 'C' || bytes[1] != 'S' || bytes[2] != 3 || bytes[21] > 1 || bytes[22] != 0 ||
      uart_v1::crc16(bytes, SIZE-2) != (bytes[23] | static_cast<uint16_t>(bytes[24]) << 8)) return false;
  safety::DailyRecord next{};
  next.day = 0; uint32_t bits = 0;
  for (size_t i = 0; i < 4; ++i) {
    next.day |= static_cast<uint32_t>(bytes[3+i]) << (8*i);
    bits |= static_cast<uint32_t>(bytes[9+i]) << (8*i);
  }
  std::memcpy(&next.grams, &bits, 4);
  // OR of two octets is bounded to uint16; integer promotion is intentional.
  next.portions = static_cast<uint16_t>(bytes[7] | static_cast<uint16_t>(bytes[8]) << 8);
  for (size_t i = 0; i < 8; ++i) next.last_feed_epoch |= static_cast<uint64_t>(bytes[13+i]) << (8*i);
  next.needs_inspection = bytes[21] == 1;
  if (!valid(next)) return false;
  r = next;
  return true;
}
}  // namespace safety_record
