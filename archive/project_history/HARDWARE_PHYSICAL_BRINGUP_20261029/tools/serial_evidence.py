"""Supervised capture only after explicit --execute. Default PLAN opens nothing.
Default TX is read-only status. Interactive actuator TX requires USER-typed SEND
and --actuator-supervised; no startup arm/test/on and no automatic sequencing.
USER_OBSERVED is recorded separately; capture never grants PHYSICAL_PASS.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import signal
import statistics
import sys
import threading
import time
from bridge_guard import BridgeGuard,command

PROFILES={'hx_reference_legacy':'status','sensors':'status','buzzer':'status','servo':'servo status','pump_inert':'pump status','pump_active':'pump status'}
def utc():return datetime.now(timezone.utc).isoformat()
def operator_host():return os.name=='posix'
def reject_constant(_):raise ValueError('non-finite JSON constant')
def manual_command(profile,text,electrical=False,actuator=False):
    if text in ('status','servo status','pump status'):return text if text==PROFILES[profile] else None
    stop={'sensors':'ultra-off CONFIRM','buzzer':'stop','servo':'servo stop','pump_inert':'pump off','pump_active':'pump off'}
    if text=='STOP':return stop.get(profile)
    if profile=='sensors' and electrical and re.fullmatch(r'ultra-(select (hc1|hc2|jsn1|jsn2)|off|multiplex|guard (60|80|100)) CONFIRM',text):return text
    if not actuator:return None
    if profile=='buzzer' and text in ('buzzer-driver ACTIVE_LOW CONFIRM','test CONFIRM','stop'):return text
    if profile=='servo' and (text in ('servo arm YES','servo open','servo close','servo disarm','servo stop') or
        re.fullmatch(r'servo (configure [0-9]{1,4} [0-9]{1,4} [0-9]{1,4} [0-9]{1,4} CONFIRM|set [0-9]{1,4})',text)):return text
    if profile=='pump_active' and (text in ('pump arm YES','pump off','pump disarm') or re.fullmatch(r'pump on ([2-9][0-9]|[1-4][0-9]{2}|500)',text)):return text
    return None
def capture(io,folder,profile,seconds=30,clock=time.monotonic,manual=None,electrical=False,actuator=False,expected_pump_off=None):
    start=clock();next_status=0;pending=bytearray();values=[];count=0;identity=set();incomplete=False
    observed_pump_off=None
    raw_path=folder/'serial_raw.bin'
    with raw_path.open('xb') as raw,(folder/'records.jsonl').open('x',encoding='utf-8') as records:
        def event(kind,**fields):records.write(json.dumps({'utc':utc(),'elapsed_s':clock()-start,'kind':kind,**fields},allow_nan=False)+'\n');records.flush()
        while clock()-start<seconds:
            elapsed=clock()-start
            if elapsed>=next_status:
                tx=PROFILES[profile];io.write((tx+'\n').encode());event('STATUS_TX',command=tx);next_status=elapsed+5
            if manual is not None:
                try:text=manual.get_nowait()
                except queue.Empty:text=None
                if text:
                    if text=='QUIT':event('USER_QUIT');break
                    if text.startswith('OBSERVE '):event('USER_OBSERVED',observation=text[8:512])
                    elif text.startswith('SEND ') or text=='STOP':
                        requested=text[5:] if text.startswith('SEND ') else text
                        allowed=manual_command(profile,requested,electrical,actuator)
                        if profile=='pump_active' and allowed and allowed not in ('pump status','pump off','pump disarm'):
                            if type(expected_pump_off) is not int or expected_pump_off not in (0,1) or observed_pump_off!=expected_pump_off:
                                allowed=None
                        if allowed:io.write((allowed+'\n').encode());event('USER_TYPED_TX',command=allowed)
                        else:event('USER_COMMAND_REJECTED',requested=requested[:256])
            chunk=io.read(min(4096,max(1,io.in_waiting)))
            if not chunk:continue
            raw.write(chunk);count+=len(chunk)
            if count>16*1024*1024:raise ValueError('raw capture budget exceeded; evidence retained')
            pending.extend(chunk)
            while b'\n' in pending:
                line,_,rest=pending.partition(b'\n');pending=bytearray(rest)
                decoded=line.decode('utf-8','replace').rstrip('\r')
                if profile=='pump_active':
                    off=re.search(r'\bGPIO7_off_level=(-?[0-9]+)\b',decoded)
                    if off:observed_pump_off=int(off.group(1))
                data=None
                try:
                    candidate=json.loads(decoded,parse_constant=reject_constant)
                    if isinstance(candidate,dict):data=candidate
                except ValueError:pass
                event('RX',ascii=decoded,json=data)
                if 'KIT_FIRMWARE_ID=' in decoded:identity.add(decoded)
                if data and data.get('kit_firmware_id'):identity.add(data['kit_firmware_id']+' '+str(data.get('kit_profile')))
                if data and 'calibration_source' not in data and data.get('valid') is True and type(data.get('measurement_grams')) in (int,float):
                    value=data['measurement_grams']
                    if __import__('math').isfinite(value) and abs(value)<=1000:values.append(value)
            if len(pending)>16384:raise ValueError('line budget exceeded; raw retained')
        incomplete=bool(pending)
    stats=None
    if values:
        half=max(1,len(values)//2)
        stats={'count':len(values),'first':values[0],'last':values[-1],'min':min(values),'max':max(values),
               'mean':sum(values)/len(values),'sigma':statistics.pstdev(values),'range':max(values)-min(values),
               'drift_half_means':sum(values[-half:])/half-sum(values[:half])/half}
    return {'raw_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(),'raw_bytes':count,
            'firmware_identity_observed':sorted(identity),'measurement_grams_all_samples':stats,
            'partial_final_line':incomplete,'physical_result':'NOT_VERIFIED','USER_OBSERVED':'SEE_RECORDS_OR_EXTERNAL_OBSERVATION',
            'ack_receipt_is_physical_success':False}
def main():
    p=argparse.ArgumentParser();p.add_argument('--port',default='/dev/ttyACM0');p.add_argument('--profile',choices=tuple(PROFILES),required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=int,default=30);p.add_argument('--service-scope',choices=('user','system'),default='user')
    p.add_argument('--interactive',action='store_true');p.add_argument('--electrical-reviewed',action='store_true');p.add_argument('--actuator-supervised',action='store_true')
    p.add_argument('--pump-observation',type=Path);p.add_argument('--execute',action='store_true');p.add_argument('--confirm');a=p.parse_args()
    if not 5<=a.seconds<=300:p.error('seconds5..300')
    if not a.execute:
        print(json.dumps({'mode':'PLAN_ONLY','port':a.port,'profile':a.profile,'status_only_tx':PROFILES[a.profile],
                          'bridge_will_be_restored':'ORIGINAL_STATE','physical_result':'NOT_VERIFIED'}));return
    if a.confirm!='OWNER_SUPERVISED_SERIAL' or not operator_host():p.error('Linux supervised session requires --confirm OWNER_SUPERVISED_SERIAL')
    if a.interactive and not sys.stdin.isatty():p.error('interactive SEND requires a human TTY, not a command pipe')
    if a.actuator_supervised and not a.interactive:p.error('--actuator-supervised requires --interactive human console')
    expected_off=None
    if a.profile=='pump_active':
        if not a.pump_observation:p.error('active pump requires separate measured-polarity USER_OBSERVED file')
        observation=json.loads(a.pump_observation.read_text())['USER_OBSERVED']
        if type(observation.get('f5305s_off_level')) is not int or observation['f5305s_off_level'] not in (0,1) or observation.get('boot_off_verified') is not True or not observation.get('observer'):p.error('pump physical review missing')
        if a.actuator_supervised and observation.get('water_primed') is not True:p.error('no dry pump: explicit owner priming observation required')
        expected_off=observation['f5305s_off_level']
    a.output.mkdir(parents=True,exist_ok=False)
    guard=BridgeGuard(scope=a.service_scope);result={'started_utc':utc(),'test_config':vars(a).copy(),'physical_result':'NOT_VERIFIED','capture_completed':False,
        'firmware_identity_observed':[],'USER_OBSERVED':'NOT_PROVIDED_SEE_RECORDS_OR_EXTERNAL_FILE'}
    result['test_config']={k:str(v) if isinstance(v,Path) else v for k,v in result['test_config'].items()}
    stopped=threading.Event();old={s:signal.signal(s,lambda *args:stopped.set()) for s in (signal.SIGINT,signal.SIGTERM)}
    commands=queue.Queue(maxsize=32)
    if a.interactive:
        def keyboard():
            for text in sys.stdin:
                try:commands.put_nowait(text.strip()[:512])
                except queue.Full:pass
        t=threading.Thread(target=keyboard);t.daemon=True;t.start()
    io=None
    try:
        with guard:
            owner=command(['fuser',a.port])
            if owner['code']!=1 or owner['stderr'].strip():raise RuntimeError('serial port still owned or ownership unknown')
            import serial
            io=serial.Serial(port=None,baudrate=115200,timeout=.1,write_timeout=1);io.dtr=False;io.rts=False;io.port=a.port
            io.open() # exactly one open; do not toggle/reset sensor calibration
            def session_clock():
                if stopped.is_set():raise KeyboardInterrupt('owner/signal stop')
                return time.monotonic()
            try:result.update(capture(io,a.output,a.profile,a.seconds,session_clock,commands if a.interactive else None,a.electrical_reviewed,a.actuator_supervised,expected_off));result['capture_completed']=True
            finally:io.close();io=None
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        if io is not None and io.is_open:io.close()
        for sig,handler in old.items():signal.signal(sig,handler)
        result.update(bridge_history=guard.history,bridge_original_state_restored=guard.restored,finished_utc=utc())
        (a.output/'session.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'evidence':str(a.output),'capture_completed':result['capture_completed'],'bridge_restored':guard.restored,'physical_result':'NOT_VERIFIED'}))
    if not result['capture_completed'] or not guard.restored:raise SystemExit(1)
if __name__=='__main__':main()
