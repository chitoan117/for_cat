"""Only new fake-service maintenance tests; never runs prior qualified suites."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
HERE=Path(__file__).resolve().parent;KIT=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    locked=[KIT/'manifest.json',KIT/'manifest.sha256',KIT/'SHA256SUMS',
            KIT/'web_hardware/gcc75_fix/transfer_manifest.json',KIT/'web_hardware/gcc75_fix/TRANSFER_SHA256SUMS']
    before={str(p):sha(p) for p in locked}
    assert before[str(KIT/'manifest.json')]=='2d9c5d18e8b911874b033b4e93784ba7a34f591011002c46411a191c5196099c'
    for name in ('readiness.py','serial_window.py','boot_capture.py','security_flags.py','app_plan.py'):
        ast.parse((HERE/name).read_text(),feature_version=(3,6))
    out=HERE/'validation';out.mkdir(exist_ok=True)
    p=subprocess.run([sys.executable,'-B',str(HERE/'test_new_tooling.py')],cwd=HERE,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    (out/'new_tooling_tests.log').write_bytes(p.stdout)
    if p.returncode:raise RuntimeError('new tests failed; read validation/new_tooling_tests.log')
    count=int(re.search(rb'Ran (\d+) tests',p.stdout).group(1))
    assert all(sha(p)==before[str(p)] for p in locked)
    result={'new_fake_service_tests_passed':count,'Python36_grammar':'PASS_NOT_TARGET_RUNTIME',
        'locked_integrity_files_unchanged':True,'existing_qualified_tests_rerun':False,
        'real_service_or_device_execution':'NOT_RUN','ARM64_native':'OWNER_CONFIRMED_PASS_NOT_RERUN',
        'APP_FLASH':'NO_GO','physical_pass':False}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    files={p.relative_to(HERE).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in HERE.rglob('*')
        if p.is_file() and not any(x in ('__pycache__','evidence') for x in p.relative_to(HERE).parts)
        and p.name not in ('INTEGRITY.json','SHA256SUMS')}
    (HERE/'INTEGRITY.json').write_text(json.dumps({'kind':'MAINTENANCE_READINESS_ONLY','qualified_590_manifest_unchanged':before[str(KIT/'manifest.json')],
        'files':dict(sorted(files.items()))},indent=2)+'\n')
    (HERE/'SHA256SUMS').write_bytes(''.join(v['sha256']+'  '+k+'\n' for k,v in sorted(files.items())).encode())
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
