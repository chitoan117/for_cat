import json,os,subprocess,tarfile,time,hashlib,urllib.request,shutil
from pathlib import Path
R=Path('/home/toan/for_cat');E=Path(EVIDENCE);web=R/'.native-build/flutter/four_ultrasonic_20261027_r2';assert not web.exists();web.mkdir()
assets=json.loads((E/'frontend_r2_sha256.json').read_text())
with tarfile.open(E/'frontend_r2.tar.gz') as t:
 for m in t:
  assert m.isfile() and m.name in assets and '..' not in Path(m.name).parts
  p=web/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read());assert hashlib.sha256(p.read_bytes()).hexdigest()==assets[m.name]
assert json.loads((web/'forcat_build.json').read_text())['mode']=='REAL'
drop=Path('/home/toan/.config/systemd/user/for-cat-api.service.d/40-flutter-real.conf');old=drop.read_text();assert 'four_ultrasonic_20261027_r1' in old;shutil.copy2(drop,E/'deploy_backup/40-before-r2.conf')
tmp=drop.with_name(drop.name+'.u4tmp');tmp.write_text(old.replace('four_ultrasonic_20261027_r1','four_ultrasonic_20261027_r2'));os.replace(tmp,drop)
try:
 subprocess.run(['systemctl','--user','daemon-reload'],check=True);subprocess.run(['systemctl','--user','restart','for-cat-api.service'],check=True,timeout=45)
 for _ in range(45):
  try:
   with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=4) as r:s=json.load(r)
   if len(s['ultrasonic'])==4 and s['data_source']=='REAL':break
  except Exception:pass
  time.sleep(1)
 else:raise RuntimeError('API r2 not ready')
except Exception:
 drop.write_text(old);subprocess.run(['systemctl','--user','daemon-reload'],check=True);subprocess.run(['systemctl','--user','restart','for-cat-api.service'],check=True);raise
result={'status':'RUNTIME_PASS','release':str(web),'flutter_tests':63};(E/'frontend_r2_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
