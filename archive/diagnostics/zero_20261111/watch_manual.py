"""Observe local button and non-actuating diagnostics directly on UART."""
from pathlib import Path
import json,serial,subprocess,time
R=Path(__file__).resolve().parent
units=('for-cat-api.service','for-cat-esp32-bridge.service')
before={u:subprocess.check_output(['systemctl','--user','is-active',u],text=True).strip() for u in units}
subprocess.run(['systemctl','--user','stop',*units],check=True,timeout=20)
lines=[];frames=[];pending=bytearray();count=0
try:
    with serial.Serial('/dev/ttyTHS1',115200,timeout=.1,write_timeout=.5,rtscts=False,dsrdtr=False) as s:
        s.write(b'jetson_ping\nmode\nhx_diag\nservo_position\npump_status\n')
        end=time.monotonic()+45;last=time.monotonic()
        print('UART monitor ready; diagnostic commands only, no feed/motor command.',flush=True)
        with (R/'manual_uart_raw.log').open('w') as log:
            while time.monotonic()<end:
                if time.monotonic()-last>=1:s.write(b'jetson_ping\n');last=time.monotonic()
                part=s.read(4096);count+=len(part);pending.extend(part)
                while b'\n' in pending:
                    raw,_,tail=pending.partition(b'\n');pending=bytearray(tail)
                    line=raw.decode('utf8',errors='replace').strip();lines.append(line);log.write(line+'\n');log.flush()
                    if line.startswith('{'):
                        try:
                            frame=json.loads(line)
                            if frame.get('type')=='status':frames.append(frame)
                        except ValueError:pass
                    elif line:print(line[:280],flush=True)
    result={'bytes':count,'lines':len(lines),'status_frames':len(frames),'events':[line for line in lines if not line.startswith('{')],'frames':frames}
    (R/'manual_uart_result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'bytes':count,'lines':len(lines),'status_frames':len(frames),'last_status':{k:frames[-1].get(k) for k in ('boot','ms','bench_state','inspect_required','demo_exited','signed_g','grams','button_pressed','button_count')} if frames else None}),flush=True)
finally:
    for unit,state in before.items():
        if state=='active':subprocess.run(['systemctl','--user','start',unit],check=True,timeout=20)
