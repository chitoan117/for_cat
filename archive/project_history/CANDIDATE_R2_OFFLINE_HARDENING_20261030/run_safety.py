import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;WS=ROOT.parent
ZIG=WS/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',action='store_true');p.add_argument('--label');a=p.parse_args()
    name='baseline_safety' if a.baseline else 'fixed_safety'
    if a.label:
        if not re.fullmatch(r'[A-Za-z0-9_]+',a.label):raise ValueError('safe new run label required')
        name+='_'+a.label
    out=ROOT/'evidence'/name
    if out.exists():raise ValueError('preserve previous run; choose a new runner revision')
    out.mkdir()
    include=WS/'CANDIDATE_GCC75_R2_20261029/candidate/firmware/include' if a.baseline else ROOT/'candidate/firmware/include'
    def run(argv,label,expected=0):
        q=subprocess.run([str(x) for x in argv],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        (out/(label+'.log')).write_bytes(q.stdout)
        if q.returncode!=expected:raise RuntimeError(label+' unexpected exit '+str(q.returncode))
        return q.stdout.decode('utf-8','replace')
    exe=out/'safety.exe'
    run([ZIG,'c++','-std=c++14','-O1','-Wall','-Wextra','-Werror','-I'+str(include),ROOT/'tests/safety_audit.cpp','-o',exe],'compile')
    probes=run([exe,'--probe'],'probes')
    text=run([exe],'tests',1 if a.baseline else 0)
    result={'mode':'BASELINE_EXPECTED_FAILURE' if a.baseline else 'FIXED_SIMULATION_TEST',
        'header_sha256':hashlib.sha256((include/'m4/dispense_bench.h').read_bytes()).hexdigest(),
        'probes':probes,'physical_pass':False,'APP_FLASH':'NO_GO'}
    if not a.baseline:
        m=re.search(r'HARDENING_SAFETY_PASS cases=(\d+) checks=(\d+)',text);result.update(cases=int(m.group(1)),checks=int(m.group(2)))
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
