#pragma once
#include <cstring>
#include "calibration_record.h"
namespace m4 { namespace inox_mount {
constexpr size_t ID_SIZE=40,SIZE=60;
inline bool validId(const char* id){
 const size_t n=std::strlen(id);if(!n||n>ID_SIZE)return false;
 for(size_t i=0;i<n;++i){const char c=id[i];if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_'||c=='-'))return false;}
 return true;
}
inline bool encode(const char* id,const ScaleCalibration& c,uint8_t(&bytes)[SIZE]){
 if(!validId(id)||!c.valid())return false;
 std::memset(bytes,0,SIZE);bytes[0]=1;bytes[1]=static_cast<uint8_t>(std::strlen(id));std::memcpy(bytes+2,id,bytes[1]);
 uint64_t bits;std::memcpy(&bits,&c.tare_counts,8);calibration_record::put(bytes+42,bits,8);
 std::memcpy(&bits,&c.grams_per_count,8);calibration_record::put(bytes+50,bits,8);
 calibration_record::put(bytes+58,uart_v1::crc16(bytes,58),2);return true;
}
inline bool matches(const uint8_t(&bytes)[SIZE],const char* id,const ScaleCalibration& c){
 uint8_t expected[SIZE];return encode(id,c,expected)&&std::memcmp(bytes,expected,SIZE)==0;
}
} }
