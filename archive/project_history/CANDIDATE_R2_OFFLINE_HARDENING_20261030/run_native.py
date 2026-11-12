import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;WS=ROOT.parent
ZIG=WS/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    out=ROOT/'evidence/native_core'
    if out.exists() and not args.resume:raise ValueError('preserve native_core; use --resume only for unfinished stages')
    out.mkdir(exist_ok=args.resume)
    common=[ZIG,'c++','-std=c++14','-O1','-Wall','-Wextra','-Werror']
    def run(argv,name):
        q=subprocess.run([str(x) for x in argv],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        log=out/(name+'.log');n=2
        while log.exists():log=out/(name+'_attempt_'+str(n)+'.log');n+=1
        log.write_bytes(q.stdout)
        if q.returncode:raise RuntimeError(name+' failed; see '+str(out))
        return q.stdout.decode('utf-8','replace')
    if args.resume:mass=(out/'mass_tests.log').read_text()
    else:
        run(common+['-I'+str(ROOT/'candidate/firmware/include'),ROOT/'tests/mass_policy.cpp','-o',out/'mass.exe'],'mass_compile')
        mass=run([out/'mass.exe'],'mass_tests')
    rows=[json.loads(s[len('MASS_RESULT '):]) for s in mass.splitlines() if s.startswith('MASS_RESULT ')]
    if not (out/'mass_outcomes.json').exists():(out/'mass_outcomes.json').write_text(json.dumps(rows,indent=2)+'\n')
    for label,include in (() if args.resume else (('baseline',WS/'CANDIDATE_GCC75_R2_20261029/candidate/bridge'),('fixed',ROOT/'candidate/bridge'))):
        run(common+['-I'+str(include),ROOT/'tests/session_probe.cpp','-o',out/(label+'_session.exe')],label+'_session_compile')
        text=run([out/(label+'_session.exe')],label+'_session_probe')
        assert ('ESP32_CONNECTED' if label=='baseline' else 'ESP32_BAD_TELEMETRY') in text
    run(common+['-I'+str(ROOT/'candidate/bridge'),ROOT/'tests/session_audit.cpp','-o',out/'session.exe'],'session_compile')
    session=run([out/'session.exe'],'session_tests')
    lib=WS/'HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install'
    run(common+['-I'+str(ROOT/'candidate/bridge'),'-I'+str(lib/'include'),ROOT/'tests/stream_bridge.cpp',lib/'lib/libjson-c.a','-ladvapi32','-o',out/'stream.exe'],'stream_compile')
    stream=run([out/'stream.exe',ROOT/'fixtures/transport_script.json'],'stream_tests')
    records=[json.loads(s) for s in stream.splitlines()]
    (out/'stream_records.json').write_text(json.dumps(records,indent=2)+'\n')
    m=re.search(r'MASS_POLICY_PASS cases=(\d+) checks=(\d+)',mass)
    result={'mass_cases':int(m.group(1)),'mass_checks':int(m.group(2)),
        'session_checks':int(re.search(r'HARDENING_SESSION_PASS checks=(\d+)',session).group(1)),
        'stream_records':len(records),'scope':'WINDOWS_FILE_SIMULATION_ONLY','ARM64':'NOT_RUN','APP_FLASH':'NO_GO'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
