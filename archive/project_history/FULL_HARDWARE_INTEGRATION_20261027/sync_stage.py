import json,subprocess,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;c=json.loads((O/'connection.json').read_text());archive=O/'stage_changes.tar.gz'
names=['config/hardware_current.json','docs/CURRENT_PROJECT_STATE.md','docs/FOUR_ULTRASONIC_20261027.md','jetson/app/device_state.py','jetson/app/system_state.py','jetson/app/ultrasonic_state.py','jetson/tests/test_ultrasonic_state.py','jetson/tests/test_system_state.py']
with tarfile.open(archive,'w:gz') as tar:
 for name in names:tar.add(O/'payload'/name,arcname=name)
r=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(archive),'toan@'+c['host']+':'+c['evidence']+'/'+archive.name],capture_output=True,timeout=120);assert r.returncode==0,r.stderr.decode()
code='from pathlib import Path;import tarfile;E=Path('+repr(c['evidence'])+');t=tarfile.open(E/"stage_changes.tar.gz");\nfor m in t:\n assert m.isfile() and ".." not in Path(m.name).parts and not Path(m.name).is_absolute();p=E/"stage/payload"/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())\n'
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson','toan@'+c['host'],'/home/toan/for_cat/.venv/jetson-integration/bin/python -'],input=code.encode(),capture_output=True,timeout=60);assert r.returncode==0,r.stderr.decode();print('Only owned test stage updated; production untouched')
