"""Edit NEW fork only: manual remains one entry point, feed-link remains INERT."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;FW=ROOT/'firmware'


def edit(name,items):
    p=FW/name;text=p.read_text(encoding='utf-8')
    for old,new,count in items:
        if new!=old and text.count(new)==count:
            continue # resume only an exactly generated replacement, never an arbitrary edit
        assert text.count(old)==count,(name,old,text.count(old))
        text=text.replace(old,new)
    p.write_text(text,encoding='utf-8',newline='\n')


edit('include/physical_kit_identity.h',[('FORCAT_MANUAL_STATION_20261030_V1','FORCAT_DUAL_STATION_20261030_V1',1)])
edit('src/diagnostics.cpp',[
    ('diag_manual_station','diag_dual_station',3),
    ('  manualTelemetry();','  manualTelemetry();\n  hybridTelemetry();',1),
])
edit('src/manual_station.cpp',[
    ('m4::LedcServoOutput servo_output;','auto& servo_output=dual_servo_bus.manual();',1),
    ('const int byte=protocolSerial().read();','const int byte=protocolSerial().read();\n    if(hybridFeedByte(static_cast<uint8_t>(byte),millis())){manual_used=0;manual_discard=false;continue;}',1),
    ('station.emergency();stopSensors();reply("STOP_LATCHED', 'hybridAbort();station.emergency();stopSensors();reply("STOP_LATCHED',1),
    ('void setup(){','void manualSetup(){',1),('void loop(){','void manualLoop(){',1),
])
text=(ROOT.parent/'INTEGRATED_MANUAL_CANDIDATE/manual_console.py').read_text()
text=text.replace("p.add_argument('--execute', choices=('OWNER_APPROVED_STATION_CONSOLE',))",
    "p.add_argument('--execute', choices=('OWNER_APPROVED_STATION_CONSOLE',))\n    p.add_argument('--profile', choices=('diag_dual_station',), default='diag_dual_station')")
text=text.replace("frame.get('mode') != 'diag_manual_station' or frame.get('kit_firmware_id') != 'FORCAT_MANUAL_STATION_20261030_V1'",
    "frame.get('mode') != a.profile or frame.get('kit_firmware_id') != 'FORCAT_DUAL_STATION_20261030_V1'")
(ROOT/'manual_console_dual.py').write_text(text)
(FW/'platformio.ini').write_text('''[platformio]
default_envs = dual_station_safe
[env:dual_station_safe]
platform = espressif32@55.3.311
board = esp32-s3-devkitc-1
framework = arduino
monitor_speed = 115200
board_upload.flash_size = 16MB
board_upload.maximum_size = 16777216
board_build.partitions = default_16MB.csv
extra_scripts = post:kit_metadata.py
build_src_filter = -<*> +<dual_station.cpp>
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
    -DFORCAT_DUAL_STATION=1
''')
print('Prepared NEW dual source only; neither locked image changed.')
