import json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    out=ROOT/'evidence/python_extras'
    if out.exists():raise ValueError('preserve extras evidence')
    out.mkdir()
    q=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','-o','pythonpath='+str(ROOT/'candidate/backend'),
        str(ROOT/'tests/test_preference.py'),str(ROOT/'tests/test_data_extra.py')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (out/'tests.log').write_bytes(q.stdout)
    if q.returncode:raise RuntimeError('extras failed; read '+str(out))
    result={'new_cases':int(re.search(rb'(\d+) passed',q.stdout).group(1)),'source':'SIMULATED','physical_pass':False,'APP_FLASH':'NO_GO'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
