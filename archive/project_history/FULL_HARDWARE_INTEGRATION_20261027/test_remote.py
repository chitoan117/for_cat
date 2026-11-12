import hashlib,json,os,re,shutil,subprocess,sys,tarfile
from pathlib import Path
R=Path('/home/toan/for_cat');E=Path(EVIDENCE);S=E/'stage';S.mkdir(exist_ok=False)
with tarfile.open(E/'integration_stage.tar.gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
  p=S/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with tar.extractfile(m) as src,p.open('xb') as dst:shutil.copyfileobj(src,dst)
P=S/'payload';F=S/'firmware/esp32';B=E/'build';B.mkdir();results=[]
for folder in ('docs','esp32'):
 shutil.copytree(R/folder,P/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.pio','__pycache__'))
env={**os.environ,'PYTHONPATH':str(P/'jetson')+':'+str(R),'PYTHONDONTWRITEBYTECODE':'1','DATABASE_PATH':str(B/'test_default.db'),
 'ESP32_TRANSPORT':'MOCK','CAMERA_PROVIDER':'MOCK','AI_RUNTIME':'MOCK','AI_SHADOW_MODE':'true','FORCAT_TEST_PROJECT_ROOT':str(P),'FORCAT_BRIDGE_TEST_BINARY':str(B/'esp32_bridge')}
for k in ('FORCAT_FLUTTER_WEB_DIR','ESP32_BRIDGE_ENABLED','SCHEDULED_DRY_RUN_WORKER_ENABLED','SYSTEM_STATE_PROVIDER'):env.pop(k,None)
def run(name,args,cwd=P,timeout=300):
 p=subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);(E/(name+'.log')).write_bytes(p.stdout);results.append({'name':name,'cmd':args,'exit':p.returncode})
 (E/'test_commands.json').write_text(json.dumps(results,indent=2));assert p.returncode==0,p.stdout.decode('utf-8','replace')[-16000:]
 return p.stdout.decode('utf-8','replace')
flags=subprocess.check_output(['pkg-config','--cflags','--libs','json-c','sqlite3']).decode().split()
run('bridge_build',['g++','-std=c++14','-O2','-Wall','-Wextra','-Wpedantic','-Werror',str(P/'jetson/device/esp32_bridge.cpp'),*flags,'-o',str(B/'esp32_bridge')])
native={}
for name,source,includes,links,argv in (
 ('quad_sampler',F/'test/quad_sampler.cpp',[],[],[]),
 ('quad_loop',F/'test/quad_firmware_loop.cpp',['-I'+str(F/'test/arduino_stub')],[],[]),
 ('quad_compat',F/'test/quad_bridge_compat.cpp',['-I'+str(P/'jetson/device')],['-ljson-c'],[str(E/'quad_loop.log')]),
 ('ultrasonic_parser',P/'jetson/device/test_ultrasonic.cpp',[],['-ljson-c'],[str(P/'jetson/tests/fixtures/esp32_current.synthetic.json')]),
 ('legacy_native',F/'test/native_drivers.cpp',[],[],[]),
 ('feed_policy',P/'jetson/device/test_policy.cpp',[],['-ljson-c'],[str(P/'jetson/tests/fixtures/esp32_current.synthetic.json')]),
 ('decision',P/'jetson/device/test_decision.cpp',[],['-ljson-c'],[]),
 ('dispense_fake',P/'jetson/device/test_dispense_35.cpp',[],[],[]),
):
 run(name+'_build',['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(F/'include'),*includes,str(source),*links,'-o',str(B/name)])
 native[name]=run(name,[str(B/name),*argv],timeout=60)[-1000:]
 if name=='quad_loop':
  frames=[json.loads(l) for l in (E/'quad_loop.log').read_text().splitlines() if l.startswith('{')]
  assert len(frames)==2 and all(len(json.dumps(f,separators=(',',':')))<4096 for f in frames)
  assert all(set(f['ultrasonic'])=={'HC_SR04_1','HC_SR04_2','JSN_SR04T_1','JSN_SR04T_2'} for f in frames)
backend=run('backend_tests',[sys.executable,'-m','pytest','jetson/tests','-q','-ra'],timeout=480)
run('pip_check',[sys.executable,'-m','pip','check'])
summary={'status':'SOFTWARE_READY','evidence':str(E),'backend_tests':int(re.search(r'(\d+) passed',backend).group(1)),'native':native,'bridge_binary_sha256':hashlib.sha256((B/'esp32_bridge').read_bytes()).hexdigest()}
(E/'software_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
