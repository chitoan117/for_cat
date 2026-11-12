"""Compile/test only in a NEW Jetson evidence directory; preserve canonical files."""
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import base64

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
PAY=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload'
FW=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
previous=json.loads((OUT/'jetson_result.json').read_text(encoding='utf-8')).get('remote_build_directory','') if (OUT/'jetson_result.json').exists() else ''
remote='/home/toan/for_cat/evidence/cat_approach_dog_buzzer_build_'+stamp
ssh=['ssh','-6','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson','toan@fe80::2f03:e65b:a064:b574%13']
bundle=io.BytesIO()
with tarfile.open(fileobj=bundle,mode='w:gz') as tar:
 for name in ('esp32_bridge.cpp','telemetry.h','ultrasonic_telemetry.h','feed_policy.h','decision_logic.h','approach_fusion.h','food_roi.h','roi_species.h','roi_ai_source.cpp','roi_review.cpp','preview_queue.h','preview_publisher.h','test_policy.cpp','test_decision.cpp'):
  tar.add(PAY/'jetson/device'/name,arcname=name)
 for name in ('uart_v1.h','dog_warning_protocol.h'):tar.add(FW/'include'/name,arcname=name)
 tar.add(PAY/'jetson/tests/fixtures/esp32_current.synthetic.json',arcname='fixture.json')
 tar.add(OUT/'test_bridge_pty.py',arcname='test_bridge_pty.py')
 if (OUT/'production.synthetic.json').exists():tar.add(OUT/'production.synthetic.json',arcname='production.synthetic.json')
program=r'''
import hashlib,io,json,os,subprocess,sys,tarfile,shutil
from pathlib import Path
out=Path(REMOTE);assert out.parent.is_dir();out.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
root=Path('/home/toan/for_cat');ai=root/'jetson/ai'
protected=[ai/'cat_dog_trt.cpp',ai/'cat_dog_trt',root/'models/tensorrt/yolov8n_320_fp16.engine',root/'.git/index']
before={str(p):sha(p) for p in protected}
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 for member in tar.getmembers():assert '/' not in member.name and not member.issym()
 tar.extractall(str(out))
def run(args,name):
 p=subprocess.run(args,cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=240)
 (out/name).write_text(p.stdout)
 if p.returncode:raise RuntimeError(p.stdout)
 return p.stdout
flags=subprocess.check_output(['pkg-config','--cflags','--libs','json-c','sqlite3'],universal_newlines=True).split()
base=['g++','-std=c++14','-O2','-Wall','-Wextra','-Wpedantic','-Werror','-I'+str(out)]
previous=Path(PREVIOUS)
def unchanged(names):return bool(PREVIOUS) and all((previous/name).is_file() and sha(previous/name)==sha(out/name) for name in names)
if unchanged(['esp32_bridge.cpp','telemetry.h','ultrasonic_telemetry.h','feed_policy.h','decision_logic.h','approach_fusion.h','food_roi.h','dog_warning_protocol.h','uart_v1.h']):
 shutil.copy2(str(previous/'esp32_bridge'),str(out/'esp32_bridge'));shutil.copyfile(str(previous/'bridge_compile.log'),str(out/'bridge_compile.log'))
else:
 run(base+[str(out/'esp32_bridge.cpp'),'-o',str(out/'esp32_bridge')]+flags,'bridge_compile.log')
if unchanged(['test_policy.cpp','feed_policy.h','telemetry.h','ultrasonic_telemetry.h','fixture.json']):
 shutil.copyfile(str(previous/'policy_test.log'),str(out/'policy_test.log'));policy=(out/'policy_test.log').read_text()
else:
 run(base+[str(out/'test_policy.cpp'),'-o',str(out/'test_policy')]+flags,'policy_compile.log')
 policy=run([str(out/'test_policy'),str(out/'fixture.json')],'policy_test.log')
if unchanged(['test_decision.cpp','decision_logic.h','feed_policy.h']):
 shutil.copyfile(str(previous/'decision_test.log'),str(out/'decision_test.log'));decision=(out/'decision_test.log').read_text()
else:
 run(base+[str(out/'test_decision.cpp'),'-o',str(out/'test_decision')],'decision_compile.log')
 decision=run([str(out/'test_decision')],'decision_test.log')
tests=run([str(root/'.venv/jetson-integration/bin/python'),str(out/'test_bridge_pty.py')],'pty_test.log')
cuda='/usr/local/cuda-10.2'
roi_flags=subprocess.check_output(['pkg-config','--cflags','--libs','opencv4','json-c','sqlite3'],universal_newlines=True).split()
if unchanged(['roi_ai_source.cpp','roi_species.h','food_roi.h','preview_queue.h','preview_publisher.h','telemetry.h','ultrasonic_telemetry.h']):
 shutil.copy2(str(previous/'roi_ai_source'),str(out/'roi_ai_source'));shutil.copyfile(str(previous/'roi_compile.log'),str(out/'roi_compile.log'))
else:
 run(['g++','-std=c++14','-O2','-pthread','-Wno-deprecated-declarations','-I'+str(ai),'-I'+cuda+'/include','-I'+str(out),str(out/'roi_ai_source.cpp'),'-o',str(out/'roi_ai_source'),'-L'+cuda+'/lib64','-lnvinfer','-lcudart']+roi_flags,'roi_compile.log')
if unchanged(['roi_review.cpp']):
 shutil.copy2(str(previous/'roi_review'),str(out/'roi_review'));shutil.copyfile(str(previous/'roi_review_compile.log'),str(out/'roi_review_compile.log'))
else:
 run(['g++','-std=c++14','-O2','-Wall','-Wextra','-Werror',str(out/'roi_review.cpp'),'-o',str(out/'roi_review')]+roi_flags,'roi_review_compile.log')
after={str(p):sha(p) for p in protected};assert before==after
result={'remote_build_directory':str(out),'bridge_build':'PASS','roi_source_build':'PASS','roi_review_build':'PASS','reused_verified_inputs':str(previous) if PREVIOUS else None,'policy':policy,'decision':decision,'pty':json.loads(tests),'protected_before':before,'protected_after':after,'hardware_opened':False,'deployed_over_canonical':False}
(out/'result.json').write_text(json.dumps(result,indent=2))
with tarfile.open(str(out/'host_binaries.tar.gz'),'w:gz') as tar:
 for name in ('esp32_bridge','roi_ai_source','roi_review','result.json','bridge_compile.log','roi_compile.log','roi_review_compile.log','pty_test.log','policy_test.log','decision_test.log'):tar.add(str(out/name),arcname=name)
print(json.dumps(result,indent=2))
'''.replace('REMOTE',repr(remote)).replace('PREVIOUS',repr(previous))
encoded=base64.b64encode(program.encode()).decode()
p=subprocess.run(ssh+["/usr/bin/python3 -c \"exec(__import__('base64').b64decode('"+encoded+"'))\""],input=bundle.getvalue(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600)
(OUT/'jetson_build.stdout.log').write_bytes(p.stdout);(OUT/'jetson_build.stderr.log').write_bytes(p.stderr)
print(p.stdout.decode('utf-8','replace'));print(p.stderr.decode('utf-8','replace'))
if p.returncode:raise SystemExit(p.returncode)
result=json.loads(p.stdout);(OUT/'jetson_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
command="/usr/bin/python3 -c \"import sys;sys.stdout.buffer.write(open('"+remote+"/host_binaries.tar.gz','rb').read())\""
p=subprocess.run(ssh+[command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
assert p.returncode==0,p.stderr.decode()
(OUT/'host_binaries.tar.gz').write_bytes(p.stdout)
with tarfile.open(fileobj=io.BytesIO(p.stdout),mode='r:gz') as tar:
 (OUT/'jetson').mkdir(exist_ok=True)
 for member in tar.getmembers():assert '/' not in member.name and not member.issym()
 tar.extractall(OUT/'jetson',filter='data')
print('JETSON_FOCUSED_BUILD_AND_PTY_PASS; canonical source/binary/engine/index unchanged')
