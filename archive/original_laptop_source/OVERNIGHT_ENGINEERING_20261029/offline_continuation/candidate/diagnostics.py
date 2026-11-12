"""Optional FastAPI hardware-test extension, not installed in production.
Reuses SystemState/FrameHub; NEVER opens a camera/serial or computes food action.
Default buzzer has NO transport and rejects before any command. Fake executor is
only for offline contract testing; actual single-owner bridge RPC is a blocker.
"""
import json
from contextlib import closing
import math
from pathlib import Path
import sqlite3
from threading import RLock
import time
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field,ConfigDict

CHANNELS={'HC_SR04_1':(12,13),'HC_SR04_2':(16,17),'JSN_SR04T_1':(14,15),'JSN_SR04T_2':(18,10)}
def finite(v):return type(v) in (int,float) and math.isfinite(v)
def manual_capability(bridge):
    cap=(bridge.get('telemetry') or {}).get('manual_buzzer_capability')
    required={'profile':'manual_buzzer_sensor_diag_v1','gpio':2,'polarity':'ACTIVE_LOW','vcc':3.3,
              'manual_only':True,'auto_off_ms':600,'max_tests_per_boot':3,'cooldown_ms':60000}
    return isinstance(cap,dict) and all(cap.get(k)==v for k,v in required.items())
def water_level(distance,geometry):
    if geometry is None:return {'percent':None,'state':'NOT_CONFIGURED'}
    required=('empty_cm','full_cm','module_min_cm','module_max_cm')
    if not isinstance(geometry,dict) or any(not finite(geometry.get(k)) for k in required) or not isinstance(geometry.get('mount_id'),str) or not geometry['mount_id'] or geometry.get('owner_reviewed') is not True:
        return {'percent':None,'state':'GEOMETRY_NOT_REVIEWED'}
    empty,full,low,high=(geometry[k] for k in required)
    if not 0<low<=full<empty<=high<=400:return {'percent':None,'state':'INVALID_GEOMETRY'}
    if not finite(distance):return {'percent':None,'state':'NO_VALID_DISTANCE'}
    if not full<=distance<=empty:return {'percent':None,'state':'OUTSIDE_CONFIGURED_GEOMETRY'}
    return {'percent':(empty-distance)/(empty-full)*100,'state':'CONFIGURED_GEOMETRY_ONLY',
            'mount_id':geometry['mount_id'],'physical_acceptance':False}
class Journal:
    def __init__(self,path):
        self.path=Path(path).resolve()
        with closing(sqlite3.connect(self.path)) as db:
            with db:db.execute('CREATE TABLE IF NOT EXISTS hardware_test_events(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,body TEXT NOT NULL)')
    def add(self,kind,body):
        body={**body,'physical_result':'NOT_VERIFIED','servo':'LOCKED','pump':'LOCKED'}
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                db.execute('INSERT INTO hardware_test_events(kind,body) VALUES(?,?)',(kind,json.dumps(body,allow_nan=False)))
                db.execute('DELETE FROM hardware_test_events WHERE seq NOT IN (SELECT seq FROM hardware_test_events ORDER BY seq DESC LIMIT 256)')
    def events(self,limit=50):
        limit=max(1,min(256,int(limit)))
        with closing(sqlite3.connect(self.path)) as db:return [{'seq':r[0],'kind':r[1],**json.loads(r[2])} for r in db.execute('SELECT seq,kind,body FROM hardware_test_events ORDER BY seq DESC LIMIT ?',(limit,))]
class BuzzerContract:
    """No real executor in this kit. A later qualified bridge must enforce MCU
    auto-off/budget itself; API polling/restart is NOT a hardware safety timer.
    """
    def __init__(self,executor=None,qualified=False,clock=time.monotonic):
        self.executor=executor;self.qualified=qualified;self.clock=clock;self.requests={};self.last=None;self.count=0;self.lock=RLock()
    def capability(self):return {'available':self.executor is not None and self.qualified,
        'gpio':2,'polarity':'ACTIVE_LOW','vcc':3.3,'sequence':'2x200ms_gap200ms','max_sequence_ms':600,
        'cooldown_s':60,'max_tests_per_boot':3,'reason':None if self.executor is not None and self.qualified else 'CURRENT_SENSOR_FIRMWARE_HAS_NO_GPIO2_MANUAL_BUZZER_CAPABILITY'}
    def request(self,request_id):
        with self.lock:
            if not self.capability()['available']:raise HTTPException(409,self.capability()['reason'])
            if request_id in self.requests:return self.requests[request_id]
            now=self.clock()
            if self.count>=3 or (self.last is not None and (now<self.last or now-self.last<60)):raise HTTPException(429,'test budget/cooldown')
            if len(self.requests)>=3:raise HTTPException(429,'bounded test identities')
            # Executor must be an explicitly injected qualified single-owner RPC.
            # This repository supplies NO implementation that writes real UART.
            self.count+=1;self.last=now
            value={'request_id':request_id,'status':'REQUEST_RECEIVED_NOT_ACOUSTIC_PASS','sequence_ms':600,
                'physical_result':'NOT_VERIFIED','feed_success':False,'servo':'LOCKED','pump':'LOCKED'}
            self.requests[request_id]=value
            try:self.executor.start_fixed_sequence(request_id)
            except Exception:value['status']='TRANSPORT_RESULT_UNKNOWN_DO_NOT_REPEAT'
            return value
class TestRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:str=Field(min_length=1,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')
    confirm:str
class Observation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    sensor_id:str=Field(min_length=1,max_length=64)
    USER_OBSERVED:str=Field(min_length=1,max_length=1024)
def require(request,permission):
    if not request.app.state.remote_policy.allowed(request.scope,permission):raise HTTPException(403,'requires '+permission)
def snapshot(system,bridge,hub,config,buzzer,clock=time.monotonic):
    connected=system.get('esp32',{}).get('connected') is True and system.get('esp32',{}).get('health')=='ESP32_CONNECTED'
    stamp=bridge.get('last_rx_monotonic_ms')
    host_age=clock()*1000-stamp if finite(stamp) else None
    fresh=connected and bridge.get('health')=='ESP32_CONNECTED' and bridge.get('telemetry_usable_now') is True and finite(host_age) and 0<=host_age<=3000
    source='REAL' if system.get('data_source')=='REAL' else 'SIMULATED' if system.get('data_source')=='MOCK' else 'UNKNOWN'
    # File replays exercise the REAL wire parser, never advertise their values as
    # real sensor measurements at the API/UI boundary.
    if config.get('execution_context')=='OFFLINE_TEST_ONLY':source='SIMULATED'
    raw=bridge.get('telemetry') or {};sensors=raw.get('sensors') or {};channels={}
    fresh=fresh and raw.get('mode')=='diag_current_hardware'
    for key,(trig,echo) in CHANNELS.items():
        s=system.get('ultrasonic',{}).get(key,{})
        valid=fresh and s.get('valid') is True and s.get('state')=='HEALTHY' and s.get('enabled') is True and s.get('timeout') is False and s.get('stale') is False
        age=s.get('sample_age_ms');valid=valid and finite(age) and 0<=age<=2000 and host_age<=2000
        distance=s.get('distance_cm');valid=valid and finite(distance) and 0<distance<=400
        identity=s.get('trigger_gpio')==trig and s.get('echo_gpio')==echo
        distance=distance if valid and identity else None
        raw_state=s.get('measurement_state',s.get('state','UNKNOWN'))
        health=bridge.get('health',system.get('esp32',{}).get('health'))
        if health=='ESP32_BAD_TELEMETRY':state='INVALID'
        elif health=='ESP32_DISCONNECTED':state='DISCONNECTED'
        elif not fresh or (finite(age) and max(host_age or 0,age)>2000):state='STALE'
        elif not identity:state='INVALID'
        elif s.get('timeout') is True:state='TIMEOUT'
        elif raw_state in ('OUT_OF_RANGE','INVALID_OR_INITIALIZING','FAULT'):state='INVALID'
        elif distance is not None:state='OK'
        elif raw_state in ('VALID_READING_NOT_PHYSICAL_PASS','HEALTHY'):state='INVALID'
        else:state=raw_state
        channels[key]={'trigger_gpio':trig,'echo_gpio':echo,'distance_cm':distance,'valid':distance is not None,
            'role':'WATER_LEVEL' if key=='JSN_SR04T_1' else 'TBD' if key=='JSN_SR04T_2' else 'DISTANCE',
            'state':state,'sample_age_ms':age if finite(age) and age>=0 else None,
            'reason':None if state=='OK' else state,'observation_is_physical_pass':False,
            'water_level':water_level(distance,config.get(key)) if key=='JSN_SR04T_1' else
                {'percent':None,'state':'ROLE_TBD_LEVEL_DISABLED'} if key=='JSN_SR04T_2' else None}
    pir=sensors.get('pir',{});q=fresh and pir.get('qualified_fields_available') is True
    pir_valid=q and host_age<=2000 and pir.get('motion_valid') is True and pir.get('motion_quality')=='VALID' and type(pir.get('motion_stable')) is bool
    weight=system.get('weight',{});hx=sensors.get('hx711',{})
    grams=None;authority='NO_CURRENT_CALIBRATED_MEASUREMENT'
    if fresh and weight.get('calibrated') is True and weight.get('calibration_valid') is True and finite(weight.get('grams')):
        grams=weight['grams'];authority='HOST_CURRENT_CALIBRATION_VIEW_NOT_FEED_AUTHORITY'
    elif fresh and hx.get('firmware_observation_valid') is True and finite(hx.get('firmware_age_at_frame_ms')) and 0<=host_age+hx['firmware_age_at_frame_ms']<=1500 and finite(hx.get('firmware_value_grams')) and abs(hx['firmware_value_grams'])<=1000:
        grams=hx['firmware_value_grams'];authority='FIRMWARE_OBSERVATION_CONTEXT_PERSISTENCE_NOT_VERIFIED'
    food=config.get('FOOD_ROI',{'mode':'FULL_FRAME','region':None,'reviewed':False})
    if not isinstance(food,dict) or food.get('mode') not in ('FULL_FRAME','ROI_ENABLED'):raise ValueError('FOOD_ROI config mode')
    if food['mode']=='ROI_ENABLED':
        roi=food.get('region')
        if food.get('reviewed') is not True or not isinstance(roi,list) or len(roi)!=4 or not all(finite(v) for v in roi) or not 0<=roi[0]<roi[2]<=1 or not 0<=roi[1]<roi[3]<=1:raise ValueError('reviewed normalized FOOD_ROI required')
    capability=buzzer.capability()
    safety=system.get('safety',{})
    safe=safety.get('actuator_execution') is False and safety.get('actuator_outputs_enabled')==0 and all(safety.get(k) is False for k in ('servo_armed','pump_armed','auto_feed','auto_water'))
    if not fresh or source!='REAL' or not safe or not manual_capability(bridge):
        capability={**capability,'available':False,'reason':'FRESH_REAL_LINK_AND_QUALIFIED_MANUAL_BUZZER_FIRMWARE_REQUIRED'}
    ai=system.get('ai',{'classification':'UNKNOWN'})
    if ai.get('classification') not in ('CAT','DOG','NONE','UNKNOWN') or ai.get('simulated') is True or ai.get('data_source') in ('SIMULATED','MOCK'):
        ai={'classification':'UNKNOWN','health':'UNKNOWN','reason':'AI_PROVENANCE_OR_CLASS_NOT_REAL_CPP_CONTRACT'}
    return {'schema_version':'hardware_diagnostics_v1','source':source,'simulated':source=='SIMULATED',
        'execution_context':config.get('execution_context','OWNER_RUNTIME_NOT_PHYSICAL_ACCEPTANCE'),
        'telemetry_time':{'clock_domain':'HOST_MONOTONIC_MS','last_rx_ms':stamp if finite(stamp) else None,
            'age_ms':host_age if finite(host_age) and host_age>=0 else None,
            'device_uptime_ms':raw.get('monotonic_ms'),'is_UTC_timestamp':False},
        'connection':system.get('esp32',{}),'camera':hub.status(),'ai':ai,
        'FOOD_ROI':{**food,'producer_membership_proof':False},'ultrasonic':channels,
        'pir':{'motion':pir['motion_stable'] if pir_valid else None,'valid':pir_valid,
            'quality':('STALE' if q and host_age>2000 else pir.get('motion_quality')) if q else 'QUALIFIED_FIELDS_UNAVAILABLE_OR_STALE'},
        'hx711':{'grams':grams,'raw_counts':weight.get('raw_counts') if fresh else None,'authority':authority,
            'static_measurement_physical_pass':'YES_OWNER_ACCEPTED','calibration_persistence':'NOT_VERIFIED','closed_loop_35g':'NOT_VERIFIED'},
        'oled':{'health':sensors.get('oled',{}).get('health','UNKNOWN') if fresh else 'STALE',
            'initialized':sensors.get('oled',{}).get('initialized') if fresh else None,'prior_display_owner_evidence':'RETAINED_NO_RETEST_REQUIRED'},
        'button':{'gpio':21,'pressed':sensors.get('button',{}).get('pressed') if fresh else None,
            'request_count':sensors.get('button',{}).get('request_count') if fresh else None,'actuator_blocked':True},
        'buzzer':capability,'servo':'LOCKED','pump':'LOCKED','actuator_execution':False,
        'hardware_safety_telemetry':safety,'lock_labels_are_policy_not_physical_off_proof':True,
        'diagnostic_snapshot_is_physical_pass':False}
def mount(app,log_path,config=None,buzzer=None,system_provider=None,bridge_provider=None,clock=time.monotonic):
    if Path(log_path).resolve()==Path(app.state.store_path).resolve():raise ValueError('diagnostic journal must NOT be production/canonical DB')
    config=config or {};journal=Journal(log_path);buzzer=buzzer or BuzzerContract()
    system_provider=system_provider or app.state.system_state.snapshot
    bridge_provider=bridge_provider or (lambda:app.state.esp32_reader.status() if app.state.esp32_reader else {})
    router=APIRouter(prefix='/api/v1/hardware-diagnostics')
    @router.get('/status')
    def status(request:Request):
        require(request,'VIEW_CAMERA')
        result=snapshot(system_provider(),bridge_provider(),app.state.live_camera,config,buzzer,clock)
        result['permissions']={'VIEW_CAMERA':True,'CONTROL_SYSTEM':request.app.state.remote_policy.allowed(request.scope,'CONTROL_SYSTEM')}
        return result
    @router.get('/events')
    def events(request:Request):require(request,'VIEW_CAMERA');return journal.events()
    @router.get('/events/export')
    def export(request:Request):
        require(request,'VIEW_CAMERA')
        return JSONResponse({'kind':'BOUNDED_HARDWARE_TEST_LOG_EXPORT','physical_pass':False,'events':journal.events(256)},
            headers={'Content-Disposition':'attachment; filename="forcat-hardware-test-log.json"','Cache-Control':'no-store'})
    @router.post('/observations')
    def observe(body:Observation,request:Request):
        require(request,'CONTROL_SYSTEM');journal.add('USER_OBSERVED',body.model_dump());return {'recorded':True,'physical_result':'NOT_VERIFIED'}
    @router.post('/buzzer-test')
    def buzzer_test(body:TestRequest,request:Request):
        require(request,'CONTROL_SYSTEM')
        if body.confirm!='BUZZER_GPIO2_ACTIVE_LOW_3V3_REVIEWED':raise HTTPException(400,'explicit electrical/owner review required')
        view=snapshot(system_provider(),bridge_provider(),app.state.live_camera,config,buzzer,clock)
        if not view['buzzer']['available']:
            journal.add('BUZZER_TEST_BLOCKED',{'request_id':body.request_id,'reason':view['buzzer']['reason'],'uart_command_sent':False})
            raise HTTPException(409,view['buzzer']['reason'])
        receipt=buzzer.request(body.request_id);journal.add('BUZZER_REQUEST_RECEIPT',receipt);return receipt
    app.include_router(router)
    return {'journal':journal,'buzzer':buzzer}
