"""RC v2 focused packaging/deployment qualification. All service tests use fakes."""
import ast
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
HERE=Path(__file__).resolve().parent;SESSION=HERE.parent;ROOT=SESSION.parent
RELEASE=SESSION/'release_candidate_v2'
sys.path.insert(0,str(HERE/'tools'))
from integrity import sha,verify,write_new
def run(args,name,env=None):
    p=subprocess.run([str(x) for x in args],cwd=HERE,capture_output=True,timeout=240,env=env)
    (HERE/(name+'.log')).write_bytes(p.stdout+p.stderr)
    print(name+': '+('PASS' if p.returncode==0 else 'FAIL'),flush=True)
    if p.returncode:raise RuntimeError(name+' failed; see log')
    return p.stdout.decode('utf-8','replace')
def main():
    manifest=verify(RELEASE)
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(RELEASE/'payload/jetson')}
    text=run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','-o',
              'pythonpath='+str(HERE/'tools')+' '+str(RELEASE/'payload/jetson'),HERE/'test_release.py',HERE/'test_packaged_python.py'],
              'focused_tests',env)
    count=int(re.search(r'(\d+) passed',text).group(1))
    native=HERE/'native';native.mkdir(exist_ok=True);exe=native/'test_packaged.exe'
    run([ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++14','-O1','-pthread',
        '-Wall','-Wextra','-Werror','-I'+str(RELEASE/'payload/jetson/device'),'-I'+str(RELEASE/'ai_reference'),
        '-I'+str(RELEASE/'firmware_include'),HERE/'test_packaged.cpp','-o',exe],'packaged_cxx14_compile')
    native_output=run([exe],'packaged_cxx14_test')
    for p in (RELEASE/'tools').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),str(p))
    verify(RELEASE)
    result={'phase':5,'completed_at':datetime.now().astimezone().isoformat(),'JETSON_PRODUCTION_STAGING_READY':'YES',
        'release':str(RELEASE),'release_file_count':len(manifest['files']),'manifest_sha256':sha(RELEASE/'manifest.json'),
        'SHA256SUMS_sha256':sha(RELEASE/'SHA256SUMS'),'focused_tests_passed':count,'packaged_cxx14':native_output.strip(),
        'python_package_imports':'PASS_FROM_IMMUTABLE_BUNDLE','deployment_operations':'FAKE_SERVICES_AND_TEMP_DB_ONLY',
        'default_dry_run':'PASS_ALL_WRITE_ACTIONS','phase4_source_and_web_hashes':'MATCH',
        'production_runtime_changed':False,'production_db_changed':False,'ssh_used':False,'camera_opened':False,'serial_opened':False,
        'servo':'LOCKED','pump':'LOCKED','physical_pass':False,
        'ARM64_TENSORRT_BUILD_PASS':'NOT_VERIFIED','JETSON_REAL_CAMERA_PASS':'NOT_VERIFIED','TAILSCALE_REMOTE_PASS':'NOT_VERIFIED',
        'ESP32_TELEMETRY_PASS':'NOT_VERIFIED','HX711_PHYSICAL_PASS':'NOT_VERIFIED','ACTUATOR_PHYSICAL_PASS':'NOT_VERIFIED',
        'known_blocker':'Actual HX711_REFERENCE firmware is incompatible with diag_current_hardware bridge; valid telemetry=0; parser and firmware unchanged',
        'evidence_sha256':{name:sha(HERE/name) for name in ('focused_tests.log','packaged_cxx14_compile.log','packaged_cxx14_test.log')}}
    (HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('completed_at','release_file_count','focused_tests_passed','JETSON_PRODUCTION_STAGING_READY','manifest_sha256')}))
if __name__=='__main__':main()
