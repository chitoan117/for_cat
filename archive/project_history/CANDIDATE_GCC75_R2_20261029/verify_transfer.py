"""Python3.6+ R2 source delta verifier. Read-only; no build/service/device API."""
from __future__ import print_function
import argparse
import hashlib
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parent
REQUIRED=('native_arm64_r2.py','native_checks.py','verify_transfer.py',
    'candidate/bridge/telemetry.h','candidate/bridge/ultrasonic_telemetry.h',
    'candidate/bridge/diagnostic_session.h','candidate/bridge/food_roi.h',
    'candidate/bridge/feed_policy.h','candidate/bridge/decision_logic.h',
    'candidate/bridge/approach_fusion.h','candidate/bridge/roi_species.h','candidate/bridge/owner_behavior.h',
    'candidate/bridge/parser_replay.cpp','candidate/bridge/test_session.cpp',
    'candidate/bridge/test_food_roi.cpp','candidate/bridge/esp32_bridge.cpp',
    'candidate/firmware/include/m4/dispense_bench.h','candidate/firmware/include/m4/servo_bench.h',
    'candidate/protocol/dog_warning_protocol.h','tests/logic_tests.cpp','tests/timeline_probe.cpp',
    'tests/dispense_regressions.cpp','fixtures/r1_quad_reports.log','fixtures/synthetic_wire.json','fixtures/synthetic_wire.jsonl')
def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('duplicate manifest key')
        d[k]=v
    return d
def verify(root=ROOT,expected=None,required=REQUIRED):
    root=Path(root)
    for name in ('TRANSFER_MANIFEST.json','TRANSFER_MANIFEST.sha256'):
        if (root/name).is_symlink() or not (root/name).is_file():raise ValueError('regular manifest/digest files required')
    raw=(root/'TRANSFER_MANIFEST.json').read_bytes();actual=hashlib.sha256(raw).hexdigest()
    recorded=(root/'TRANSFER_MANIFEST.sha256').read_text(encoding='ascii').strip()
    if not re.match(r'^[0-9a-f]{64}$',recorded) or actual!=recorded:raise ValueError('manifest digest mismatch')
    if expected is not None and actual!=expected.lower():raise ValueError('external trusted manifest digest mismatch')
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=unique)
    if value.get('revision')!='GCC75_R2' or value.get('kind')!='FORCAT_R2_SOURCE_DELTA':raise ValueError('wrong package kind/revision')
    if not isinstance(value.get('files'),dict) or not set(required)<=set(value['files']):raise ValueError('required executable/test inputs absent from manifest')
    for name,meta in value['files'].items():
        parts=name.split('/')
        if name.startswith('/') or ':' in name or '\\' in name or any(x in ('','.','..') for x in parts):raise ValueError('unsafe manifest path')
        if any(root.joinpath(*parts[:n]).is_symlink() for n in range(1,len(parts)+1)):raise ValueError('symlink source rejected')
        p=root/name
        if not p.is_file() or p.stat().st_size!=meta['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('file mismatch: '+name)
    return {'transfer_integrity':'PASS','revision':'GCC75_R2','files_checked':len(value['files']),
        'manifest_sha256':actual,'external_digest_checked':expected is not None,
        'ARM64_NATIVE_TEST_PASS':'NOT_RUN_BY_VERIFIER','APP_FLASH':'NO_GO','serial_opened':False,'services_changed':False}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--expected-sha256');a=p.parse_args()
    print(json.dumps(verify(expected=a.expected_sha256),indent=2))
if __name__=='__main__':main()
