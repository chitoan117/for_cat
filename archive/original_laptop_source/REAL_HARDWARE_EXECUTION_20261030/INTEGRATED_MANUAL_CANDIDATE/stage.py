"""Snapshot existing qualified firmware into NEW candidate; no builds/devices."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1] / 'HARDWARE_PHYSICAL_BRINGUP_20261029/firmware'
FW = ROOT / 'firmware'
if FW.exists():
    raise ValueError('preserve staged source; do not overwrite')
FW.mkdir()
inputs = {}
for folder in ('include', 'src', 'test'):
    for p in sorted((BASE / folder).rglob('*')):
        if p.is_file():
            rel = p.relative_to(BASE)
            target = FW / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
            inputs[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copyfile(BASE / 'kit_metadata.py', FW / 'kit_metadata.py')


def edit(rel, replacements):
    p = FW / rel
    text = p.read_text(encoding='utf-8')
    for old, new, count in replacements:
        assert text.count(old) == count, (rel, old, text.count(old))
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8', newline='\n')


edit('include/serial_port.h', [
    ('#if defined(M4_DOG_WARNING) && M4_DOG_WARNING',
     '#if (defined(M4_DOG_WARNING) && M4_DOG_WARNING) || defined(FORCAT_MANUAL_STATION)', 2),
    ('  bool overflowed()const{return overflow_;}',
     '  bool overflowed()const{return overflow_;}\n  bool empty()const{return count_==0;}', 1),
])
edit('include/m4/arduino_io.h', [
    ('  bool save(const CalibrationRecord& record) {',
     '  bool save(const CalibrationRecord& record) {\n#if defined(FORCAT_MANUAL_STATION)\n    (void)record; return false; // Candidate never writes calibration/NVS\n#else', 1),
    ('    prefs.end(); return ok;\n  }', '    prefs.end(); return ok;\n#endif\n  }', 1),
])
edit('include/physical_kit_identity.h', [
    ('FORCAT_PHYSICAL_KIT_20261029_V1', 'FORCAT_MANUAL_STATION_20261030_V1', 1),
])
edit('src/diagnostics.cpp', [
    ('void report() {', 'void report() {\n  if(!protocolSerial().empty())return;', 1),
    ('void serialCommands() {', '__attribute__((unused)) void serialCommands() {', 1),
    ('m4::diagnosticName(),static_cast<unsigned long>(snapshot.sampled_at_ms)',
     '"diag_manual_station",static_cast<unsigned long>(snapshot.sampled_at_ms)', 1),
    ('diag_four_ultrasonic', 'diag_manual_station', 2),
    ('  auto& serial=protocolSerial();\n  serial.printf',
     '  auto& serial=protocolSerial();\n  serial.printf', 1),
    ('  serial.printf("\\"kit_firmware_id', '  manualTelemetry();\n  serial.printf("\\"kit_firmware_id', 1),
    ('  serial.print("\\"servo_armed\\":false,\\"servo_state\\":\\"PWM_NOT_ATTACHED_CLOSE_PHYSICAL_UNVERIFIED\\",");',
     '  serial.printf("\\"servo_armed\\":%s,\\"servo_state\\":\\"%s\\",",manualServoActive()?"true":"false",manualServoState());', 1),
    ('  serial.print("\\"pump_armed\\":false,\\"pump_state\\":\\"OUTPUT_NOT_ENABLED_PHYSICAL_OFF_UNVERIFIED\\",");',
     '  serial.printf("\\"pump_armed\\":%s,\\"pump_state\\":\\"%s\\",",manualPumpActive()?"true":"false",manualPumpState());', 1),
    ('\\"physical_pump_on\\":false,\\"actuator_outputs_enabled\\":0',
     '\\"physical_pump_on\\":null,\\"automatic_actuator_outputs_enabled\\":0', 1),
    ('void setup() {', 'void sensorSetup() {', 1),
    ('void loop() {', 'void sensorLoop() {', 1),
    ('  serialCommands();', '  // Integrated owner-only parser runs in manual_station.cpp.', 1),
    ('SERVO6/PUMP7 UNTOUCHED.', 'MANUAL STATION: SERVO6 PWM_OFF; PUMP7 POLARITY_GATED.', 2),
])
(FW / 'platformio.ini').write_text('''[platformio]
default_envs = manual_station_safe

[env]
platform = espressif32@55.3.311
board = esp32-s3-devkitc-1
framework = arduino
monitor_speed = 115200
board_upload.flash_size = 16MB
board_upload.maximum_size = 16777216
board_build.partitions = default_16MB.csv
extra_scripts = post:kit_metadata.py
build_src_filter = -<*> +<manual_station.cpp>
build_flags =
    -DACTUATOR_OUTPUTS_ENABLED=0
    -DFORR_BOARD_S3=1
    -DFORR_REAL_S3_NO_PSRAM=1
    -DFORR_NATIVE_USB=0
    -DARDUINO_USB_CDC_ON_BOOT=0
    -DFORR_HW_SAFE=1
    -DSERVO_DIAGNOSTIC_ENABLED=0
    -DPUMP_DIAGNOSTIC_ENABLED=0
    -DPHYSICAL_VALIDATION_KIT=1
    -DM4_SENSOR_BRINGUP=1
    -DM4_DIAGNOSTIC_MODE=7
    -DM4_HX711_INSTALLED=1
    -DM4_CURRENT_HARDWARE_PROFILE=1
    -DM4_QUAD_ULTRASONIC=1
    -DFORCAT_MANUAL_STATION=1

[env:manual_station_safe]
''', encoding='utf-8')
with (ROOT / 'BASELINE_SNAPSHOT.json').open('x', encoding='utf-8') as f:
    json.dump({'source': str(BASE), 'files': inputs, 'locked_source_modified': False}, f, indent=2)
    f.write('\n')
print(json.dumps({'staged': str(FW), 'baseline_files': len(inputs), 'devices_opened': False}))
