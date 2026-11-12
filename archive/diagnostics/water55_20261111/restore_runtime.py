from pathlib import Path
import importlib.util,json,time,urllib.request,subprocess
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('flash_deployment',R/'deploy_firmware.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
before=json.loads((R/'preflight.json').read_text())['telemetry']['fc_live']
current=m.wait_status(lambda s:s['device']==m.UART)
fc=current['telemetry']['fc_live']
assert fc['pump_auto_enabled'] is False and fc['pump_auto_running'] is False
assert abs(fc['pump_on_cm']-5.7)<.001 and abs(fc['pump_off_cm']-5.5)<.001
assert not fc.get('inspect_required') and fc.get('meal_phase') not in ('CAPTURING','OBSERVING')
m.same_cal(before,fc)
if before.get('demo_exited') is False:
    m.queue('start\nmode\npump_status')
    stamp=time.monotonic()*1000
    current=m.wait_status(lambda s:s['updated_monotonic_ms']>stamp and s['telemetry']['fc_live'].get('demo_exited') is False)
fc=current['telemetry']['fc_live'];m.same_cal(before,fc)
assert fc['backup_enabled']==before['backup_enabled']
assert fc['pump_auto_enabled'] is False and fc['pump_auto_running'] is False
with urllib.request.urlopen('http://127.0.0.1:8000/api/water-control',timeout=5) as r:water=json.load(r)
assert water['fresh'] and water['policy_ready'] and water['enabled'] is False and water['running'] is False
units=['for-cat-api.service','for-cat-esp32-bridge.service','for-cat-ai.service']
for unit in units:subprocess.run(['systemctl','--user','is-active','--quiet',unit],check=True)
result={'normal_mode_restored':fc['demo_exited'] is False,'backup_enabled':fc['backup_enabled'],'calibration_preserved':True,'water':water,'pump_enable_commands_sent':False,'physical_flow_test_performed':False}
(R/'runtime_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
