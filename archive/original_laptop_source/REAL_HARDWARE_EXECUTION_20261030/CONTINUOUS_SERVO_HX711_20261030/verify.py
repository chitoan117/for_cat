"""Compile/run ONLY new continuous-servo logic. No firmware image/device/old suite."""
import argparse
from datetime import datetime,timezone
import hashlib,json,re,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent;WS=ROOT.parents[1]
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
if not a.label.replace('_','').isalnum():p.error('NEW label')
out=ROOT/('tests_'+a.label);out.mkdir()
cases=('config_and_arm_no_motion','supervised_aim35_actual38_unconfirmed','measured_close_lead_not_lower_band',
 'persistent30_no_early_success_or_topup','automatic_needs_real_feedback_contract','automatic_close_timeout_not_closed',
 'overshoot_all_motion_and_settle_states','calibration_stale_conflict_and_clock_fail','stop_no_reverse_and_no_deadline_extension',
 'fault_close_optin_bounded_never_complete','link_loss_neutral_not_auto_rearm','idempotency_journal_fail_and_pending_reboot',
 'frozen_samples_not_stable_window','late_attach_or_open_stop_cannot_resurrect','late_journal_clear_stop_preserves_pending',
 'raw_pwm_failure_no_false_success','hx_adapter_uses_passed_reading_no_display_or_refit','below30_measured_fault_not_reopened',
 'inclusive_band_and_no_epsilon_widening','expired_arm_lease_and_reentrant_start_journal','closed_feedback_loss_after_neutral_blocks_complete')
result=dict(status='FAIL',source='NEW_CONTINUOUS_LOGIC_MOCK_IO',physical_pass=False,commands=[],new_cases=[])


def run(args,label):
    q=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (out/(label+'.log')).write_bytes(q.stdout)
    result['commands'].append(dict(command=[str(x) for x in args],timestamp_utc=datetime.now(timezone.utc).isoformat(),exit_code=q.returncode,log=label+'.log'))
    if q.returncode:raise RuntimeError(label+' failed; preserve output')
    return q.stdout.decode('utf-8','replace')


try:
    run([WS/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++14','-O1','-Wall','-Wextra','-Werror',
        '-I'+str(ROOT/'include'),ROOT/'tests/continuous_test.cpp','-o',out/'continuous.exe'],'compile')
    for case in cases:
        text=run([out/'continuous.exe',case],case);assert 'CONTINUOUS_PASS' in text
        result['new_cases'].append(dict(name=case,checks=int(re.search(r'checks=(\d+)',text).group(1))))
    baseline=json.loads((ROOT/'BASELINE.json').read_text())
    for rel,meta in baseline['files'].items():
        assert hashlib.sha256((ROOT/'include'/rel).read_bytes()).hexdigest()==meta['sha256'],rel
        assert hashlib.sha256(Path(meta['source']).read_bytes()).hexdigest()==meta['sha256'],meta['source']
    result.update(status='PASS_OFFLINE',new_case_count=len(cases),hx711_driver_unchanged=True,
        copied_headers_unchanged=len(baseline['files']),old_suites_rerun=False,firmware_built=False,flashed=False,
        source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                       for d in ('include','tests') for p in (ROOT/d).rglob('*') if p.is_file()})
except Exception as e:result['error']=str(e);raise
finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','new_case_count','hx711_driver_unchanged','copied_headers_unchanged','firmware_built','physical_pass')},indent=2))
