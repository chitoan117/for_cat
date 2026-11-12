#pragma once
// Identifies this diagnostic family, not proof of which bytes were flashed.
// Actual image SHA256 must be compared with the build/flash evidence separately.
constexpr const char* physical_kit_id="FORCAT_PHYSICAL_KIT_20261029_V1";
template<class Serial>inline void physicalKitBanner(Serial& serial,const char* profile){
  serial.printf("KIT_FIRMWARE_ID=%s PROFILE=%s FLASH16MB NO_VERIFIED_PSRAM UART0_115200 PHYSICAL_PASS=NOT_VERIFIED\r\n",physical_kit_id,profile);
}
