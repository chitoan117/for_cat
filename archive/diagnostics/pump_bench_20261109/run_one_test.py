from pathlib import Path
import os,time,json
r=Path('/home/toan/for_cat/evidence/pump_bench_20261109')
def send(body):
    t=Path('/tmp/fc_pump_test_'+str(os.getpid())+'.txt')
    with t.open('x') as f:f.write(body)
    try:os.link(str(t),'/tmp/for_cat_cmd.txt')
    finally:t.unlink()
def read_after(offset):
    with open('/var/log/syslog','rb') as f:
        f.seek(offset);return f.read().decode('utf-8','replace')
with open('/var/log/syslog','rb') as f:f.seek(0,2);offset=f.tell()
send('0\nmode\n');time.sleep(3)
pre=read_after(offset)
assert 'exited=1' in pre and 'servo_moving=0' in pre,'Not paused/idle: '+pre[-1500:]
try:
    send('pump_test\n')  # exactly one test; never replay on disconnect
    time.sleep(5)
finally:
    send('pump_off\n')  # additional OFF only, never another ON
    time.sleep(2)
log=read_after(offset)
lines=[s for s in log.splitlines() if '[esp32]' in s]
result={'pump_test_commands_sent':1,'requested_duration_ms':1000,
        'start_ack':any('PUMP TEST START:' in s for s in lines),
        'automatic_stop_ack':any('PUMP TEST DONE:' in s for s in lines),
        'final_off_ack':any('PUMP OFF GPIO7 LOW.' in s for s in lines),
        'physical_water_flow':'AWAITING_OWNER_OBSERVATION','log':lines}
(r/'one_test_result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
assert result['start_ack'] and result['automatic_stop_ack'] and result['final_off_ack']
