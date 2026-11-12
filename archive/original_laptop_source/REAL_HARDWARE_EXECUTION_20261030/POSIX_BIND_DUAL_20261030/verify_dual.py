"""New dual router/shared-driver regressions only; no old30-case suite rerun."""
from datetime import datetime,timezone
import argparse
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--label');a=p.parse_args()
if a.label and not a.label.replace('_','').isalnum():p.error('NEW label')
out=ROOT/('dual_tests_'+a.label if a.label else 'dual_tests');out.mkdir()
records=[]


def run(args,label):
    q=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    (out/(label+'.log')).write_bytes(q.stdout);records.append(dict(command=[str(x) for x in args],timestamp_utc=datetime.now(timezone.utc).isoformat(),exit_code=q.returncode,log=label+'.log'))
    if q.returncode:raise RuntimeError(label+' failed')


run([ROOT.parents[1]/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++17','-O1','-Wall','-Wextra','-Werror',
    '-I'+str(ROOT/'firmware/test/arduino_stub'),'-I'+str(ROOT/'firmware/include'),ROOT/'tests/dual_loop.cpp','-o',out/'dual.exe'],'compile')
cases=('boot','manual_with_binary_hello','binary_cannot_arm','malformed_binary_manual_deadline','stop_latches_both_domains','bus_peer_cannot_detach_or_start','nonblocking_deadline','telemetry_identity_and_no_nvs')
for case in cases:
    run([out/'dual.exe',case,out/(case+'.json')],case)
    frame=json.loads((out/(case+'.json')).read_text())
    assert frame['mode']=='diag_dual_station' and frame['kit_firmware_id']=='FORCAT_DUAL_STATION_20261030_V1'
    assert frame['feed_link']['physical_enable'] is False and frame['feed_link']['closure_provider_available'] is False
    assert len((out/(case+'.json')).read_bytes())<=8192
result=dict(status='PASS_OFFLINE',new_dual_cases=len(cases),physical_pass=False,source='ACTUAL_DUAL_FIRMWARE_LOOP_MOCK_GPIO',commands=records)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
