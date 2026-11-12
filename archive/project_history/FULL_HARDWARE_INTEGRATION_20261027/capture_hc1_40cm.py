"""Supervised HC1 only: bounded diagnostic handoff then passive REAL REST/WS sampling."""
import asyncio,datetime,hashlib,json,math,statistics,subprocess,termios,time,urllib.request
from pathlib import Path
import serial
from serial.tools import list_ports

R=Path('/home/toan/for_cat');E=Path(EVIDENCE)
O=E/('hc1_target_40cm_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));O.mkdir()
IDS={'HC_SR04_1','HC_SR04_2','JSN_SR04T_1','JSN_SR04T_2'};HC='HC_SR04_1'
COMMAND=b'ultra-select hc1 CONFIRM\n'
result={'status':'BLOCKED','evidence':str(O),'operator_declared_target_cm':40,
 'reference':'USER_PLACED_APPROXIMATE_FLAT_TARGET_NOT_CALIBRATION_CERTIFICATE',
 'actuator_commands_sent':False,'flash_performed':False,'commands':[],'physical_status':'NOT_TESTED'}
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=6) as r:return json.load(r)
def safe_api(state):
    assert state['data_source']=='REAL' and state['esp32']['connected'] is True
    assert state['safety']['actuator_outputs_enabled']==0
    for k in ('auto_feed','auto_water','servo_armed','pump_armed','actuator_execution'):assert state['safety'][k] is False
def safe_wire(frame):
    assert frame['mode']=='diag_current_hardware' and frame['ultrasonic_schema_version']==1
    assert frame['actuator_outputs_enabled']==0 and frame['physical_pump_on'] is False
    assert frame['rtc_type']=='NONE'
    assert frame['hardware_verified'] is False
    for k in ('servo_armed','pump_armed','auto_feed','auto_water'):assert frame['current_hardware'][k] is False
    assert set(frame['ultrasonic'])==IDS
    assert (frame['ultrasonic'][HC]['trigger_gpio'],frame['ultrasonic'][HC]['echo_gpio'],frame['ultrasonic'][HC]['role'])==(12,13,'CAT_APPROACH')
    for key in IDS-{HC}:assert frame['ultrasonic'][key]['enabled'] is False
def others_disabled(state):
    for key in IDS-{HC}:
        assert state['ultrasonic'][key]['enabled'] is False
        assert state['ultrasonic'][key]['distance_cm'] is None
frames=[];lines=[];buffer=bytearray();discard=False;stopped=False
try:
    before=get('/api/status');safe_api(before)
    assert set(before['ultrasonic'])==IDS and all(s['firmware_supported'] is True for s in before['ultrasonic'].values())
    assert all(s['enabled'] is False for s in before['ultrasonic'].values()),'Unexpected acquisition already enabled; stop before changing it'
    assert get('/api/hx711/status')['actual_dispensed_grams'] is None
    (O/'before_state.json').write_text(json.dumps(before,indent=2))
    ports=[p for p in list_ports.comports() if p.vid==0x1a86 and p.pid==0x55d3 and p.serial_number=='5C85066678']
    assert len(ports)==1,'Unique expected ESP32 identity not found'
    device=ports[0].device
    subprocess.run(['systemctl','--user','stop','for-cat-esp32-bridge.service'],check=True,timeout=20);stopped=True
    try:
        owners=subprocess.run(['fuser',device],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert owners.returncode==1,'Serial owner remains; do not open competing port'
        with (O/'diagnostic_raw_serial.bin').open('xb') as raw:
            port=serial.Serial(port=None,baudrate=115200,timeout=.1,write_timeout=1,exclusive=True)
            port.dtr=False;port.rts=False;port.port=device
            with port:
                settings=termios.tcgetattr(port.fileno());settings[2]&=~termios.HUPCL;termios.tcsetattr(port.fileno(),termios.TCSANOW,settings)
                def receive(seconds):
                    global discard
                    end=time.monotonic()+seconds
                    while time.monotonic()<end:
                        chunk=port.read(min(4096,max(1,port.in_waiting)))
                        if not chunk:continue
                        raw.write(chunk)
                        assert raw.tell()<=262144,'Raw capture budget exceeded'
                        for byte in chunk:
                            if byte in (10,13):
                                line=bytes(buffer);buffer.clear()
                                if discard:discard=False;continue
                                if not line:continue
                                lines.append(line.decode('utf-8','replace'))
                                if line.startswith(b'{'):
                                    try:frame=json.loads(line)
                                    except (ValueError,UnicodeError):continue
                                    safe_wire(frame);frames.append(frame)
                            elif not discard:
                                if len(buffer)<4096:buffer.append(byte)
                                else:discard=True;buffer.clear()
                receive(3.5)
                assert len(frames)>=2 and all(not s['enabled'] for s in frames[-1]['ultrasonic'].values()),'Disabled safe raw baseline not established'
                assert COMMAND==b'ultra-select hc1 CONFIRM\n'
                port.write(COMMAND);port.flush();result['commands'].append(COMMAND.decode().strip())
                receive(4.5)
                assert any('ULTRA_SINGLE_ACQUISITION_ENABLED_NOT_PHYSICAL_PASS' in line for line in lines),'No sensor-select ACK observed'
                assert frames[-1]['ultrasonic'][HC]['enabled'] is True
    finally:
        subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True,timeout=20);stopped=False
        (O/'raw_frames.json').write_text(json.dumps(frames,indent=2));(O/'serial_lines.log').write_text('\n'.join(lines)+'\n')
    ready=None
    for _ in range(30):
        try:
            state=get('/api/status');safe_api(state);others_disabled(state)
            if state['ultrasonic'][HC]['enabled'] is True:ready=state;break
        except Exception:pass
        time.sleep(.5)
    assert ready is not None,'Bridge did not resume fresh HC1 telemetry'
    samples=[];seen=set();attempts=[];deadline=time.monotonic()+65
    while len(samples)<24 and time.monotonic()<deadline:
        state=get('/api/status');safe_api(state);others_disabled(state)
        row=state['ultrasonic'][HC];assert row['enabled'] is True
        attempts.append(state)
        stamp=row['last_update']
        if stamp is not None and stamp not in seen:
            seen.add(stamp);samples.append({'observed_at':state['observed_at'],'esp32_monotonic_ms':state['esp32']['monotonic_ms'],**row})
        if len(samples)<24:time.sleep(1.1)
    assert len(samples)>=20,'Insufficient independent completed acquisitions; do not claim success'
    (O/'rest_samples.json').write_text(json.dumps(samples,indent=2));(O/'rest_full_states.json').write_text(json.dumps(attempts,indent=2))
    valid=[r['distance_cm'] for r in samples if r['valid'] is True and r['state']=='HEALTHY' and r['distance_cm'] is not None]
    assert all(type(v) in (int,float) and math.isfinite(v) and 0<v<=400 for v in valid)
    async def ws_check():
        import websockets
        async with websockets.connect('ws://127.0.0.1:8000/api/ws/state',open_timeout=8,max_size=131072) as ws:
            values=[json.loads(await asyncio.wait_for(ws.recv(),8)) for _ in range(4)]
        for state in values:safe_api(state);others_disabled(state);assert state['ultrasonic'][HC]['enabled'] is True
        return values
    ws=asyncio.run(ws_check());(O/'ws_frames.json').write_text(json.dumps(ws,indent=2))
    final=get('/api/status');safe_api(final);others_disabled(final)
    worker=get('/api/meal-plans/worker')['worker'];assert worker['running'] and worker['last_error'] is None and worker['actual_dispensed_grams'] is None
    owner=subprocess.run(['fuser',device],stdout=subprocess.PIPE,stderr=subprocess.PIPE);bridge_pid=int(subprocess.check_output(['systemctl','--user','show','for-cat-esp32-bridge','-p','MainPID','--value']))
    assert [int(p) for p in owner.stdout.split()]==[bridge_pid]
    metrics={'completed_samples':len(samples),'valid_samples':len(valid),'timeout_reports':sum(r['timeout'] is True for r in samples),
        'stale_reports':sum(r['stale'] is True for r in samples),'states':sorted({r['state'] for r in samples}),
        'timeout_counter_delta':samples[-1]['timeout_count']-samples[0]['timeout_count'],
        'min_cm':min(valid) if valid else None,'max_cm':max(valid) if valid else None,
        'mean_cm':statistics.mean(valid) if valid else None,'median_cm':statistics.median(valid) if valid else None,
        'spread_cm':max(valid)-min(valid) if valid else None,'stddev_cm':statistics.pstdev(valid) if valid else None,
        'max_sample_age_ms':max((r['sample_age_ms'] for r in samples if r['sample_age_ms'] is not None),default=None)}
    result.update(status='RUNTIME_PASS' if len(valid)>=20 else 'TIMEOUT' if not valid and metrics['timeout_reports'] else 'BLOCKED',metrics=metrics,
        direction_response='NOT_TESTED',physical_status='NOT_TESTED',other_channels_disabled=True,rest_ws_verified=True,serial_owner=bridge_pid,
        acquisition_left_enabled='HC_SR04_1_ONLY',safety=final['safety'],actual_dispensed_grams=None,
        next='Review results before requesting one near/far target movement')
    (O/'final_state.json').write_text(json.dumps(final,indent=2))
except Exception as error:
    result['error']=str(error);raise
finally:
    if stopped:subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True,timeout=20)
    (O/'summary.json').write_text(json.dumps(result,indent=2))
    (O/'manifest_sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='manifest_sha256.json'},indent=2))
    print(json.dumps(result,indent=2))
