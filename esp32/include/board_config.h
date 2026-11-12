#pragma once

#ifndef ACTUATOR_OUTPUTS_ENABLED
#define ACTUATOR_OUTPUTS_ENABLED 0
#endif

#if defined(FORR_BOARD_CLASSIC) && defined(FORR_BOARD_S3)
#error "Only one MCU compile profile can be selected"
#endif
#if defined(FORR_NATIVE_USB) && FORR_NATIVE_USB && !defined(FORR_BOARD_S3)
#error "Native USB profile requires ESP32-S3 compile surrogate"
#endif
#if defined(FORR_NATIVE_USB) && FORR_NATIVE_USB && \
    (!defined(ARDUINO_USB_CDC_ON_BOOT) || ARDUINO_USB_CDC_ON_BOOT != 1)
#error "Native serial profile requires explicit CDC-on-boot configuration"
#endif
#if defined(ARDUINO) && defined(FORR_BOARD_S3) && !defined(CONFIG_IDF_TARGET_ESP32S3)
#error "S3 board profile selected for a non-S3 toolchain"
#endif

#if defined(FORR_REAL_S3_NO_PSRAM)
#if !defined(FORR_BOARD_S3) || !defined(FORR_HW_SAFE) || defined(SIMULATED_SENSORS)
#error "Measured S3 profile must be S3 HW_SAFE, never simulation"
#endif
// CONFIG_SPIRAM_* in the shared precompiled SDK describes capability, not board enable.
#if defined(BOARD_HAS_PSRAM) || (defined(FORR_ENABLE_PSRAM) && FORR_ENABLE_PSRAM)
#error "Current measured board profile must not enable unverified PSRAM"
#endif
#if !defined(FORR_NATIVE_USB) || FORR_NATIVE_USB != 0 || !defined(ARDUINO_USB_CDC_ON_BOOT) || ARDUINO_USB_CDC_ON_BOOT != 0
#error "Measured bridge profile requires UART0, not native USB CDC"
#endif
#endif

namespace board_profile {
enum class Board { CLASSIC_ESP32DEV, GENERIC_ESP32_S3_N16R8, ESP32_S3_FLASH16MB_NO_VERIFIED_PSRAM };
#if defined(FORR_REAL_S3_NO_PSRAM)
constexpr Board selected = Board::ESP32_S3_FLASH16MB_NO_VERIFIED_PSRAM;
#elif defined(FORR_BOARD_S3)
constexpr Board selected = Board::GENERIC_ESP32_S3_N16R8;
#else
constexpr Board selected = Board::CLASSIC_ESP32DEV;
#endif
constexpr bool gpio_verified = false;
constexpr bool physical_outputs = ACTUATOR_OUTPUTS_ENABLED != 0;
static_assert(!physical_outputs && !gpio_verified, "RC2 permits no physical output/pin profile");
}  // namespace board_profile

// No verified board mapping, wiring, actuator interlock or load testing exists.
// Deliberate future hardware work must revise this guard before any output.
#if ACTUATOR_OUTPUTS_ENABLED != 0
#error "Actuator output is prohibited until board pins and safety are hardware verified"
#endif

#if defined(SIMULATED_SENSORS) && defined(GENERIC_ESP32DEV)
#error "Select one safe board profile"
#endif
#if defined(SIMULATED_SENSORS) && defined(FORR_HW_SAFE)
#error "HW_SAFE cannot also select synthetic sensor execution"
#endif
