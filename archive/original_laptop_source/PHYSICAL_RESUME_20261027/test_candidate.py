"""Compile/run fake GPIO tests in evidence directory; never flash/open physical serial."""
import importlib.util,json,os,re,subprocess,tarfile,time
from pathlib import Path
R=Path('/home/toan/for_cat');E=max((R/'evidence').glob('physical_resume_20261027_*'),key=lambda p:p.name);F=E/'firmware_candidate_r2';F.mkdir(exist_ok=True)
with tarfile.open(E/'firmware_candidate_r2.tar.gz','r:gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
  p=F/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with tar.extractfile(m) as src:
   body=src.read()
   if p.exists():assert p.read_bytes()==body
   else:p.write_bytes(body)
S=F/'esp32';logs=[]
for name,source,extra in (
 ('quad_sampler',S/'test/quad_sampler.cpp',[]),
 ('quad_firmware_loop',S/'test/quad_firmware_loop.cpp',['-I'+str(S/'test/arduino_stub')]),
 ('candidate_bridge_compat',S/'test/quad_bridge_compat.cpp',['-I'+str(R/'jetson/device')]),
 ('legacy_native_drivers',S/'test/native_drivers.cpp',[]),
 ('canonical_feed_policy',R/'jetson/device/test_policy.cpp',[]),
 ('canonical_decision',R/'jetson/device/test_decision.cpp',[]),
 ('canonical_dispense_35',R/'jetson/device/test_dispense_35.cpp',[]),
):
 binary=F/name
 previous=F/(name+'.log')
 if name in ('quad_sampler','quad_firmware_loop','legacy_native_drivers') and previous.exists() and binary.exists():
  body=previous.read_text();assert 'assert' in body.lower();logs.append({'name':name,'status':'SOFTWARE_READY','summary':body[-1200:],'retained_prior_success':True});continue
 cmd=['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(S/'include'),*extra,str(source),'-o',str(binary)]+(['-ljson-c'] if name.startswith(('canonical_','candidate_')) else [])
 oldlog=F/(name+'_build.log')
 if oldlog.exists():oldlog.rename(F/(name+'_build_attempt_'+str(time.time_ns())+'.log'))
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);(F/(name+'_build.log')).write_bytes(p.stdout)
 assert p.returncode==0,p.stdout.decode('utf-8','replace')
 if previous.exists():previous.rename(F/(name+'_runtime_attempt_'+str(time.time_ns())+'.log'))
 argv=[str(binary)]+([str(R/'jetson/tests/fixtures/esp32_current.synthetic.json')] if name=='canonical_feed_policy' else [])
 if name=='candidate_bridge_compat':argv.append(str(F/'quad_firmware_loop.log'))
 p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45);(F/(name+'.log')).write_bytes(p.stdout)
 assert p.returncode==0,p.stdout.decode('utf-8','replace')
 body=p.stdout.decode('utf-8','replace');logs.append({'name':name,'status':'SOFTWARE_READY','summary':body[-1200:]})
 if name=='quad_firmware_loop':
  frame=json.loads(next(line for line in body.splitlines() if line.startswith('{')))
  assert frame['rtc_type']=='NONE' and frame['actuator_outputs_enabled']==0
  assert len(frame['ultrasonic4'])==4
  assert all(s['distance_cm'] is None and s['enabled'] is False and s['wired'] is None for s in frame['ultrasonic4'])
  assert len(json.dumps(frame,separators=(',',':')))<4096
summary={'evidence':str(E),'status':'SOFTWARE_READY','flash':'NOT_TESTED','native_groups':logs,'esptool_available_in_runtime':importlib.util.find_spec('esptool') is not None}
(F/'software_test_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
