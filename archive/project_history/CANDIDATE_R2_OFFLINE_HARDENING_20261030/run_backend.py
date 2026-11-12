import json,os,re,subprocess,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    out=ROOT/'evidence'/('backend_'+datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
    env={**os.environ,'HARDENING_OUTPUT':str(out),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
    q=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','-o',
        'pythonpath='+str(ROOT/'candidate/backend')+' '+str(ROOT/'candidate'),str(ROOT/'tests/test_backend.py')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180,env=env)
    (out/'tests.log').write_bytes(q.stdout)
    if q.returncode:raise RuntimeError('new backend tests failed: '+str(out))
    result={'cases':int(re.search(rb'(\d+) passed',q.stdout).group(1)),'source':'SIMULATED','physical_pass':False,'APP_FLASH':'NO_GO'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'output':str(out),**result},indent=2))
if __name__=='__main__':main()
