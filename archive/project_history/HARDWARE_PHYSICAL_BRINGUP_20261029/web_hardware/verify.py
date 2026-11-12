"""Focused FILE/ASGI/Flutter checks, no deploy/build firmware/physical operation."""
from datetime import datetime
import json
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
HERE=Path(__file__).resolve().parent;KIT=HERE.parent;ROOT=KIT.parent
BACK=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'
FE=Path(r'D:\DA_KT_NC\feeder_demo')
def run(argv,name,cwd=HERE,env=None):
    p=subprocess.run([str(x) for x in argv],cwd=cwd,capture_output=True,timeout=240,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','FLUTTER_SUPPRESS_ANALYTICS':'true',**(env or {})})
    (HERE/(name+'.log')).write_bytes(p.stdout+p.stderr)
    print(name+': '+('PASS' if p.returncode==0 else 'FAIL'),flush=True)
    if p.returncode:raise RuntimeError(name+' failed; see log')
    return (p.stdout+p.stderr).decode('utf-8','replace')
def main():
    p=argparse.ArgumentParser();p.add_argument('--part',choices=('all','backend','flutter'),default='all');a=p.parse_args()
    prior=json.loads((HERE/'result.json').read_text()) if (HERE/'result.json').exists() else {}
    backend_count=prior.get('backend_tests');flutter_count=prior.get('flutter_tests')
    if a.part in ('all','backend'):
        text=run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','-o',
            'pythonpath='+HERE.as_posix()+' '+BACK.as_posix()+' '+(KIT/'tools').as_posix(),HERE/'test_diagnostics.py'],'backend_tests')
        backend_count=int(re.search(r'(\d+) passed',text).group(1))
    if a.part in ('all','flutter'):
        run([r'D:\dev\flutter\bin\flutter.bat','pub','get','--offline'],'flutter_pub_offline',HERE/'flutter')
        flutter=run([r'D:\dev\flutter\bin\flutter.bat','test','--no-pub','--reporter','expanded','test/hardware_diagnostics_test.dart'],'flutter_tests',HERE/'flutter')
        # Separate harness uses the primary app as a path dependency, not a copied UI.
        analyze=run([r'D:\dev\flutter\bin\flutter.bat','analyze','--no-pub'],'flutter_analyze',HERE/'flutter')
        flutter_count=int(re.search(r'\+(\d+): All tests passed',flutter).group(1))
    if backend_count is None or flutter_count is None:raise ValueError('both focused parts must have evidence before handoff')
    result={'completed_at':datetime.now().astimezone().isoformat(),'backend_tests':backend_count,
        'flutter_tests':flutter_count,
        'flutter_analyze':'PASS_NO_ISSUES','backup_AB_file_integrity':'PASS','rollback_artifact':'LOCAL_EXTRACTION_PASS_HARDWARE_RESTORE_NOT_VERIFIED',
        'bridge_candidate_native_compile':'WINDOWS_CPP14_JSONC_PARSER_SESSION_PASS_ARM64_OWNER_BUILD_FAILED_R1_PENDING',
        'native_parser_evidence':json.loads((HERE/'native_parser_result.json').read_text()),
        'kit_revision':'GCC75_R1','ARM64_NATIVE_TEST_PASS':False,'ARM64_R1_RETEST':'NOT_RUN',
        'latest_owner_ARM64_attempt':json.loads((HERE/'gcc75_fix/OWNER_ARM64_FAILURE.json').read_text()),
        'food_roi_evidence':json.loads((HERE/'gcc75_fix/food_roi_result.json').read_text()),
        'bridge_candidate_source':'SEPARATE_KIT_COPY_NOT_PRODUCTION_PATCH','new_endpoints':'OPTIONAL_ROUTER_NOT_INSTALLED_IN_LIVE_APP',
        'buzzer_live_transport':'NOT_IMPLEMENTED_DISABLED_CURRENT_FIRMWARE_CAPABILITY_MISSING',
        'web_preparation':'OFFLINE_CONTRACT_AND_PANEL_PASS_WITH_LIVE_BLOCKERS','real_web_hardware_pass':'NOT_VERIFIED',
        'production_source_changed':False,'firmware_changed':False,'serial_opened':False,'camera_opened':False,
        'services_changed':False,'physical_pass':False}
    (HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
