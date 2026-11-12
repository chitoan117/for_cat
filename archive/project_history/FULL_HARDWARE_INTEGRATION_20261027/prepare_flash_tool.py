import json,subprocess
from pathlib import Path
E=Path(EVIDENCE);V=E/'flash_tool';python=V/'bin/python'
steps=[]
commands=[] if V.exists() else [('venv',['/home/toan/for_cat/.venv/jetson-integration/bin/python','-m','venv',str(V)])]
commands += [('install',[str(python),'-m','pip','install','--only-binary=:all:','--no-binary=esptool,reedsolo','esptool==5.3.0']),('version',[str(python),'-m','esptool','version']),('dependencies',[str(python),'-m','pip','freeze'])]
for name,args in commands:
 log=E/('flash_tool_'+name+'.log')
 if log.exists():
  import shutil,time
  shutil.copy2(log,E/('flash_tool_'+name+'_attempt_'+str(time.time_ns())+'.log'))
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180);(E/('flash_tool_'+name+'.log')).write_bytes(p.stdout);steps.append({'name':name,'exit':p.returncode})
 if p.returncode:break
result={'status':'SOFTWARE_READY' if all(s['exit']==0 for s in steps) and len(steps)>=3 else 'BLOCKED','steps':steps,'python':str(python),'serial_opened':False,'flash_performed':False}
(E/'flash_tool_status.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
