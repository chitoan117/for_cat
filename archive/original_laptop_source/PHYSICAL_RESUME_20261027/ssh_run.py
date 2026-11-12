"""Run reviewed local Python script over existing SSH, preserving captured output."""
import argparse,json,subprocess,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
OUT=Path(__file__).resolve().parent
HOST=json.loads((OUT/'connection.json').read_text())['verified_host'] if (OUT/'connection.json').exists() else 'server-jetson.local'
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson','toan@'+HOST]
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('script');p.add_argument('--timeout',type=int,default=240);args=p.parse_args()
 script=Path(args.script);assert script.is_file() and OUT.is_dir()
 result=subprocess.run(SSH+['/home/toan/for_cat/.venv/jetson-integration/bin/python -'],input=script.read_bytes(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=args.timeout)
 (OUT/(script.stem+'.stdout.log')).write_bytes(result.stdout);(OUT/(script.stem+'.stderr.log')).write_bytes(result.stderr)
 print(result.stdout.decode('utf-8','replace'));print(result.stderr.decode('utf-8','replace'),file=sys.stderr)
 if result.returncode==0:
  try:(OUT/(script.stem+'_result.json')).write_text(json.dumps(json.loads(result.stdout),indent=2,ensure_ascii=False),encoding='utf-8')
  except ValueError:pass
 raise SystemExit(result.returncode)
