#pragma once
#include <cstring>
#include "calibration.h"
#include "uart_v1.h"

namespace m4 {
struct CalibrationRecord {
  ScaleCalibration hx711{};
  LevelCalibration food{}, water{};
};
namespace calibration_record {
constexpr size_t SIZE = 39;
inline bool valid(const CalibrationRecord& record) {
  if (record.hx711.tared && !rawValid(record.hx711.tare_counts)) return false;
  if (!record.hx711.tared && (record.hx711.tare_counts != 0 || record.hx711.calibrated)) return false;
  if (record.hx711.calibrated && !record.hx711.valid()) return false;
  if (!record.hx711.calibrated && record.hx711.grams_per_count != 0) return false;
  const LevelCalibration* geometries[] = {&record.food, &record.water};
  for (const auto* geometry : geometries) {
    if (geometry->calibrated && !geometry->valid()) return false;
    if (!geometry->calibrated && (geometry->full_cm != 0 || geometry->empty_cm != 0)) return false;
  }
  return true;
}
inline void put(uint8_t* output, uint64_t bits, size_t count) {
  for (size_t i = 0; i < count; ++i) output[i] = static_cast<uint8_t>(bits >> (8*i));
}
inline uint64_t get(const uint8_t* input, size_t count) {
  uint64_t result = 0;
  for (size_t i = 0; i < count; ++i) result |= static_cast<uint64_t>(input[i]) << (8*i);
  return result;
}
inline bool encode(const CalibrationRecord& record, uint8_t (&bytes)[SIZE]) {
  static_assert(sizeof(double)==8 && sizeof(float)==4, "explicit sensor calibration numeric layout");
  if (!valid(record)) return false;
  bytes[0]='M'; bytes[1]='4'; bytes[2]='C'; bytes[3]=1;
  bytes[4] = (record.hx711.tared ? 1 : 0) | (record.hx711.calibrated ? 2 : 0) |
             (record.food.calibrated ? 4 : 0) | (record.water.calibrated ? 8 : 0);
  uint64_t bits;
  std::memcpy(&bits, &record.hx711.tare_counts, 8); put(bytes+5, bits, 8);
  std::memcpy(&bits, &record.hx711.grams_per_count, 8); put(bytes+13, bits, 8);
  const float values[] = {record.food.full_cm, record.food.empty_cm, record.water.full_cm, record.water.empty_cm};
  for (size_t i=0; i<4; ++i) { uint32_t word; std::memcpy(&word, values+i, 4); put(bytes+21+i*4, word, 4); }
  put(bytes+SIZE-2, uart_v1::crc16(bytes, SIZE-2), 2); return true;
}
inline bool decode(const uint8_t (&bytes)[SIZE], CalibrationRecord& record) {
  if (bytes[0]!='M' || bytes[1]!='4' || bytes[2]!='C' || bytes[3]!=1 || (bytes[4]&0xf0) ||
      get(bytes+SIZE-2,2) != uart_v1::crc16(bytes,SIZE-2)) return false;
  CalibrationRecord next;
  next.hx711.tared=bytes[4]&1; next.hx711.calibrated=bytes[4]&2;
  next.food.calibrated=bytes[4]&4; next.water.calibrated=bytes[4]&8;
  uint64_t bits=get(bytes+5,8); std::memcpy(&next.hx711.tare_counts,&bits,8);
  bits=get(bytes+13,8); std::memcpy(&next.hx711.grams_per_count,&bits,8);
  float* values[]={&next.food.full_cm,&next.food.empty_cm,&next.water.full_cm,&next.water.empty_cm};
  for (size_t i=0;i<4;++i) { uint32_t word=static_cast<uint32_t>(get(bytes+21+i*4,4)); std::memcpy(values[i],&word,4); }
  if (!valid(next)) return false;
  record=next; return true; // invalid data never becomes a guessed factor/geometry
}
}  // namespace calibration_record
}  // namespace m4
