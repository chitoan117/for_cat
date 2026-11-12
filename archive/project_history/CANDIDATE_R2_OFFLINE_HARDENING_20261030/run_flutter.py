import argparse,json,os,re,subprocess,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('backend');parser.add_argument('--probe-only',action='store_true');a=parser.parse_args()
    backend=Path(a.backend);out=ROOT/'evidence'/('flutter_'+datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
    env={**os.environ,'HARDENING_OUTPUT':str(backend.resolve()),'FLUTTER_SUPPRESS_ANALYTICS':'true'}
    def run(args,name):
        q=subprocess.run([r'D:\dev\flutter\bin\flutter.bat']+args,cwd=ROOT/'candidate/flutter',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240,env=env)
        (out/(name+'.log')).write_bytes(q.stdout)
        if q.returncode:raise RuntimeError(name+' failed; see '+str(out))
        return q.stdout.decode('utf-8','replace')
    run(['pub','get','--offline'],'pub')
    args=['test','--no-pub','--reporter','expanded','test/hardening_test.dart']
    if a.probe_only:args+=['--name','baseline']
    text=run(args,'tests')
    run(['analyze','--no-pub'],'analyze')
    value={'tests':int(re.search(r'\+(\d+): All tests passed',text).group(1)),'analyze':'NO_ISSUES','source':'SIMULATED','physical_pass':False,'APP_FLASH':'NO_GO'}
    (out/'result.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'output':str(out),**value},indent=2))
if __name__=='__main__':main()
