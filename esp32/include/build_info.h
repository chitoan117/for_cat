#pragma once
#include "board_config.h"

// Human monitor/boot metadata only. GET_STATUS/UART v1 payloads are NOT expanded.
namespace build_info {
constexpr const char* firmware_version = "0.1.0-m3-pack1";
#if defined(FORR_BOARD_S3)
constexpr const char* board = "GENERIC_ESP32_S3_N16R8_COMPILE_SURROGATE";
#if defined(SIMULATED_SENSORS)
constexpr const char* profile = "esp32s3_n16r8_sim";
#elif defined(FORR_NATIVE_USB) && FORR_NATIVE_USB
constexpr const char* profile = "esp32s3_n16r8_hw_safe";
#else
constexpr const char* profile = "esp32s3_n16r8_hw_safe_uart";
#endif
#else
constexpr const char* board = "CLASSIC_ESP32DEV";
#if defined(SIMULATED_SENSORS)
constexpr const char* profile = "esp32dev_sim";
#else
constexpr const char* profile = "esp32dev_hw_safe";
#endif
#endif
#if defined(SIMULATED_SENSORS)
constexpr bool simulation = true;
#else
constexpr bool simulation = false;
#endif
constexpr bool actuator_enabled = board_profile::physical_outputs;
static_assert(!actuator_enabled, "M3 first flash cannot enable physical outputs");
#if defined(FORR_BUILD_BANNER) && FORR_BUILD_BANNER && !defined(FORR_HW_SAFE)
#error "First-flash monitor banner is only permitted in an HW_SAFE build"
#endif
}  // namespace build_info
