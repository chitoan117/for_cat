"""Read-only post-flash validation. Never open serial or enable acquisition."""
import asyncio,datetime,hashlib,json,sqlite3,subprocess,time,urllib.request
from pathlib import Path

R=Path('/home/toan/for_cat');E=Path(EVIDENCE)
F=E/'manual_flash_20261027T035746784238Z'
O=E/('post_manual_flash_check_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));O.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=8) as response:return json.load(response)
def safe(state):
    assert state['data_source']=='REAL'
    for key in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution'):
        assert state['safety'][key] is False,(key,state['safety'])
    assert state['safety']['actuator_outputs_enabled']==0
def pid(unit):return int(subprocess.check_output(['systemctl','--user','show',unit,'-p','MainPID','--value']))
result={'status':'BLOCKED','evidence':str(O),'acquisition_commands_sent':False,'serial_opened':False}
try:
    receipt=json.loads((F/'receipt.json').read_text());manifest=json.loads((E/'release_manifest.json').read_text())
    assert receipt['status']=='RUNTIME_PASS' and receipt['nvs_unchanged'] is True
    assert len(receipt['writes'])==1 and receipt['writes'][0]['offset']=='0x10000'
    assert receipt['writes'][0]['image_sha256']==manifest['firmware']['firmware.bin']
    assert len(receipt['commands'])==7 and all(c['exit']==0 for c in receipt['commands'])
    assert len((F/'nvs_before.bin').read_bytes())==0x5000
    assert sha(F/'nvs_before.bin')==sha(F/'nvs_after.bin')==receipt['nvs_sha256']
    assert sha(E/'host_release/firmware/firmware.bin')==manifest['firmware']['firmware.bin']
    services={u:pid(u) for u in ('for-cat-api','for-cat-esp32-bridge','for-cat-ai')}
    assert all(value>0 for value in services.values())
    owner={}
    for device in ('/dev/ttyACM0','/dev/video0'):
        p=subprocess.run(['fuser',device],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        owner[device]=[int(v) for v in p.stdout.split()];assert len(owner[device])==1
    assert owner['/dev/ttyACM0']==[services['for-cat-esp32-bridge']]
    detector=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            command=(p/'cmdline').read_bytes().split(b'\0')
            if command[0]==str(R/'jetson/ai/cat_dog_trt').encode():detector.append(int(p.name))
        except (OSError,IndexError):pass
    assert detector==owner['/dev/video0'] and len(detector)==1
    samples=[]
    expected={'HC_SR04_1':(12,13,'CAT_APPROACH'),'JSN_SR04T_1':(14,15,'WATER_LEVEL'),'HC_SR04_2':(16,17,'TBD'),'JSN_SR04T_2':(18,10,'TBD')}
    for i in range(8):
        state=get('/api/status');safe(state)
        assert state['esp32']['connected'] is True
        assert state['ai']['health']=='ONLINE' and state['ai']['classification'] in ('CAT','DOG','NONE')
        assert set(state['ultrasonic'])==set(expected)
        for key,(trig,echo,role) in expected.items():
            s=state['ultrasonic'][key]
            assert (s['trigger_gpio'],s['echo_gpio'],s['role'])==(trig,echo,role)
            assert s['firmware_supported'] is True and s['wired'] is True and s['configured'] is True
            assert s['enabled'] is False and s['state']=='DISABLED' and s['valid'] is False
            assert s['distance_cm'] is None and s['timeout'] is False and s['stale'] is False
        assert state['weight']['grams'] is None and state['weight']['calibration_state']=='NOT_CALIBRATED'
        samples.append(state)
        if i<7:time.sleep(1.2)
    (O/'rest_samples.json').write_text(json.dumps(samples,indent=2))
    bridge=get('/api/v1/esp32/status');worker=get('/api/meal-plans/worker')['worker'];hx=get('/api/hx711/status');cal=get('/api/hx711/calibration')
    assert bridge['telemetry']['ultrasonic_schema_version']==1 and bridge['serial_tx_enabled'] is False
    assert bridge['unsafe_telemetry_latched'] is False
    assert worker['enabled'] is True and worker['running'] is True and worker['mode']=='DRY_RUN_ONLY'
    assert worker['timezone']=='Asia/Ho_Chi_Minh' and worker['last_error'] is None
    assert worker['actuator_execution'] is False and worker['actual_dispensed_grams'] is None
    assert hx['actual_dispensed_grams'] is None and cal['active'] is None
    async def frames():
        import websockets
        async with websockets.connect('ws://127.0.0.1:8000/api/ws/state',open_timeout=8,max_size=131072) as ws:
            return [json.loads(await asyncio.wait_for(ws.recv(),8)) for _ in range(3)]
    ws=asyncio.run(frames())
    for state in ws:
        safe(state);assert len(state['ultrasonic'])==4 and all(s['state']=='DISABLED' for s in state['ultrasonic'].values())
    (O/'ws_frames.json').write_text(json.dumps(ws,indent=2))
    pre=json.loads((E/'preflight_summary.json').read_text())
    assert sha(R/'.git/index')==pre['index_sha256']
    for name,meta in pre['ai_metadata'].items():assert sha(R/name)==meta['sha256']
    with sqlite3.connect('file:'+pre['database']+'?mode=ro',uri=True) as db:
        counts={name:db.execute(sql).fetchone()[0] for name,sql in {'feed_requests':'SELECT COUNT(*) FROM feed_requests','feeding_records':"SELECT COUNT(*) FROM typed_records WHERE kind='feeding'",'feed_events':"SELECT COUNT(*) FROM events WHERE kind='FEED'"}.items()}
    assert counts==pre['baseline_feed_counts']
    for name,value in {'bridge':bridge,'worker':worker,'hx':hx,'calibration':cal}.items():(O/(name+'.json')).write_text(json.dumps(value,indent=2))
    service_log=subprocess.run(['systemctl','--user','status','for-cat-api','for-cat-esp32-bridge','for-cat-ai','--no-pager','-l'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);assert service_log.returncode==0
    (O/'services.log').write_bytes(service_log.stdout)
    first,last=samples[0]['esp32']['counters'],samples[-1]['esp32']['counters']
    delta={key:last[key]-first[key] for key in ('valid_reports','parse_errors','oversized_lines','storage_errors')}
    assert delta['valid_reports']>0 and all(delta[k]==0 for k in ('parse_errors','oversized_lines','storage_errors'))
    result.update(status='RUNTIME_PASS',flash_receipt=str(F/'receipt.json'),app_verified=True,nvs_unchanged=True,
        services=services,owners=owner,ai='ONLINE_'+samples[-1]['ai']['classification'],ai_unchanged=True,index_preserved=True,
        safety=samples[-1]['safety'],actual_dispensed_grams=None,ultrasonic=samples[-1]['ultrasonic'],
        hx711={'raw_available':samples[-1]['weight']['raw_available'],'raw_counts':samples[-1]['weight']['raw_counts'],'grams':None,'calibration_state':'NOT_CALIBRATED'},
        worker={'enabled':worker['enabled'],'running':worker['running'],'mode':worker['mode'],'last_error':worker['last_error']},
        rest_samples=len(samples),ws_frames=len(ws),counter_delta=delta,feed_counts=counts,physical='NOT_TESTED',
        next_user_action='Place a flat target at 40 cm in front of HC-SR04 #1 only; keep actuator power disconnected')
except Exception as error:
    result['error']=str(error);raise
finally:
    (O/'summary.json').write_text(json.dumps(result,indent=2))
    (O/'manifest_sha256.json').write_text(json.dumps({p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='manifest_sha256.json'},indent=2))
    print(json.dumps(result,indent=2))
