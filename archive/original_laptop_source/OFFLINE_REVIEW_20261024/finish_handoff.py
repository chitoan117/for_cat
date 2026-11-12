"""Record guarded-update tests and create a source-only transfer archive."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parent
BUNDLE=ROOT/'handoff'
result=subprocess.run([sys.executable,'-m','pytest',str(ROOT/'test_handoff_guard.py'),'-q'],
                      cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
(ROOT/'checks/handoff_guard.log').write_bytes(result.stdout)
print(result.stdout.decode('utf-8','replace'))
assert result.returncode==0
assert re.search(r'8 passed',result.stdout.decode('utf-8','replace'))
manifest=json.loads((BUNDLE/'manifest.json').read_text(encoding='utf-8'))
for name,record in manifest['files'].items():
    payload=(BUNDLE/'payload'/name).read_bytes()
    assert hashlib.sha256(payload).hexdigest()==record['after_sha256']
    assert (ROOT/'project'/name).read_bytes()==payload
print('PAYLOAD AND CURRENT OFFLINE SOURCE MATCH; NOT APPLIED TO JETSON')
archive=ROOT/'for_cat_backend_offline_20261024.zip'
assert not archive.exists()
members=['README.md','apply_source_update.py','manifest.json','review.diff']
members+=['payload/'+name for name in manifest['files']]
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as out:
    for name in members:out.write(BUNDLE/name,name)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(ROOT/'PACKAGE_SHA256.txt').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
(ROOT/'checks/handoff_summary.json').write_text(json.dumps({
    'scope':'OFFLINE_TEMP_GIT_TESTS_ONLY','guard_tests_passed':8,
    'payload_source_files':len(manifest['files']),'archive':archive.name,'sha256':digest,
    'jetson_deployment':'NOT_APPLIED','physical_tests':'NOT_PERFORMED'},indent=2),encoding='utf-8')
print('SOURCE-ONLY ARCHIVE',archive)
print('SHA256',digest)
