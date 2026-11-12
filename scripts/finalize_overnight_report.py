"""Final non-actuating audit. Captures exact files/Git/evidence/current availability."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import urllib.request

ROOT=Path('/home/toan/for_cat');E=ROOT/'evidence/overnight_integration_20261023'
def command(args):
    p=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
    return {'command':args,'exit_code':p.returncode,'output':p.stdout.decode('utf-8','replace')}
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
audit=json.loads((E/'audit.json').read_text())
files=json.loads((E/'session_files.json').read_text())
for name,expected in files.items():assert digest(ROOT/name)==expected,name
status=command(['git','status','--short'])
staged=command(['git','diff','--cached','--binary'])
assert staged['output']==(E/'git_staged.txt').read_text(),'original staged content changed'
protected={name:digest(ROOT/name) for name in audit['protected_hashes']}
assert protected==audit['protected_hashes'],'protected AI files changed'
original_doc=(E/'originals/docs/CURRENT_PROJECT_STATE.md').read_text()
assert original_doc.split('\n',1)[1] in (ROOT/'docs/CURRENT_PROJECT_STATE.md').read_text()
for name in command(['git','diff','--cached','--name-only'])['output'].splitlines():
    if name=='docs/CURRENT_PROJECT_STATE.md':continue
    index=subprocess.check_output(['git','show',':'+name],cwd=ROOT)
    assert (ROOT/name).read_bytes()==index,'staged user source overwritten: '+name
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:state=json.load(response)
assert state['data_source']=='REAL' and state['safety']['actuator_execution'] is False
checks=sorted(E.glob('checks_*'))[-1];regressions=sorted(E.glob('regressions_*'))[-1]
positive=json.loads((E/'vertical_slice/evidence.json').read_text())
later=json.loads((E/'availability_recovery/evidence.json').read_text())
tests={
    'backend_all':re.search(r'(\d+) passed',(regressions/'backend_all.log').read_text()).group(0),
    'new_subset':re.search(r'(\d+) passed',(checks/'new_pty_api_tests.log').read_text()).group(0),
    'native_policy':(checks/'native_policy_ubsan.log').read_text().strip(),
    'decision':(checks/'decision_ubsan.log').read_text().strip(),
    'dispense':(regressions/'dispense_policy_ubsan.log').read_text().strip(),
    'checks_directory':str(checks),'regressions_directory':str(regressions)}
with sqlite3.connect(str(ROOT/'jetson/data/events.db')) as db:
    database={'user_version':db.execute('PRAGMA user_version').fetchone()[0],
              'quick_check':db.execute('PRAGMA quick_check').fetchone()[0],
              'counts':{name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
                        for name in ['events','typed_records','feed_requests','esp32_events','feed_dry_run_requests','ai_latest','esp32_latest']}}
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':command(['git','rev-parse','HEAD'])['output'].strip(),
        'initial_git_status':(E/'git_status.txt').read_text(),'final_git_status':status['output'],
        'git_diffstat':command(['git','diff','--stat'])['output'],
        'git_diff_check':command(['git','diff','--check']),
        'original_staged_diff_unchanged':True,
        'original_git_index_bytes_unchanged':digest(ROOT/'.git/index')==audit['git_index_sha256'],
        'protected_ai_hashes':protected,'ai_hashes_unchanged':True,
        'source_files_changed':sorted(files),'session_source_line_count':sum(len((ROOT/name).read_bytes().splitlines()) for name in files),
        'services':command(['systemctl','--user','show','for-cat-esp32-bridge.service','for-cat-api.service','for-cat-ai.service','-p','ActiveState','-p','SubState','-p','NRestarts','-p','UnitFileState']),
        'usb':command(['lsusb']),'serial_owner':command(['fuser','/dev/ttyACM0']),
        'current_system_state':state,'database':database,'tests':tests,
        'positive_vertical_slice_proof':{view:{k:v for k,v in details.items() if k not in ('first_rendered_state','later_without_refresh')}
                                         for view,details in positive['browser'].items()},
        'latest_real_availability_views':{view:{k:v for k,v in details.items() if k not in ('first_rendered_state','later_without_refresh')}
                                         for view,details in later['browser'].items()},
        'real_receiver_stale_recovery':later.get('real_link_stale_test',{}),
        'physical_usb_unplug_test_performed_by_agent':False,'controlled_target_motion_performed_by_agent':False,
        'firmware_flash_performed':False,'actuator_commands_sent':False,
        'serial_commands_sent':['echo-approach-3v3 CONFIRM','echo-water-3v3 CONFIRM'],
        'physical_35g_dispense':False,'new_button_physical_pass_awarded':False,
        'remaining':['camera USB currently absent/error -71: user cable/power/replug check',
                     'OLED live FAULT regression after board reboot: user inspection',
                     'Echo confirmations cleared by reboot: operator re-enable after divider review',
                     'GPIO21 press/hold physical evidence still needed',
                     'JSN operational geometry/no-Echo and final near thresholds not calibrated',
                     'HX gram calibration deferred; all physical dispense/pump blocked',
                     'Meal Plan persistent CRUD/autonomous scheduling worker still future; due-instance/time adapter only',
                     'production eating weight-trend adapter/physical validation still blocked on calibration',
                     'real Jetson staged ESP32 source remains legacy/conflicting; source sync required before future flash']}
(E/'FINAL_REPORT.json').write_text(json.dumps(report,indent=2))
markdown=['# ForCat overnight integration — final evidence', '', 'Generated '+report['utc'],
          '', '## Current live state', '```json',json.dumps(state,indent=2),'```',
          '', '## Tests/builds', '```json',json.dumps(tests,indent=2),'```',
          '', '## Exact source files changed', '```',*report['source_files_changed'],'```',
          '', '## git status --short', '```',report['final_git_status'],'```',
          '', '## Tracked diff summary (new files listed above)', '```',report['git_diffstat'],'```',
          '', '## Safety / preservation',
          'No ESP32 flash/erase/NVS write, no servo/pump action. Only two fixed Echo sensor acknowledgements.',
          'Original staged diff, other staged working files and protected AI source/binary/engine verified unchanged.',
          'New services started read-only/dry-run, not enabled for automatic boot.',
          '', '## Remaining / physical actions', *['- '+item for item in report['remaining']],
          '', 'Full machine-readable evidence: FINAL_REPORT.json; positive live proof: vertical_slice/;',
          'later availability and receiver-only pause/recovery: availability_recovery/.']
(E/'FINAL_REPORT.md').write_text('\n'.join(markdown)+'\n')
print(json.dumps({key:report[key] for key in ['utc','head','original_staged_diff_unchanged','original_git_index_bytes_unchanged',
                                            'ai_hashes_unchanged','source_files_changed','session_source_line_count','tests','database',
                                            'positive_vertical_slice_proof','latest_real_availability_views','final_git_status','git_diffstat']},indent=2))
