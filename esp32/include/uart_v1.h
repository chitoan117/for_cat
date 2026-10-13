#pragma once

// Same frozen v1 fields/CRC as Python codec, no Arduino dependency or heap.
#include <cstddef>
#include <cstdint>

namespace uart_v1 {
constexpr uint8_t START_A = 0xA5, START_B = 0x5A, VERSION = 1;
constexpr size_t HEADER = 10, MAX_PAYLOAD = 256, MAX_FRAME = HEADER + MAX_PAYLOAD + 2;
enum Command : uint8_t {
  PING = 1, GET_STATUS = 2, FEED_REQUEST = 3, FEED_STATUS = 4,
  SYSTEM_STATUS = 5, ACK = 6, NACK = 7
};

inline uint16_t crc16(const uint8_t* data, size_t length) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < length; ++i) {
    crc ^= static_cast<uint16_t>(data[i]) << 8;
    for (uint8_t bit = 0; bit < 8; ++bit)
      crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021)
                           : static_cast<uint16_t>(crc << 1);
  }
  return crc;
}

inline bool encode(uint32_t id, uint8_t command, const uint8_t* payload,
                   uint16_t length, uint8_t* output, size_t capacity, size_t& written) {
  written = 0;
  if (!output || length > MAX_PAYLOAD || capacity < HEADER + length + 2 ||
      (length && !payload)) return false;
  output[0] = START_A; output[1] = START_B; output[2] = VERSION;
  for (uint8_t i = 0; i < 4; ++i) output[3 + i] = static_cast<uint8_t>(id >> (i * 8));
  output[7] = command;
  output[8] = static_cast<uint8_t>(length);
  output[9] = static_cast<uint8_t>(length >> 8);
  for (uint16_t i = 0; i < length; ++i) output[HEADER + i] = payload[i];
  const uint16_t crc = crc16(output + 2, HEADER - 2 + length);
  output[HEADER + length] = static_cast<uint8_t>(crc);
  output[HEADER + length + 1] = static_cast<uint8_t>(crc >> 8);
  written = HEADER + length + 2;
  return true;
}
}  // namespace uart_v1
