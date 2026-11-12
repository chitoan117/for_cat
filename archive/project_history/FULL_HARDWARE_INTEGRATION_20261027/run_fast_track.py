"""Dispatcher for the one shared harness; never duplicates sensor procedure code."""
import json,shlex,subprocess,sys
from pathlib import Path
O=Path(__file__).resolve().parent;C=json.loads((O/'connection.json').read_text());E=C['evidence'];sys.stdout.reconfigure(encoding='utf-8')
options=['-o','BatchMode=yes','-o','ConnectTimeout=12','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson']
for name in ('observe_ultrasonic.py','test_observe_ultrasonic.py'):
 r=subprocess.run(['scp',*options,str(O/name),'toan@'+C['host']+':'+E+'/'+name],capture_output=True,timeout=60)
 assert r.returncode==0,r.stderr.decode()
if '--status' in sys.argv and (O/'FAST_TRACK_PROGRESS.md').exists():
 r=subprocess.run(['scp',*options,str(O/'FAST_TRACK_PROGRESS.md'),'toan@'+C['host']+':'+E+'/fast_track_ultrasonic/PROGRESS.md'],capture_output=True,timeout=60);assert r.returncode==0,r.stderr.decode()
test=' '.join(shlex.quote(v) for v in ['/home/toan/for_cat/.venv/jetson-integration/bin/python','-m','unittest','discover','-s',E,'-p','test_observe_ultrasonic.py','-v'])
r=subprocess.run(['ssh',*options,'toan@'+C['host'],test],capture_output=True,timeout=60)
(O/'focused_harness_tests.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr).decode('utf-8','replace')
forward=sys.argv[1:] or ['--sequence','jsn1','hc2','jsn2','all','--samples','24','--target-cm','20','--adopt-hc1']
cmd=' '.join(shlex.quote(v) for v in ['/home/toan/for_cat/.venv/jetson-integration/bin/python',E+'/observe_ultrasonic.py','--evidence',E,*forward])
r=subprocess.run(['ssh',*options,'toan@'+C['host'],cmd],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600)
label='fast_track_status' if '--status' in forward else 'fast_track_flashcheck' if '--check-flash' in forward else 'fast_track_run'
(O/(label+'.log')).write_bytes(r.stdout+r.stderr);print(r.stdout.decode('utf-8','replace'));print(r.stderr.decode('utf-8','replace'),file=sys.stderr)
if r.returncode==0:
 try:(O/(label+'_result.json')).write_text(json.dumps(json.loads(r.stdout),indent=2))
 except ValueError:pass
raise SystemExit(r.returncode)
