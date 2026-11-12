import hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
R=Path('/home/toan/for_cat');E=Path(EVIDENCE);P=E/'stage/payload';B=E/'build'
shutil.copy2(R/'pytest.ini',P/'pytest.ini')
for source in (R/'ai').rglob('*.py'):
    if '__pycache__' in source.parts:continue
    target=P/'ai'/source.relative_to(R/'ai');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
tap=P/'.native-build/esp32/ai_state_tap';tap.parent.mkdir(parents=True,exist_ok=True)
if not tap.exists():shutil.copy2(R/'.native-build/esp32/ai_state_tap',tap)  # existing passive tap, synthetic stdin only; not detector/engine
env={**os.environ,'PYTHONPATH':str(P/'jetson')+':'+str(R/'jetson')+':'+str(R),'PYTHONDONTWRITEBYTECODE':'1','DATABASE_PATH':str(B/'test_default.db'),
 'ESP32_TRANSPORT':'MOCK','CAMERA_PROVIDER':'MOCK','AI_RUNTIME':'MOCK','AI_SHADOW_MODE':'true','FORCAT_TEST_PROJECT_ROOT':str(P),'FORCAT_BRIDGE_TEST_BINARY':str(B/'esp32_bridge')}
for k in ('FORCAT_FLUTTER_WEB_DIR','ESP32_BRIDGE_ENABLED','SCHEDULED_DRY_RUN_WORKER_ENABLED','SYSTEM_STATE_PROVIDER'):env.pop(k,None)
log=E/'backend_tests.log'
if log.exists():
    import time
    shutil.copy2(log,E/('backend_tests_attempt_'+str(time.time_ns())+'.log'))
cmd=[sys.executable,'-m','pytest','-c',str(P/'pytest.ini'),'--rootdir',str(P),'jetson/tests','-q','-ra']
p=subprocess.run(cmd,cwd=P,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=480);log.write_bytes(p.stdout)
assert p.returncode==0,p.stdout.decode('utf-8','replace')[-22000:]
check=subprocess.run([sys.executable,'-m','pip','check'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(E/'pip_check.log').write_bytes(check.stdout);assert check.returncode==0
native={name:(E/(name+'.log')).read_text()[-1000:] for name in ('quad_sampler','quad_loop','quad_compat','ultrasonic_parser','legacy_native','feed_policy','decision','dispense_fake')}
summary={'status':'SOFTWARE_READY','evidence':str(E),'backend_tests':int(re.search(r'(\d+) passed',p.stdout.decode()).group(1)),'native':native,'bridge_binary_sha256':hashlib.sha256((B/'esp32_bridge').read_bytes()).hexdigest(),'pytest_rootdir':str(P)}
(E/'software_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
