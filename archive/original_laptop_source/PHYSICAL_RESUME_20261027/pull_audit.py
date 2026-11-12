"""Download already backed-up read-only source/metadata for dedicated local review."""
import base64,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));from ssh_run import SSH,OUT,HOST
summary=json.loads((OUT/'preflight_backup_result.json').read_text());E=summary['evidence']
names=['esp32/platformio.ini','esp32/include/board_config.h','esp32/include/pins.h','esp32/include/m4/candidate_sensor_pins.h','esp32/include/m4/diagnostic_config.h','esp32/src/diagnostics.cpp','jetson/app/main.py','jetson/app/frontend_assets.py','jetson/app/meal_plans.py','jetson/app/scheduled_worker.py','jetson/tools/hx711_calibration.py','jetson/tests/test_esp32_bridge.py','scripts/run_integration_regressions.py','scripts/verify_dispense_preparation.sh','scripts/enable_verified_sensor_acquisition.py','config/hardware_current.json','docs/CURRENT_PROJECT_STATE.md']
code='from pathlib import Path;import json,base64;R=Path("/home/toan/for_cat");names='+repr(names)+';print(json.dumps({n:base64.b64encode((R/n).read_bytes()).decode() for n in names if (R/n).is_file()}))'
p=subprocess.run(SSH+['/home/toan/for_cat/.venv/jetson-integration/bin/python -'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
assert p.returncode==0,p.stderr.decode()
for name,data in json.loads(p.stdout).items():
 target=OUT/'remote_audit'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(data))
for name in ('audit/git_diff.log','audit/git_staged_diff.log','audit/before_bridge.json','audit/before_hx_calibration.json','preflight_summary.json','manifest_phase0_sha256.json'):
 target=OUT/'remote_evidence'/name;target.parent.mkdir(parents=True,exist_ok=True)
 p=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson','toan@'+HOST+':'+E+'/'+name,str(target)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
 assert p.returncode==0,p.stderr.decode()
print('Read-only source/evidence copied to '+str(OUT/'remote_audit'))
