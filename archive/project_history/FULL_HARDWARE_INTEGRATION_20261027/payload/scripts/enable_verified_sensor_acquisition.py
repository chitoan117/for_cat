"""One-time diagnostic helper; sole port owner, fixed sensor-only commands.

Requires already owner-confirmed dividers. Never accepts arbitrary TX or feed/
servo/pump commands. The production C++ bridge remains strictly RX-only.
"""
import datetime
import json
from pathlib import Path
import subprocess
import termios
import time

import serial
from serial.tools import list_ports

ROOT = Path('/home/toan/for_cat')
OUT = ROOT / 'evidence/overnight_integration_20261023' / ('sensor_enable_' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
OUT.mkdir(exist_ok=False)
candidates = [p for p in list_ports.comports() if p.vid == 0x1a86 and p.pid == 0x55d3 and p.serial_number == '5C85066678']
assert len(candidates) == 1, 'no unique previously identified ESP32'
device = candidates[0].device
commands = []
reports = []
buffer = bytearray()


def safe(data):
    assert data['mode'] == 'diag_current_hardware'
    assert data['distance_roles'] == {'channel_1': 'APPROACH', 'channel_2': 'WATER_OPERATIONAL'}
    assert type(data['actuator_outputs_enabled']) is int and data['actuator_outputs_enabled'] == 0
    assert data['physical_pump_on'] is False
    current = data['current_hardware']
    assert current['button_gpio'] == 21
    for name in ('servo_armed', 'pump_armed', 'auto_feed', 'auto_water'):
        assert current[name] is False
    assert current['servo_state'] == 'PWM_NOT_ATTACHED_CLOSE_PHYSICAL_UNVERIFIED'
    assert current['pump_state'] == 'OUTPUT_NOT_ENABLED_PHYSICAL_OFF_UNVERIFIED'


subprocess.check_call(['systemctl', '--user', 'stop', 'for-cat-esp32-bridge.service'])
try:
    with (OUT / 'raw_serial.bin').open('xb') as raw:
        port = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=1, exclusive=True)
        port.dtr = False
        port.rts = False
        port.port = device
        with port:
            settings = termios.tcgetattr(port.fileno())
            settings[2] &= ~termios.HUPCL
            termios.tcsetattr(port.fileno(), termios.TCSANOW, settings)

            def receive(seconds):
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    chunk = port.read(min(4096, max(1, port.in_waiting)))
                    if not chunk:
                        continue
                    raw.write(chunk)
                    if raw.tell() > 128 * 1024:
                        raise RuntimeError('bounded raw budget exceeded')
                    for byte in chunk:
                        if byte in (10, 13):
                            line = bytes(buffer)
                            buffer.clear()
                            if line.startswith(b'{'):
                                try:
                                    data = json.loads(line)
                                except (ValueError, UnicodeError):
                                    continue
                                safe(data)
                                reports.append(data)
                        elif len(buffer) < 4096:
                            buffer.append(byte)

            receive(4)
            assert len(reports) >= 2, 'safe initial continuous telemetry not established'
            for ack, command in (('approach_echo_ack', b'echo-approach-3v3 CONFIRM\n'),
                                 ('water_echo_ack', b'echo-water-3v3 CONFIRM\n')):
                if reports[-1][ack] is not True:
                    safe(reports[-1])
                    assert command in (b'echo-approach-3v3 CONFIRM\n', b'echo-water-3v3 CONFIRM\n')
                    port.write(command)
                    port.flush()
                    commands.append(command.decode().strip())
                    receive(3)
                    assert reports[-1][ack] is True, 'sensor ACK not observed'
            receive(4)
finally:
    subprocess.check_call(['systemctl', '--user', 'start', 'for-cat-esp32-bridge.service'])
receipt = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'device': device,
           'commands': commands, 'report_count': len(reports), 'latest_report': reports[-1] if reports else None,
           'divider_confirmation_source': 'PRIOR_USER_PHYSICAL_CONFIRMATION_NOT_FIRMWARE_VOLTAGE_MEASUREMENT',
           'actuator_commands_sent': False, 'firmware_flash': False}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2))
