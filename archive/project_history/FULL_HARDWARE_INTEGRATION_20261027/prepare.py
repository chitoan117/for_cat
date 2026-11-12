import contextlib,hashlib,io,json,shutil,subprocess,sys,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;OLD=Path(r'D:\for_cat\PHYSICAL_RESUME_20261027');sys.path.insert(0,str(OLD));from ssh_run import SSH,HOST
code=(OLD/'preflight_backup.py').read_text().replace("'physical_resume_20261027_'","'full_hardware_integration_20261027_'")
wrapped='import contextlib,io,json,shutil,hashlib\n_capture=io.StringIO()\nwith contextlib.redirect_stdout(_capture):\n'+''.join(' '+line+'\n' for line in code.splitlines())+'\nsummary=json.loads(_capture.getvalue())\n'
wrapped+='shutil.copy2(ROOT/".native-build/esp32/esp32_bridge",E/"backup/esp32_bridge.original")\nsummary["bridge_binary_sha256"]=digest(E/"backup/esp32_bridge.original")\n(E/"preflight_summary.json").write_text(json.dumps(summary,indent=2))\n(E/"manifest_phase0_sha256.json").write_text(json.dumps({str(p.relative_to(E)):digest(p) for p in E.rglob("*") if p.is_file() and p.name!="manifest_phase0_sha256.json"},indent=2))\nprint(json.dumps(summary,indent=2))\n'
r=subprocess.run(SSH+['/home/toan/for_cat/.venv/jetson-integration/bin/python -'],input=wrapped.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300)
(O/'preflight.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode()
summary=json.loads(r.stdout);assert all(summary['safety_checks'].values());(O/'preflight.json').write_text(json.dumps(summary,indent=2))
E=summary['evidence'];(O/'connection.json').write_text(json.dumps({'host':HOST,'evidence':E}))
for remote,name in [('backup/backend_source_config_firmware.tar.gz','backend_before.tar.gz'),('audit/before_bridge.json','bridge_before.json'),('audit/before_status.json','status_before.json')]:
 r=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson','toan@'+HOST+':'+E+'/'+remote,str(O/name)],capture_output=True,timeout=120);assert r.returncode==0,r.stderr.decode()
with tarfile.open(O/'backend_before.tar.gz') as t:
 for m in t.getmembers():
  if not m.isfile() or not m.name.startswith(('jetson/','config/','docs/','scripts/')):continue
  target=O/'payload'/m.name;target.parent.mkdir(parents=True,exist_ok=True)
  with t.extractfile(m) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
F=O/'firmware/esp32';shutil.copytree(OLD/'firmware_candidate/esp32',F,ignore=shutil.ignore_patterns('.pio','__pycache__'))
P=Path(r'D:\DA_KT_NC\feeder_demo');before={}
for folder in ('lib','test','web','assets'):
 for p in (P/folder).rglob('*'):
  if p.is_file():
   dest=O/'frontend_before'/p.relative_to(P);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);before[p.relative_to(P).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
(O/'frontend_before_sha256.json').write_text(json.dumps(before,indent=2))
print(json.dumps({'evidence':E,'safety':summary['safety_checks'],'index':summary['index_sha256'],'current_frontend':summary['current_frontend']},indent=2))
