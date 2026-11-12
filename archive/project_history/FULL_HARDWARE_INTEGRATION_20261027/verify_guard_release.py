import hashlib,json,shutil,subprocess,tarfile
from pathlib import Path
R=Path('/home/toan/for_cat');E=Path(EVIDENCE);G=E/'guard_tuning_release';assert not G.exists();G.mkdir()
with tarfile.open(E/'guard_tuning_release.tar.gz') as tar:
 for m in tar:
  assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
  p=G/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
M=json.loads((G/'release_manifest.json').read_text());F=G/'esp32'
for name,value in M['source_sha256'].items():assert sha(F/name)==value
for name,value in M['firmware'].items():assert sha(G/'host_release/firmware'/name)==value
test_results={}
for name,source,inc,lib,args in (
 ('quad_sampler',F/'test/quad_sampler.cpp',[],[],[]),
 ('quad_loop',F/'test/quad_firmware_loop.cpp',['-I'+str(F/'test/arduino_stub')],[],[]),
 ('quad_compat',F/'test/quad_bridge_compat.cpp',['-I'+str(R/'jetson/device')],['-ljson-c'],[str(G/'quad_loop.log')]),
 ('legacy_native',F/'test/native_drivers.cpp',[],[],[])):
 command=['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(F/'include'),*inc,str(source),*lib,'-o',str(G/name)]
 p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);(G/(name+'_build.log')).write_bytes(p.stdout);assert p.returncode==0,p.stdout.decode()
 p=subprocess.run([str(G/name),*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45);(G/(name+'.log')).write_bytes(p.stdout);assert p.returncode==0,p.stdout.decode()
 test_results[name]=p.stdout.decode()[-1200:]
 if name=='quad_loop':
  frames=[json.loads(line) for line in p.stdout.decode().splitlines() if line.startswith('{')]
  assert len(frames)==2 and all(f['ultrasonic_guard_ms']==80 for f in frames)
  assert all(len(json.dumps(f,separators=(',',':')))<4096 for f in frames)
  assert all(f['actuator_outputs_enabled']==0 and f['rtc_type']=='NONE' for f in frames)
changes=[]
base=E/'stage/firmware/esp32'
for name in M['source_sha256']:
 if (base/name).is_file() and sha(base/name)!=sha(F/name):
  changes.append(name)
  if Path(name).suffix in ('.h','.cpp','.ini'):
   assert not any(line.rstrip()!=line for line in (F/name).read_text().splitlines())
shutil.copy2(E/'flash_app_only.py',G/'flash_app_only.py');(G/'flash_tool').symlink_to(E/'flash_tool',target_is_directory=True)
plan=subprocess.run([str(E/'flash_tool/bin/python'),str(G/'flash_app_only.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15);(G/'flash_plan.log').write_bytes(plan.stdout)
assert plan.returncode==0 and json.loads(plan.stdout)['flash_performed'] is False
summary={'status':'SOFTWARE_READY','physical_status':'NOT_TESTED_NEW_GUARD_VALUES','tests':test_results,'changed_firmware_files':changes,
 'legacy_parser_accepts_extension':True,'flash_performed':False,'release':str(G),'image_sha256':M['firmware']['firmware.bin'],
 'manual_command':json.loads(plan.stdout)['manual_command']}
(G/'software_summary.json').write_text(json.dumps(summary,indent=2))
(G/'manifest_sha256.json').write_text(json.dumps({str(p.relative_to(G)):sha(p) for p in G.rglob('*') if p.is_file() and not p.is_symlink() and p.name!='manifest_sha256.json'},indent=2))
print(json.dumps(summary,indent=2))
