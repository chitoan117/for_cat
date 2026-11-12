"""Windows-only fresh test log for R2 transfer/PLAN guards, no device operations."""
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
def main():
    if sys.platform!='win32':raise ValueError('this wrapper records Windows tooling tests only')
    out=ROOT/('validation_tooling_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir()
    argv=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','-o','pythonpath='+str(ROOT),str(ROOT/'tests/test_r2_tooling.py')]
    p=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
    (out/'tests.log').write_bytes(p.stdout)
    if p.returncode:raise RuntimeError('R2 tooling tests failed; see '+str(out))
    count=int(re.search(rb'(\d+) passed',p.stdout).group(1))
    value={'scope':'WINDOWS_TEMP_FILES_AND_DEFAULT_PLAN_ONLY','command':argv,
        'log':str(out.relative_to(ROOT)/'tests.log'),'tests_passed':count,
        'ARM64_NATIVE_TEST_PASS':'NOT_RUN','serial_opened':False,'camera_opened':False,
        'services_changed':False,'physical_pass':False,'APP_FLASH':'NO_GO'}
    (out/'result.json').write_text(json.dumps(value,indent=2)+'\n')
    (ROOT/'WINDOWS_TOOLING_RESULT.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value,indent=2))
if __name__=='__main__':main()
