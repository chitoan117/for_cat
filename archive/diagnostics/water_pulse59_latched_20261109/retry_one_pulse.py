from pathlib import Path
import json, os, re, time

root = Path('/home/toan/for_cat/evidence/water_pulse59_latched_20261109')
out = root / ('retry_one_pulse_' + str(int(time.time())) + '.json')

def send(body):
    p = Path('/tmp/fc_water_retry_' + str(os.getpid()) + '.txt')
    with p.open('x') as f:
        f.write(body + '\n')
    try:
        os.link(str(p), '/tmp/for_cat_cmd.txt')
    finally:
        p.unlink()

with open('/var/log/syslog', 'rb') as f:
    f.seek(0, 2)
    offset = f.tell()

def log():
    with open('/var/log/syslog', 'rb') as f:
        f.seek(offset)
        return f.read().decode('utf-8', 'replace')

result = {'requested_max_ms': 1000, 'on_commands_sent': 0,
          'physical_flow_after_off': 'AWAITING_OWNER_OBSERVATION'}
try:
    send('pump_auto off\npump_off\nmode\npump_status')
    time.sleep(2)
    pre = log()
    assert 'servo_moving=0' in pre, 'Servo idle not confirmed'
    rows = re.findall(r'PUMP auto=(\d) running=(\d) test=(\d) fault=(\d) driver_verified=(\d) reason=(\S+) D1=([-\d.]+) pulses=(\d+)', pre)
    assert rows and rows[-1][:3] == ('0', '0', '0'), 'Pump OFF not confirmed'
    result['pre_status'] = rows[-1]
    cm = float(rows[-1][6])
    if not 5.9 < cm <= 6.4:
        result['outcome'] = 'NOT_RUN_D1_OUTSIDE_SAFE_TEST_RANGE'
    else:
        # Exactly one native-timed pulse, never replay ON after uncertain ACK.
        send('pump_test 1000')
        result['on_commands_sent'] = 1
        time.sleep(3)
        result['start_ack'] = 'PUMP TEST START: GPIO7 HIGH/ON max1000ms' in log()
        result['native_stop_ack'] = 'PUMP TEST DONE: GPIO7 LOW/OFF after1000ms' in log()
        result['outcome'] = 'TIMED_PULSE_CONFIRMED' if result['start_ack'] and result['native_stop_ack'] else 'CHECK_ACK_NO_ON_RETRY'
finally:
    send('pump_off\npump_off\npump_status')
    time.sleep(2)
    result['log'] = [s for s in log().splitlines() if '[esp32]' in s]
    result['final_off_ack'] = 'PUMP OFF GPIO7 LOW.' in log()
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
