import json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;WS=ROOT.parent;ZIG=WS/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
def main():
    out=ROOT/'evidence/behavior'
    if out.exists():raise ValueError('preserve previous behavior run')
    out.mkdir()
    def run(argv,label):
        q=subprocess.run([str(x) for x in argv],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
        (out/(label+'.log')).write_bytes(q.stdout)
        if q.returncode:raise RuntimeError(label+' failed')
        return q.stdout.decode('utf-8','replace')
    flags=[ZIG,'c++','-std=c++14','-O1','-Wall','-Wextra','-Werror']
    for label,inc in (('baseline',WS/'CANDIDATE_GCC75_R2_20261029/candidate/bridge'),('fixed',ROOT/'candidate/bridge')):
        exe=out/(label+'.exe');run(flags+['-I'+str(inc),ROOT/'tests/behavior_probe.cpp','-o',exe],label+'_compile')
        result=run([exe],label+'_probe');assert ('would_request_35g=1' if label=='baseline' else 'would_request_35g=0') in result
    exe=out/'behavior.exe';run(flags+['-I'+str(ROOT/'candidate/bridge'),ROOT/'tests/behavior_hardening.cpp','-o',exe],'behavior_compile')
    text=run([exe],'behavior_tests')
    data={'checks':int(re.search(r'BEHAVIOR_HARDENING_PASS checks=(\d+)',text).group(1)),'source':'SIMULATED','owner_model':'BLOCKED','physical_pass':False}
    (out/'result.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))
if __name__=='__main__':main()
