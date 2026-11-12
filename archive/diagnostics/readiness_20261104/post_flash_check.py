from pathlib import Path
import subprocess,time,sqlite3,json,urllib.request
r=Path(__file__).parent
cmd=Path('/tmp/for_cat_cmd.txt')
assert not cmd.exists(),'Existing command file; preserve and inspect before restarting'
subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True)
time.sleep(3)
# start only resumes the state machine/sensor polling; it does not move a motor.
assert not cmd.exists(),'A pending command appeared; leave it unchanged'
cmd.write_text('start\nmode\nhx_diag\nsensors\n')
samples=[]
for attempt in range(5):
    time.sleep(3)
    c=sqlite3.connect('file:/home/toan/for_cat/jetson/data/events.db?mode=ro',uri=True)
    row=c.execute('select body from esp32_latest where id=1').fetchone()
    c.close()
    d=json.loads(row[0]) if row else {}
    telemetry=d.get('telemetry',{})
    sample={'age_ms':int(time.monotonic()*1000)-d.get('updated_monotonic_ms',0),
            'frames_ok':d.get('counters',{}).get('frames_ok'),
            'hx':telemetry.get('sensors',{}).get('hx711'),
            'grams':telemetry.get('fc_live',{}).get('signed_g'),
            'bench_state':telemetry.get('fc_live',{}).get('bench_state')}
    samples.append(sample)
    print(json.dumps(sample),flush=True)
report={'serial_samples':samples,'bridge_active':subprocess.check_output(['systemctl','--user','is-active','for-cat-esp32-bridge.service'],text=True).strip(),
        'udev_ignore_rule_installed':Path('/etc/udev/rules.d/99-forcat-esp32.rules').exists(),
        'motor_movement_commands_sent':False}
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=10) as response:
    report['api_status']=json.load(response)
with urllib.request.urlopen('http://127.0.0.1:8000/app',timeout=10) as response:
    report['offline_app_http']=response.status
report['serial_readonly_verification_passed']=len(samples)>=3 and all(s['age_ms']<2500 for s in samples) and samples[-1]['frames_ok']>samples[0]['frames_ok']
(r/'post_flash_result.json').write_text(json.dumps(report,indent=2))
result_file=r/'firmware/flash_result.json'
flash=json.loads(result_file.read_text())
flash['bridge_left_stopped_for_pcb_work']=False
flash['bridge_restored']=report['bridge_active']=='active'
flash['normal_state_machine_resumed']=True
result_file.write_text(json.dumps(flash,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['api_status','serial_samples']},indent=2))
assert report['serial_readonly_verification_passed'],'Serial cache is stale or not updating'
