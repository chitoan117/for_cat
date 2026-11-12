from pathlib import Path
import json,subprocess,time,serial
R=Path(__file__).resolve().parent
unit='for-cat-esp32-bridge.service'
subprocess.run(['systemctl','--user','stop',unit],check=True,timeout=15)
count=0;lines=[];pending=bytearray();statuses=[]
try:
    s=serial.Serial('/dev/ttyTHS1',115200,timeout=.1,write_timeout=.5,rtscts=False,dsrdtr=False)
    with s:
        s.write(b'pump_auto off\npump_off\npump_status\njetson_ping\n')
        end=time.monotonic()+12;last=time.monotonic()
        while time.monotonic()<end:
            if time.monotonic()-last>=1:s.write(b'jetson_ping\n');last=time.monotonic()
            part=s.read(4096);count+=len(part);pending.extend(part)
            while b'\n' in pending:
                line,_,tail=pending.partition(b'\n');pending=bytearray(tail)
                text=line.decode('utf8',errors='replace').strip();lines.append(text)
                if text.startswith('{'):
                    try:
                        obj=json.loads(text)
                        if obj.get('type')=='status':statuses.append(obj)
                    except ValueError:pass
    result={'bytes':count,'lines':len(lines),'status_frames':len(statuses),'line_tails':lines[-8:],'last_status':statuses[-1] if statuses else None}
    (R/'uart_probe_result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'bytes':count,'lines':len(lines),'status_frames':len(statuses),'sample':lines[-1][:180] if lines else None}))
finally:subprocess.run(['systemctl','--user','start',unit],check=True,timeout=15)
