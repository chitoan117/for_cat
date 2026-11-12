"""Operator-only current-mount raw capture/assessment. No flash/tare/calibration TX.

Only wire command is status. 'fit' writes a NEW pending candidate from a fresh
same-boot FIT set; analyze never refits, activates, writes NVS or claims physical PASS.
"""
from datetime import datetime,timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
import uuid

MASSES=(0,5,10,20,35,38)
PHASES=('BASELINE','FIT','FIT_RETURN','VERIFY','RETURN','REBOOT_EMPTY','REBOOT_VERIFY','REBOOT_RETURN')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def finite(v):return type(v) in (int,float) and math.isfinite(v)
def save_new(path,data):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')
def raw_stats(samples):
    if len(samples)<2:raise ValueError('NO_RAW_WINDOW')
    ticks=[s['monotonic_ms'] for s in samples];values=[s['median_raw'] for s in samples]
    if any(type(t) is not int for t in ticks) or any(b<=a or b-a>750 for a,b in zip(ticks,ticks[1:])):raise ValueError('REBOOT_GAP_OR_NONINCREASING_REPORTS')
    if any(not finite(v) or int(v)!=v or v in (0,-1) or not -8388608<v<8388607 for v in values):raise ValueError('INVALID_RAW')
    n=max(1,len(values)//2)
    return {'count':len(values),'span_s':(ticks[-1]-ticks[0])/1000,'mean':statistics.fmean(values),
            'min':min(values),'max':max(values),'range':max(values)-min(values),'sigma':statistics.pstdev(values),
            'drift':abs(statistics.fmean(values[-n:])-statistics.fmean(values[:n]))}
def point_ok(stats,factor):
    return stats['count']>=60 and stats['span_s']>=25 and stats['range']*abs(factor)<=.2 and stats['sigma']*abs(factor)<=.05 and stats['drift']*abs(factor)<=.1
def measurement_stats(samples,key):
    values=[s[key] for s in samples if s.get('valid') is True and finite(s.get(key))]
    return None if not values else {'count':len(values),'mean':statistics.fmean(values),'min':min(values),'max':max(values),'sigma':statistics.pstdev(values)}
def load_session(path):
    folder=Path(path).resolve();session=json.loads((folder/'session.json').read_text(encoding='utf-8'))
    if session.get('kind')!='INOX_BOWL_CURRENT_MOUNT_VALIDATION':raise ValueError('not an inox session')
    return folder,session
def capture(folder,session,port,phase,reference,seconds):
    import serial
    if phase not in PHASES or reference not in MASSES or not 30<=seconds<=120:raise ValueError('capture30..120s, supported phase/mass required')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=folder/('capture_'+stamp+'_'+phase+'_'+str(reference)+'g');out.mkdir(exist_ok=False)
    result={'kind':'REAL_UART_OWNER_PLACED_REFERENCE','session_id':session['session_id'],'mount_id':session['mount_id'],
            'phase':phase,'reference_g':reference,'owner_declared_placement':True,'started_utc':datetime.now(timezone.utc).isoformat(),
            'commands':[],'physical_pass':False,'tare_sent':False,'calibration_or_nvs_write_sent':False,'port':port,'seconds_requested':seconds}
    io=serial.Serial(port=None,baudrate=115200,timeout=.1,write_timeout=1);io.dtr=io.rts=False;io.port=port
    pending=bytearray();samples=[];full=[];rawfile=(out/'serial_raw.bin').open('xb');start=time.monotonic();next_status=0
    try:
        io.open();start=time.monotonic()
        while time.monotonic()-start<seconds:
            elapsed=time.monotonic()-start
            if elapsed>=next_status:
                io.write(b'status\n');io.flush();result['commands'].append({'command':'status','elapsed_s':elapsed});next_status=elapsed+5
            data=io.read(min(4096,max(1,io.in_waiting)))
            if data:rawfile.write(data);rawfile.flush();pending.extend(data)
            while b'\n' in pending:
                line,_,rest=pending.partition(b'\n');pending=bytearray(rest)
                try:message=json.loads(line.decode('utf-8'))
                except (ValueError,UnicodeError):continue
                if not isinstance(message,dict) or message.get('mode')!='HX711_REFERENCE':continue
                if 'profile' in message:
                    full.append(message)
                    if message.get('profile')!='INOX_GROSS_DIAGNOSTIC' or message.get('mount_id')!=session['mount_id']:raise ValueError('WRONG_PROFILE_OR_MOUNT_NOT_DECLARED')
                    if message.get('servo_locked') is not True or message.get('pump_locked') is not True or message.get('actuator_outputs_enabled')!=0:raise ValueError('ACTUATOR_LOCK_CONTRACT')
                    if len({m['boot_nonce'] for m in full})>1:raise ValueError('MCU_RESTART_DURING_CAPTURE')
                elif 'calibration_source' not in message:
                    samples.append(message)
            if len(pending)>16384:raise ValueError('line bound')
        if not full:raise ValueError('INOX_STATUS_NOT_OBSERVED')
        result['boot_nonce']=full[0]['boot_nonce'];result['stats']=raw_stats(samples)
    except Exception as error:result['capture_error']=type(error).__name__+': '+str(error)
    finally:
        if io.is_open:io.close()
        rawfile.close()
    result['elapsed_s']=time.monotonic()-start;result['full_status']=full;result['samples']=samples
    (out/'serial.log').write_text((out/'serial_raw.bin').read_bytes().decode('utf-8','replace'),encoding='utf-8',newline='')
    result['raw_sha256']=sha(out/'serial_raw.bin');save_new(out/'capture.json',result)
    print(json.dumps({'evidence':str(out),'stats':result.get('stats'),'capture_error':result.get('capture_error'),'physical_pass':False},indent=2))
    return result
def points(folder,session):
    values=[]
    for path in sorted(folder.glob('capture_*/capture.json')):
        value=json.loads(path.read_text(encoding='utf-8'));value['_evidence']=str(path)
        if value.get('capture_error') or value.get('mount_id')!=session['mount_id'] or value.get('session_id')!=session['session_id']:raise ValueError('capture error or session mismatch: '+str(path))
        raw=path.parent/'serial_raw.bin'
        if sha(raw)!=value['raw_sha256']:raise ValueError('raw evidence hash mismatch')
        value['stats']=raw_stats(value['samples']);values.append(value)
    return values
def fit_candidate(folder,session):
    if (folder/'calibration_candidate.json').exists():raise ValueError('candidate is frozen; no refit of validation failures, create an explicitly new session if needed')
    selected=[p for p in points(folder,session) if p['phase']=='FIT']
    if len(selected)!=len(MASSES) or sorted(p['reference_g'] for p in selected)!=list(MASSES):raise ValueError('one fresh FIT capture per0/5/10/20/35/38g required')
    if len({p['boot_nonce'] for p in selected})!=1:raise ValueError('FIT points must share the same MCU boot')
    baseline=next(p for p in selected if p['reference_g']==0);offset=baseline['stats']['mean']
    slope=sum(p['reference_g']*(p['stats']['mean']-offset) for p in selected)/sum(m*m for m in MASSES)
    if not finite(slope) or slope==0:raise ValueError('no scale response')
    factor=1/slope
    if abs(factor)>.35:raise ValueError('raw quantization too coarse for0.7g demo tolerance')
    errors=[]
    for p in sorted(selected,key=lambda p:p['reference_g']):
        delta=(p['stats']['mean']-offset)*factor;error=delta-p['reference_g']
        if not point_ok(p['stats'],factor) or abs(error)>(.2 if p['reference_g']==0 else .7):raise ValueError('fit unstable/outside acceptance; no automatic refit')
        errors.append({'reference_g':p['reference_g'],'candidate_delta_g':delta,'error_g':error,'evidence':p['_evidence']})
    model={'kind':'CURRENT_INOX_MOUNT_CANDIDATE','mount_id':session['mount_id'],'session_id':session['session_id'],
           'offset_counts':offset,'counts_per_gram':slope,'gross_origin':'BOWL_ANCHORED_CALIBRATED_SCALE_NOT_ABSOLUTE_BOWL_MASS',
           'empty_bowl_reference_raw':offset,'fit_results':errors,'validation_passed':False,'physical_pass':False,
           'requires_independent_VERIFY_points':True,'fit_boot_nonce':baseline['boot_nonce']}
    save_new(folder/'calibration_candidate.json',model);print(json.dumps(model,indent=2));return model
def analyze(folder,session):
    data=points(folder,session);model_path=folder/'calibration_candidate.json'
    if not model_path.exists():
        result={'assessment':'RAW_ONLY_NO_CURRENT_MOUNT_CANDIDATE','physical_pass':False,'captures':len(data),'raw_windows':[{'phase':p['phase'],'reference_g':p['reference_g'],'stats':p['stats']} for p in data]}
    else:
        model=json.loads(model_path.read_text(encoding='utf-8'))
        if model['mount_id']!=session['mount_id'] or model['session_id']!=session['session_id']:raise ValueError('candidate mount/session mismatch')
        factor=1/model['counts_per_gram'];out=[]
        for p in data:
            value=(p['stats']['mean']-model['empty_bowl_reference_raw'])*factor
            out.append({'phase':p['phase'],'reference_g':p['reference_g'],'fixed_candidate_scale_reading_g':value,
                        'error_g':value-p['reference_g'],'stable':point_ok(p['stats'],factor),
                        'within_tolerance':abs(value-p['reference_g'])<=(.2 if p['reference_g']==0 else .7),
                        'measurement_grams_unfiltered':measurement_stats(p['samples'],'measurement_grams'),
                        'display_grams':measurement_stats(p['samples'],'display_grams'),
                        'boot_nonce':p['boot_nonce'],'evidence':p['_evidence']})
        verify=[p for p in data if p['phase'] in ('VERIFY','RETURN')]
        expected=[('VERIFY',0)]+[(phase,mass) for m in MASSES[1:] for phase,mass in (('VERIFY',m),('RETURN',0))]
        sequence=[(p['phase'],p['reference_g']) for p in verify]
        complete=sequence==expected and len({p['boot_nonce'] for p in verify})==1
        reboot=[p for p in data if p['phase'].startswith('REBOOT')]
        reboot_complete=[(p['phase'],p['reference_g']) for p in reboot]==[('REBOOT_EMPTY',0),('REBOOT_VERIFY',35),('REBOOT_RETURN',0)]
        reboot_same_pair=False
        if reboot_complete:
            reboot_same_pair=all(p['full_status'] and all(s.get('mount_binding_match') is True and s.get('calibration_source')=='ESP32_NVS_CURRENT_MOUNT_PENDING' and
                finite(s.get('offset')) and abs(s['offset']-model['offset_counts'])<1e-6 and finite(s.get('scale_factor_counts_per_gram')) and abs(s['scale_factor_counts_per_gram']-model['counts_per_gram'])<1e-6 for s in p['full_status']) for p in reboot)
            reboot_same_pair=reboot_same_pair and len({p['boot_nonce'] for p in reboot})==1 and reboot[0]['boot_nonce']!=verify[0]['boot_nonce'] if verify else False
        checks=[p for p in out if p['phase'] not in ('FIT','BASELINE')]
        okay=complete and reboot_complete and reboot_same_pair and all(p['stable'] and p['within_tolerance'] for p in checks)
        result={'assessment':'POINTS_WITHIN_CRITERIA_PENDING_OWNER_EVIDENCE_REVIEW' if okay else 'VALIDATION_PENDING_OR_FAILED',
                'verification_sequence_complete':complete,'reboot_sequence_complete':reboot_complete,'nvs_same_pair_after_reboot':reboot_same_pair,
                'physical_pass':False,'no_auto_tare_or_refit':True,'gross_origin':model['gross_origin'],'points':out}
    output=folder/('analysis_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json');save_new(output,result)
    print(json.dumps({'report':str(output),**result},indent=2));return result
def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    new=sub.add_parser('new');new.add_argument('--directory',type=Path,required=True);new.add_argument('--mount-id',required=True)
    for cmd in ('fit','analyze'):
        p=sub.add_parser(cmd);p.add_argument('--session',type=Path,required=True)
    p=sub.add_parser('capture');p.add_argument('--session',type=Path,required=True);p.add_argument('--port',required=True);p.add_argument('--phase',choices=PHASES,required=True);p.add_argument('--reference-g',type=int,choices=MASSES,required=True);p.add_argument('--seconds',type=int,default=30)
    args=parser.parse_args()
    if args.command=='new':
        if not 1<=len(args.mount_id)<=40 or any(not(c.isascii() and (c.isalnum() or c in '_-')) for c in args.mount_id):raise ValueError('ASCII mount ID1..40 required')
        args.directory.mkdir(parents=True,exist_ok=False)
        data={'kind':'INOX_BOWL_CURRENT_MOUNT_VALIDATION','session_id':uuid.uuid4().hex,'mount_id':args.mount_id,
              'created_at':datetime.now(timezone.utc).isoformat(),'bowl_fixed':'OWNER_TO_CONFIRM','logic_3v3_protection':'OWNER_MEASUREMENT_REQUIRED',
              'physical_pass':False,'old_calibration_authority':'NOT_ACCEPTED_FOR_NEW_MOUNT'}
        save_new(args.directory/'session.json',data);print(json.dumps(data,indent=2));return
    folder,session=load_session(args.session)
    if args.command=='capture':capture(folder,session,args.port,args.phase,args.reference_g,args.seconds)
    elif args.command=='fit':fit_candidate(folder,session)
    else:analyze(folder,session)
if __name__=='__main__':main()
