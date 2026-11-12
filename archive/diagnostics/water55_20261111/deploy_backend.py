from pathlib import Path
import hashlib,json,os,py_compile,shutil,sqlite3,subprocess,threading,time,urllib.request
import serial
R=Path(__file__).resolve().parent;ROOT=Path('/home/toan/for_cat/jetson')
files={'fc_live_bridge.py':ROOT/'tools/fc_live_bridge.py','main.py':ROOT/'app/main.py','water_control.py':ROOT/'app/water_control.py','water_routes.py':ROOT/'app/api/water_routes.py'}
plan=json.loads((R/'backend_plan.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,p in files.items():
    assert (sha(p) if p.exists() else None)==plan[n]['before'],'Changed live file: '+n
    assert sha(R/'backend'/n)==plan[n]['after']
    py_compile.compile(str(R/'backend'/n),doraise=True)
backup=R/'live_before';backup.mkdir(exist_ok=False)
for n,p in files.items():
    if p.exists():shutil.copy2(p,backup/n)
def service(action):subprocess.run(['systemctl','--user',action,'for-cat-api.service','for-cat-esp32-bridge.service'],check=True,timeout=20)
def snapshot():
    with sqlite3.connect(ROOT/'data/events.db',timeout=2) as db:return json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
before=snapshot();fc=before['telemetry']['fc_live']
assert 0<=time.monotonic()*1000-before['updated_monotonic_ms']<2500
assert fc['bench_state'] in ('READY','CAT FAULT*','MASS OK GATE?') and not fc.get('dog_running')
assert fc.get('meal_phase') not in ('CAPTURING','OBSERVING')
(R/'before_status.json').write_text(json.dumps(before,indent=2))
class Keepalive:
    def __enter__(self):
        self.stop=threading.Event();self.ser=serial.Serial('/dev/ttyTHS1',115200,timeout=.1,write_timeout=.5,rtscts=False,dsrdtr=False)
        self.ser.write(b'pump_auto off\npump_off\njetson_ping\n')
        def run():
            last=time.monotonic()
            while not self.stop.is_set():
                self.ser.read(4096)
                if time.monotonic()-last>=1:self.ser.write(b'jetson_ping\n');last=time.monotonic()
        self.thread=threading.Thread(target=run,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join(2);self.ser.close()
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=3) as r:return json.load(r)
service('stop')
try:
    with Keepalive():
        for n,p in files.items():p.write_bytes((R/'backend'/n).read_bytes())
    service('start')
    end=time.monotonic()+18
    while time.monotonic()<end:
        # If bridge startup fails, roll back before heartbeat-loss threshold.
        active=subprocess.run(['systemctl','--user','is-active','--quiet','for-cat-esp32-bridge.service']).returncode==0
        if not active:raise RuntimeError('New bridge is not active')
        try:
            status=get('/api/water-control')
            if status.get('fresh') and status.get('supported') and status.get('enabled') is False and status.get('running') is False:break
        except (OSError,ValueError):pass
        time.sleep(.4)
    else:raise RuntimeError('No fresh confirmed OFF water state')
    # End-to-end OFF only. Never acknowledge a water ENABLE in deployment.
    req=urllib.request.Request('http://127.0.0.1:8000/api/water-control',data=json.dumps({'request_id':'deployment_off_'+str(int(time.time())),'action':'DISABLE','confirmed':False}).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=3) as r:assert r.status==202
    end=time.monotonic()+8
    while time.monotonic()<end:
        status=get('/api/water-control')
        if (status.get('request') or {}).get('status')=='APPLIED' and status.get('enabled') is False:break
        time.sleep(.3)
    else:raise RuntimeError('OFF request not confirmed by device')
    after=snapshot();live=after['telemetry']['fc_live']
    for key in ('tare_counts','grams_per_count'):assert live[key]==fc[key],'Calibration changed'
    assert live.get('backup_enabled')==fc.get('backup_enabled'),'Backup setting changed'
    result={'deployed':True,'water_status':status,'calibration_unchanged':True,'firmware_not_flashed_by_backend_script':True,'backup_setting_unchanged':True,'physical_enable_commands_sent':False,'source_hashes':plan}
    (R/'backend_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
except BaseException:
    service('stop')
    with Keepalive():
        for n,p in files.items():
            if (backup/n).exists():p.write_bytes((backup/n).read_bytes())
            elif plan[n]['before'] is None:p.unlink(missing_ok=True)
    service('start');raise
