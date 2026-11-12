"""Operator physical-reference workflow; uses existing REAL HTTP, no device/TX access."""
import argparse
from contextlib import contextmanager
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import urllib.request

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.hx711_calibration import CalibrationStore, MASSES, binding, safe_bridge

ROOT=Path(__file__).resolve().parents[2]


def api(base,path):
    with urllib.request.urlopen(base+path,timeout=4) as response:return json.load(response)


def provenance(detail):
    raw=safe_bridge(detail)
    ms=detail['telemetry']['monotonic_ms'];host=detail['host_boot_id'];rx=detail['last_rx_monotonic_ms']
    return raw,ms,{'binding':binding(detail),'host_boot_id':host,'boot_estimate_ms':rx-ms,
                  'capture_origin':'OPERATOR_PLACED_REFERENCE_REAL_API',
                  'safety_before':detail['telemetry']['safety'],'safety_after':detail['telemetry']['safety']}


def write_raw_evidence(path,body):
    path.write_text(json.dumps(body,indent=2))
    path.with_name(path.name+'.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest())


def measurement_fields(active,candidate,stats,criteria):
    model=active or candidate
    computed=None if model is None else (stats['mean_raw']-model['tare_offset_counts'])*model['grams_per_count']
    maximum=35+max(criteria['absolute_error_g'],35*criteria['relative_error_fraction'])
    in_range=computed is not None and -criteria['zero_error_g']<=computed<=maximum
    from app.hx711_calibration import point_quality
    quality=None if model is None else point_quality(stats,model['grams_per_count'],criteria)
    return {'grams':computed if active is not None and in_range else None,
      'candidate_grams':computed if active is None and candidate is not None else None,
      'out_of_range_estimate_g':computed if active is not None and not in_range else None,
      'stable':None if active is None else quality['stable'],'candidate_quality':quality,
      'tare_offset_counts':None if model is None else model['tare_offset_counts'],
      'grams_per_count':None if model is None else model['grams_per_count'],
      'calibration_state':'NOT_CALIBRATED' if active is None else active['calibration_state'] if in_range else 'OUT_OF_VALIDATED_RANGE'}


@contextmanager
def exclusive(path):
    import fcntl
    with open(str(path)+'.hx711-calibration.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:fcntl.flock(lock,fcntl.LOCK_UN)


def capture(store,base,session_id,phase,mass,seconds,settle):
    session=store.session(session_id)
    if not 30<=seconds<=120 or not 3<=settle<=30:raise ValueError('capture30..120s after3..30s settling required')
    if mass not in MASSES:raise ValueError('allowed references:0/5/10/20/30/35g')
    samples=[];detail=api(base,'/api/v1/esp32/status');_,_,context=provenance(detail)
    if context['binding']!=session['binding']:raise ValueError('device identity changed')
    print(json.dumps({'phase':'SETTLING','seconds':settle,'operator_declared_reference_g':mass,'grams':None,'actuator_execution':False}),flush=True)
    start=time.monotonic();last_ms=None;epochs=[];end=start+settle+seconds
    failure=None
    try:
        while time.monotonic()<end:
            detail=api(base,'/api/v1/esp32/status');raw,ms,current=provenance(detail)
            if current['host_boot_id']!=context['host_boot_id'] or current['binding']!=context['binding'] or abs(current['boot_estimate_ms']-context['boot_estimate_ms'])>5000:
                raise ValueError('restart/device change during capture; repeat this point')
            if last_ms is not None and ms<last_ms:raise ValueError('MCU reboot during capture')
            if ms!=last_ms and time.monotonic()-start>=settle:
                samples.append({'raw':raw,'device_ms':ms,'observed_at':detail['last_received_at'],
                                'age_seconds':detail.get('bridge_heartbeat_age_seconds')})
                epochs.append(current['boot_estimate_ms'])
            last_ms=ms
            time.sleep(.2)
    except Exception as error:failure=type(error).__name__+': '+str(error)
    context['boot_estimate_ms']=statistics.median(epochs) if epochs else context['boot_estimate_ms']
    context['safety_after']=detail['telemetry']['safety']
    out=Path(session['evidence_dir'])/session_id;out.mkdir(parents=True,exist_ok=True)
    raw_path=out/(phase+'_'+str(mass)+'g_'+str(time.time_ns())+'.raw.json')
    raw_body={'phase':phase,'reference_g':mass,'samples':samples,'context':context,'physical_placement_source':'OPERATOR_COMMAND','capture_error':failure}
    write_raw_evidence(raw_path,raw_body)
    if failure:raise ValueError(failure+'; partial raw evidence='+str(raw_path))
    point=store.record(session_id,phase,mass,samples,context)
    (out/(point['point_id']+'.point.json')).write_text(json.dumps(point,indent=2))
    session=store.session(session_id);candidate=session['candidate'];active=store.active()
    return {'point_id':point['point_id'],'reference_g':mass,'stats':point['stats'],
      **measurement_fields(active,candidate,point['stats'],session['criteria']),
      'tare_candidate_counts':point['stats']['mean_raw'] if phase=='fit' and mass==0 else None,
      'state':session['state'],'physical_result':'PHYSICAL_CALIBRATION_IN_PROGRESS','evidence':str(raw_path),
      'actuator_execution':False,'actual_dispensed_grams':None}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=ROOT/'jetson/data/events.db')
    parser.add_argument('--api-base',default='http://127.0.0.1:8000')
    commands=parser.add_subparsers(dest='command',required=True)
    new=commands.add_parser('new');new.add_argument('--evidence-dir',type=Path,required=True);new.add_argument('--load-cell-capacity-g',type=float)
    for name in ('status','fit','validate','activate','finish'):
        sub=commands.add_parser(name)
        if name!='status':sub.add_argument('--session',required=True)
        if name=='finish':sub.add_argument('--confirm-physical-tests',action='store_true')
    point=commands.add_parser('capture');point.add_argument('--session',required=True);point.add_argument('--phase',choices=['fit','verify','persistence'],required=True)
    point.add_argument('--mass-g',type=float,required=True);point.add_argument('--seconds',type=float,default=30);point.add_argument('--settle-seconds',type=float,default=5)
    reset=commands.add_parser('reset-phase');reset.add_argument('--session',required=True);reset.add_argument('--phase',choices=['verify','persistence'],required=True)
    args=parser.parse_args();store=CalibrationStore(args.db)
    if args.command=='status':result=store.status()
    else:
        with exclusive(args.db):
            if args.command=='new':
                detail=api(args.api_base,'/api/v1/esp32/status');safe_bridge(detail)
                result=store.new(binding(detail),args.evidence_dir,args.load_cell_capacity_g)
            elif args.command=='capture':result=capture(store,args.api_base,args.session,args.phase,args.mass_g,args.seconds,args.settle_seconds)
            elif args.command=='fit':result=store.fit(args.session)
            elif args.command=='validate':result=store.verify(args.session)
            elif args.command=='activate':
                detail=api(args.api_base,'/api/v1/esp32/status');_,_,context=provenance(detail)
                result=store.activate(args.session,context)
            elif args.command=='reset-phase':result=store.reset_phase(args.session,args.phase)
            else:result=store.finish(args.session,args.confirm_physical_tests)
            if args.command not in ('new','capture'):
                session=store.session(args.session);out=Path(session['evidence_dir'])/args.session;out.mkdir(parents=True,exist_ok=True)
                body={'command':args.command,'result':result,'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
                (out/(args.command+'_'+str(time.time_ns())+'.json')).write_text(json.dumps(body,indent=2))
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'status':'BLOCKED','error':type(error).__name__,'detail':str(error),
                          'grams':None,'actuator_execution':False,'actual_dispensed_grams':None}),file=sys.stderr)
        raise SystemExit(2)
