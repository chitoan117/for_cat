import json,subprocess,sys
from pathlib import Path
O=Path(__file__).resolve().parent;sys.stdout.reconfigure(encoding='utf-8');c=json.loads((O/'connection.json').read_text());s=Path(sys.argv[1]);timeout=int(sys.argv[2]) if len(sys.argv)>2 else 300
body="EVIDENCE="+repr(c['evidence'])+'\n'+s.read_text(encoding='utf-8')
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson','toan@'+c['host'],'/home/toan/for_cat/.venv/jetson-integration/bin/python -'],input=body.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
(O/(s.stem+'.log')).write_bytes(r.stdout+r.stderr);print(r.stdout.decode('utf-8','replace'));print(r.stderr.decode('utf-8','replace'),file=sys.stderr)
if r.returncode==0:
 try:(O/(s.stem+'_result.json')).write_text(json.dumps(json.loads(r.stdout),indent=2))
 except ValueError:pass
raise SystemExit(r.returncode)
