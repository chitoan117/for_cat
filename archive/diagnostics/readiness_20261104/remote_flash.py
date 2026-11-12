from pathlib import Path
import struct,zlib,json,hashlib,subprocess,time,serial

r=Path('/home/toan/for_cat/evidence/readiness_20261104/firmware')
tool='/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/flash_tool/bin/esptool.py'
data=(r/'before_flash_0_150000.bin').read_bytes()
assert len(data)==0x150000
assert data[0x8000:0x8c00]==(r/'esp32.ino.partitions.bin').read_bytes()
assert hashlib.sha256((r/'esp32.ino.bin').read_bytes()).hexdigest()=='f0e91dcb650f96e9f494d011c493888211b9658e24a686898693c892ac273c79'
# Actual Arduino OTA metadata: seq1 and seq0, valid CRCs; largest selects app0.
entries=[]
for off in (0xe000,0xf000):
    b=data[off:off+32]
    seq=struct.unpack_from('<I',b)[0]
    state=struct.unpack_from('<I',b,24)[0]
    crc=struct.unpack_from('<I',b,28)[0]
    assert crc==zlib.crc32(b[:4],0xffffffff) and state==0xffffffff
    entries.append(seq)
assert entries==[1,0],f'Unexpected boot selection {entries}'
assert data[0x10000]==0xe9
base=[tool,'--chip','esp32s3','--port','/dev/ttyACM0','--baud','921600','--before','default-reset','--after','no-reset']
def run(name,args):
    with (r/(name+'.log')).open('w') as log:
        result=subprocess.run(base+args,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    if result.returncode:
        print((r/(name+'.log')).read_text()[-3500:],flush=True)
        raise SystemExit(result.returncode)
    print(name+': PASS',flush=True)
run('write_app0',['write-flash','0x10000',str(r/'esp32.ino.bin')])
run('verify_app0',['verify-flash','0x10000',str(r/'esp32.ino.bin')])
run('read_nvs_after',['read-flash','0x9000','0x5000',str(r/'nvs_after.bin')])
assert (r/'nvs_before.bin').read_bytes()==(r/'nvs_after.bin').read_bytes(),'NVS contents changed'
print('NVS_PRESERVED: PASS',flush=True)
# Reset and inspect the application without starting the AI dispatch bridge.
s=serial.Serial('/dev/ttyACM0',115200,timeout=0.15,dsrdtr=False,rtscts=False)
try:
    s.dtr=False
    s.rts=True
    time.sleep(0.1)
    s.rts=False
    end=time.monotonic()+9
    lines=[]
    zero_sent=False
    mode_sent=False
    profile_seen=False
    statuses=[]
    while time.monotonic()<end:
        line=s.readline().decode('utf-8',errors='replace').strip()
        if line:
            lines.append(line)
            if 'SERVO UNO PROFILE:' in line:
                profile_seen=True
                print(line,flush=True)
            if 'EXIT 0' in line or 'MODE:' in line or 'LIMIT SWITCH DISABLED' in line or 'HX_DIAG' in line:
                print(line,flush=True)
            try:
                msg=json.loads(line)
            except ValueError:
                msg={}
            if msg.get('type')=='status':
                statuses.append({k:msg.get(k) for k in ['ms','bench_state','bench_servo_armed','closure_mode','limit_switch_enabled','physical_closed','hx_health','calibrated']})
        if not zero_sent and profile_seen:
            s.write(b'0\n')
            zero_sent=True
        if not mode_sent and zero_sent and len(lines)>15:
            s.write(b'mode\nlimit\nhx_diag\n')
            mode_sent=True
    (r/'boot_verification.log').write_text('\n'.join(lines)+'\n')
    result={'profile_seen':profile_seen,'stop_sent':zero_sent,'app_verified':True,'nvs_preserved':True,
            'servo_movement_commands_sent':False,'bridge_left_stopped_for_pcb_work':True,'statuses':statuses[-3:]}
    (r/'flash_result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
    assert profile_seen,'New firmware boot banner not observed'
finally:
    s.close()
