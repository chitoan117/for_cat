"""Offline gated APP-only argument generator; NEVER executes any device command.

Reuses existing bank/security/backup/rollback validator, then binds this exact NEW
image and unchanged partition table. No approval -> no executable flash arguments.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1] / 'HARDWARE_PHYSICAL_BRINGUP_20261029'
sys.path.insert(0, str(BASE / 'maintenance_readiness'))
import app_plan as prior

EXTRA_GATES = ('manual_station_image_and_protocol_reviewed',
               'no_production_bridge_during_manual_actuation',
               'exact_HX_coefficients_preserved_for_RAM_reimport_or_verified_compatible_NVS')


def plan(review=None, build_result=None):
    v = review or {}
    result = prior.plan(v)
    problems = list(result.get('blockers', []))
    for gate in EXTRA_GATES:
        if v.get('candidate_gates', {}).get(gate) is not True:
            problems.append(gate)
    if not build_result:
        problems.append('EXACT_CANDIDATE_BUILD_RESULT_REQUIRED')
    if problems:
        return {'mode': 'PLAN_ONLY', 'APP_FLASH': 'NO_GO', 'blockers': problems,
                'write_argv_available': False, 'device_commands_executed': False}
    bpath = Path(build_result)
    b = json.loads(bpath.read_text(encoding='utf-8'))
    image = Path(b['image'])
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    if b.get('build') != 'VERIFIED_PASS_BUILD_ONLY' or b.get('image_sha256') != digest or v.get('candidate_image_sha256') != digest:
        raise ValueError('review/build/image SHA binding mismatch')
    if b.get('image_bytes') != image.stat().st_size or not b.get('partition_table_unchanged'):
        raise ValueError('candidate image/layout mismatch')
    if b['partitions'] != json.loads((BASE / 'artifacts/diag_four_ultrasonic/layout.json').read_text())['partitions']:
        raise ValueError('candidate partition layout changed')
    if b.get('secure_version') != prior.descriptor_version(image) or b['secure_version'] != 0:
        raise ValueError('unreviewed secure-version branch')
    if b['build_app_offset'] != v['actual_running_offset'] or image.stat().st_size > b['application_partition']['size']:
        raise ValueError('actual running bank/size not compatible')
    if b['pump_off_level'] == -1:
        if v.get('candidate_gates', {}).get('inert_pump_load_power_physically_isolated') is not True:
            raise ValueError('INERT/high-Z is not measured OFF; isolate pump load')
    else:
        if v.get('candidate_gates', {}).get('pump_polarity_measurements_reviewed') is not True or v.get('pump_observation_sha256') != b['pump_observation_sha256']:
            raise ValueError('measured pump-polarity evidence not bound to this build')
    for name in ('write_argv', 'verify_argv'):
        result[name][-1] = str(image)
    result.update(candidate_image_sha256=digest, candidate_profile=b['profile'],
                  protocol='diag_manual_station V1; current production Bridge intentionally rejects',
                  build_result_sha256=hashlib.sha256(bpath.read_bytes()).hexdigest(),
                  APP_FLASH='REVIEWED_PLAN_ONLY_EXECUTION_REQUIRES_OWNER',
                  device_commands_executed=False)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review', type=Path)
    p.add_argument('--build-result', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    result = plan(json.loads(a.review.read_text()) if a.review else None, a.build_result)
    if a.output:
        with a.output.open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
