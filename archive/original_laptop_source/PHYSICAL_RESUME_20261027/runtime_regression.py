"""Read-only production checks + tests using isolated fixtures/PTYs only."""
import hashlib,json,os,re,sqlite3,subprocess,sys
from pathlib import Path
ROOT=Path('/home/toan/for_cat');E=max((ROOT/'evidence').glob('physical_resume_20261027_*'),key=lambda p:p.name)
OUT=E/'regression';OUT.mkdir(exist_ok=False)
env={**os.environ,'PYTHONPATH':str(ROOT/'jetson')+':'+str(ROOT),'PYTHONDONTWRITEBYTECODE':'1',
 'DATABASE_PATH':str(OUT/'isolated_default.db'),'ESP32_TRANSPORT':'MOCK','CAMERA_PROVIDER':'MOCK','AI_RUNTIME':'MOCK','AI_SHADOW_MODE':'true'}
for k in ('FORCAT_FLUTTER_WEB_DIR','SCHEDULED_DRY_RUN_WORKER_ENABLED','ESP32_BRIDGE_ENABLED','SYSTEM_STATE_PROVIDER'):env.pop(k,None)
commands=[];summary={'evidence':str(E),'status':'BLOCKED','scope':'SOFTWARE_REGRESSION_SYNTHETIC_FIXTURES_AND_PTY_ONLY'}
for name,cmd in (
 ('backend_all',[sys.executable,'-m','pytest','jetson/tests','-q','-ra']),
 ('pip_check',[sys.executable,'-m','pip','check']),
 ('git_diff_check',['git','diff','--check']),
 ('git_staged_diff_check',['git','diff','--cached','--check']),
):
 p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=420)
 (OUT/(name+'.log')).write_bytes(p.stdout);commands.append({'name':name,'cmd':cmd,'exit':p.returncode})
 (OUT/'commands.json').write_text(json.dumps(commands,indent=2))
 if p.returncode:
  summary['failed']=name;summary['tail']=p.stdout.decode('utf-8','replace')[-14000:];break
 if name=='backend_all':summary['backend_passed']=int(re.search(r'(\d+) passed',p.stdout.decode()).group(1))
else:summary['status']='SOFTWARE_READY'
pre=json.loads((E/'preflight_summary.json').read_text())
summary['index_preserved']=hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==pre['index_sha256']
summary['commands']=commands
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
assert summary['status']=='SOFTWARE_READY' and summary['index_preserved']
