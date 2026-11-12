"""Python3.6+ OWNER human-TTY console for this station only. Default PLAN.
Never stops/starts services, flashes, resets, schedules feed or opens camera.
Execute requires inactive Bridge, free stable port, reviewed image and explicit
per-output physical approval. Session/keepalive are non-actuating bookkeeping.
"""
from __future__ import print_function
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

PORT = '/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00'


def validate_command(text, approval, state):
    if text in ('status', 'servo status', 'pump status', 'stop'):
        return True
    if text.startswith('servo '):
        if not approval.get('allow_servo') or not approval.get('servo_power_mechanics_reviewed') or not approval.get('pump_load_isolated'):
            return False
        positions = approval.get('servo_positions_us')
        if not isinstance(positions, list) or len(positions) != 4 or any(type(x) is not int for x in positions):
            return False
        lo, hi, close, opened = positions
        if not (1000 <= lo < hi <= 2000 and hi - lo <= 100 and lo <= close <= hi and lo <= opened <= hi and close != opened):
            return False
        if text.startswith('servo configure '):
            return text == 'servo configure ' + ' '.join(str(x) for x in positions) + ' CONFIRM'
        if text.startswith('servo set '):
            return bool(re.match(r'^servo set [0-9]+$', text)) and lo <= int(text.split()[-1]) <= hi
        return text in ('servo arm YES', 'servo open', 'servo close', 'servo disarm')
    if text.startswith('pump '):
        if not approval.get('allow_pump') or not approval.get('pump_power_driver_priming_reviewed') or not approval.get('servo_load_isolated'):
            return False
        level = approval.get('pump_off_level')
        if type(level) is not int or level not in (0, 1) or state.get('pump_off_level') != level or state.get('pump_supported') is not True:
            return False
        if text.startswith('pump on '):
            maximum = approval.get('maximum_pump_ms')
            return type(maximum) is int and bool(re.match(r'^pump on [0-9]+$', text)) and 20 <= int(text.split()[-1]) <= min(500, maximum)
        return text in ('pump arm YES', 'pump off', 'pump disarm')
    if text in ('buzzer-driver ACTIVE_LOW CONFIRM', 'buzzer test CONFIRM'):
        return bool(approval.get('allow_buzzer') and approval.get('buzzer_3v3_active_low_reviewed') and
                    approval.get('servo_load_isolated') and approval.get('pump_load_isolated'))
    if text.startswith('hx import ') and approval.get('allow_exact_HX_RAM_import') is True:
        match = re.match(r'^hx import (\S+) (\S+) CONFIRM$', text)
        coefficients = approval.get('exact_HX_coefficients', {})
        if not match:
            return False
        try:
            offset, factor = map(float, match.groups())
            return math.isfinite(offset) and math.isfinite(factor) and factor != 0 and \
                offset == coefficients.get('offset') and factor == coefficients.get('counts_per_gram')
        except ValueError:
            return False
    return False


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', choices=('OWNER_APPROVED_STATION_CONSOLE',))
    p.add_argument('--approval', type=Path)
    p.add_argument('--image', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--seconds', type=int, default=180)
    a = p.parse_args()
    if not a.execute:
        print(json.dumps({'mode': 'PLAN_ONLY', 'port': PORT, 'opens_serial': False,
                          'service_changes': False, 'requires': 'new specific activation approval, inactive Bridge, image SHA and human TTY'}))
        return 0
    if sys.platform != 'linux' or not sys.stdin.isatty() or not 5 <= a.seconds <= 300 or not a.approval or not a.image or not a.out:
        p.error('Linux human TTY, approval, image, NEW output and bounded5..300s required')
    approval = json.loads(a.approval.read_text())
    expiry = datetime.strptime(approval['valid_until_utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    if approval.get('scope') != 'OWNER_SUPERVISED_MANUAL_STATION' or approval.get('approved') is not True or not approval.get('approved_by'):
        p.error('specific owner activation approval required')
    if not 0 < (expiry-datetime.now(timezone.utc)).total_seconds() <= 86400 or approval.get('emergency_cutoff_ready') is not True or approval.get('Serial_open_RAM_loss_reviewed') is not True:
        p.error('expired/missing physical cutoff/RAM review')
    image_sha = hashlib.sha256(a.image.read_bytes()).hexdigest()
    if image_sha != approval.get('flash_verified_image_sha256'):
        p.error('image must match actual reviewed flash-verify receipt')
    state = subprocess.check_output(['systemctl', '--user', 'show', 'for-cat-esp32-bridge.service', '-p', 'ActiveState', '--value']).decode().strip()
    if state not in ('inactive', 'failed') or str(Path(PORT).resolve(strict=True)) != '/dev/ttyACM0':
        p.error('Bridge must be released in separately approved maintenance window; console never stops it')
    holder = subprocess.run(['fuser', '/dev/ttyACM0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if holder.returncode != 1 or holder.stdout.strip() or holder.stderr.strip():
        p.error('Serial owned or ownership visibility unknown')
    if a.out.exists() or a.out.is_symlink() or not a.out.parent.is_dir():
        p.error('NEW output with existing parent required')
    import serial  # imported only after explicit approval and passive ownership checks
    a.out.mkdir(mode=0o700)
    events = (a.out / 'events.jsonl').open('x')
    raw = (a.out / 'serial_raw.bin').open('xb')
    lock = threading.RLock()
    stopped = threading.Event()
    current = {'boot': 0, 'session': 0, 'seq': 0, 'ready': False, 'manual': {}}
    io = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=.3, exclusive=True)
    io.dtr = False
    io.rts = False
    io.port = PORT
    thread = None
    def log(kind, **fields):
        events.write(json.dumps(dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), kind=kind, **fields))+'\n'); events.flush()
    def tx(text):
        io.write((text+'\n').encode('ascii')); log('TX', command=text)
    def packet(text):
        if not current['ready'] or not current['session']:
            raise ValueError('validated station and USER SESSION required')
        current['seq'] += 1
        tx('@%d %d %d %s' % (current['boot'], current['session'], current['seq'], text))
    def reader():
        pending = bytearray(); total = 0; last = 0
        try:
            while not stopped.is_set():
                chunk = io.read(min(4096, max(1, io.in_waiting)))
                if chunk:
                    with lock:
                        raw.write(chunk); raw.flush(); total += len(chunk); pending.extend(chunk)
                        if total > 4*1024*1024 or len(pending)>16384:
                            raise ValueError('RX budget exceeded')
                        while b'\n' in pending:
                            line, _, rest = pending.partition(b'\n'); pending = bytearray(rest)
                            text = line.decode('utf-8', 'replace').rstrip('\r'); log('RX', line=text)
                            if text.startswith('{'):
                                frame = json.loads(text)
                                if frame.get('mode') != 'diag_manual_station' or frame.get('kit_firmware_id') != 'FORCAT_MANUAL_STATION_20261030_V1':
                                    raise ValueError('wrong running firmware; no command allowed')
                                manual = frame['manual_station']
                                if manual['boot_nonce'] != current['boot']:
                                    current.update(boot=manual['boot_nonce'], session=0, seq=0)
                                current.update(ready=True, manual=manual)
                            match = re.match(r'^MANUAL_RESULT boot=(\d+) session=(\d+) seq=(\d+) result=(.*)$', text)
                            if match:
                                boot, session, seq = map(int, match.groups()[:3])
                                if boot == current['boot']:
                                    if session != current['session']:
                                        current.update(session=session, seq=seq)
                                    else:
                                        current['seq'] = max(current['seq'], seq)
                                print(text)
                if time.monotonic()-last >= 1:
                    with lock:
                        if current['session'] and current['ready']:
                            packet('keepalive')
                        else:
                            tx('status')
                    last = time.monotonic()
        except Exception as e:
            with lock:
                log('READER_ERROR', error=str(e)); current['ready']=False
            stopped.set()
    try:
        io.open()
        log('OPEN', image_sha256=image_sha, approval_sha256=hashlib.sha256(a.approval.read_bytes()).hexdigest())
        thread = threading.Thread(target=reader); thread.daemon=True; thread.start()
        timer = threading.Timer(min(a.seconds, (expiry-datetime.now(timezone.utc)).total_seconds()), stopped.set); timer.daemon=True; timer.start()
        print('No automatic motion. Wait for valid status; type SESSION, then explicitly SEND approved command. STOP / QUIT.')
        # A select loop enforces timeout even while the user is not typing.
        import select
        while not stopped.is_set():
            ready, _, _ = select.select([sys.stdin], [], [], .2)
            if not ready:
                continue
            incoming = sys.stdin.readline()
            if not incoming:
                break
            text = incoming.strip()
            with lock:
                if text == 'QUIT':
                    break
                if text == 'STOP':
                    tx('stop'); current['session']=0
                elif text == 'SESSION' and current['ready']:
                    tx('session begin')
                elif text.startswith('SEND ') and validate_command(text[5:], approval, current['manual']):
                    if text[5:] in ('status', 'servo status', 'pump status', 'stop'):
                        tx(text[5:])
                    else:
                        packet(text[5:])
                else:
                    print('REJECTED: no matching specific approval/valid firmware/session/command')
    finally:
        stopped.set()
        if thread is not None:
            thread.join(timeout=1)
        with lock:
            if io.is_open:
                try:
                    tx('stop')  # latched OFF; never sends ARM/ON or resets the board
                finally:
                    io.close()
            log('CLOSED_NO_SERVICE_RESTART', physical_pass=False)
            raw.close(); events.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
