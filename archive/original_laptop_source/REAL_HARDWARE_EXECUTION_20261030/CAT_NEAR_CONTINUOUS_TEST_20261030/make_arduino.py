"""Amalgamate the built source into ONE self-contained Arduino IDE sketch."""
from pathlib import Path
import re
R=Path(__file__).resolve().parent;H=R/'firmware/include'
def clean(text):
    text=re.sub(r'//[^\n]*','',text)
    text=re.sub(r'^\s*#(?:pragma once|include "[^"\n]+")\s*$', '',text,flags=re.M)
    return '\n'.join(s.rstrip() for s in text.splitlines() if s.strip())+'\n'
def header(name):return clean((H/name).read_text())
parts=['''// FOR_CAT: single-file Arduino IDE version of CAT_NEAR_CONTINUOUS_TEST.
// Board: ESP32S3 Dev Module, ESP32 Arduino core 3.3.11, USB CDC On Boot Disabled.
// Serial is UART0 / external USB-UART bridge at 115200, not native USB CDC.
// No library install required beyond the ESP32 board package.
#include <Arduino.h>
#include <Preferences.h>
#include <driver/gpio.h>
#include <esp_system.h>
#include <cmath>
#include <cstring>
#include <cstdint>
#include <cstddef>
#include <cstdarg>
#include <cstdio>
#include <esp_arduino_version.h>
#if ESP_ARDUINO_VERSION_MAJOR < 3
#error "Select ESP32 Arduino board package 3.x (tested 3.3.11)"
#endif
#if !defined(CONFIG_IDF_TARGET_ESP32S3)
#error "Select ESP32S3 Dev Module"
#endif
#if ARDUINO_USB_CDC_ON_BOOT
#error "Disable USB CDC On Boot: this project uses Serial0 and the external UART bridge"
#endif
#define M4_SENSOR_BRINGUP 1
#define M4_QUAD_ULTRASONIC 1
#define FORCAT_MANUAL_STATION 1
void setup();
void loop();
namespace current_hardware {
constexpr int SERVO_SIGNAL=6,PUMP_CONTROL=7,OPTIONAL_WATER_INPUT=10;
}
namespace uart_v1 {
inline uint16_t crc16(const uint8_t* p,size_t n){uint16_t c=0xffff;for(size_t i=0;i<n;++i){c^=uint16_t(p[i])<<8;for(unsigned j=0;j<8;++j)c=c&0x8000?uint16_t((c<<1)^0x1021):uint16_t(c<<1);}return c;}
}
''']
for h in ('m4/health.h','m4/io.h','m4/calibration.h','m4/hx711_reference.h','m4/hx711.h','m4/calibration_record.h'):parts.append(header(h))
io=(H/'m4/arduino_io.h').read_text()
parts.append('namespace m4 {\n'+clean(io[io.index('class ArduinoPins'):io.index('class ArduinoI2C')]))
parts.append(clean(io[io.index('enum class CalibrationLoad'):]))
parts.append('''namespace m4 { namespace servo_bench {
constexpr int pin=6;
constexpr uint16_t electrical_min_us=1000,electrical_max_us=2000;
class Output {public:virtual ~Output()=default;virtual bool start(uint16_t)=0;virtual bool write(uint16_t)=0;virtual bool off()=0;};
}}
''')
for h in ('m4/ledc_servo.h','serial_port.h','continuous_servo.h','continuous_dispense.h','continuous_hx_adapter.h','m4/ultrasonic.h','cat_gate.h','test_wire.h','user_settings.h'):parts.append(header(h))
source=(R/'firmware/src/cat_continuous.cpp').read_text()
source=source.replace('bool quiet(){','bool quiet();\nvoid stop();\nvoid reply(uint32_t,bool,const char*);\nvoid number(float);\nvoid telemetry(const Sample&);\nvoid command(char*,const Sample&);\nbool quiet(){')
parts.append(clean(source))
out=R/'arduino/FOR_CAT_25G';out.mkdir(parents=True,exist_ok=True)
(out/'FOR_CAT_25G.ino').write_text('\n'.join(parts),encoding='utf-8')
print('Self-contained sketch:',out/'FOR_CAT_25G.ino')
print('Lines:',sum(len(p.splitlines()) for p in parts))
