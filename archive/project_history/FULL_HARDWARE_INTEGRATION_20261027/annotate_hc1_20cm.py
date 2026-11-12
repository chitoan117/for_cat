import hashlib,json
from pathlib import Path
E=Path(EVIDENCE);O=E/'hc1_target_20cm_passive_20261027T045529082502Z'
states=json.loads((O/'rest_full_states.json').read_text());summary=json.loads((O/'summary.json').read_text())
a=states[0]['esp32']['counters'];b=states[-1]['esp32']['counters']
delta={k:b[k]-a[k] for k in ('valid_reports','parse_errors','oversized_lines','device_reboots','storage_errors')}
assert summary['metrics']['valid_samples']==24 and summary['comparison']['direction_correct']
assert all(delta[k]==0 for k in ('parse_errors','oversized_lines','device_reboots','storage_errors'))
handoff=json.loads((E/'hc1_enable_for_20cm_20261027T045519492556Z/summary.json').read_text())
note={'near_capture_status':'RUNTIME_PASS','capture_counter_delta':delta,
 'reset_observed_during_serial_handoff':handoff['raw_uptime_ms']<handoff['before_uptime_ms'],
 'reset_cause':'NOT_PROVEN; serial handoff coincides with uptime restart; do not infer power or component fault',
 'near_capture_itself_had_reboot':False,'physical_completion':'NOT_TESTED_PENDING_RETURN_TO_40CM',
 'next_single_action':'Move same flat target from nominal20cm back to nominal40cm, keep orientation; no other sensor enabled'}
(O/'analysis_note.json').write_text(json.dumps(note,indent=2));(O/'manifest_sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='manifest_sha256.json'},indent=2));print(json.dumps(note,indent=2))
