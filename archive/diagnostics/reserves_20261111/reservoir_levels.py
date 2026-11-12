"""Container level calibration. E2=food hopper; D2=water tank, never D1."""
from pathlib import Path
from threading import RLock
import json,math,os,time,statistics

SENSORS={'food':('HC_SR04_2','E2'),'water':('JSN_SR04T_2','D2')}
LOCK=RLock()
DEFAULT_PATH=Path(__file__).resolve().parents[1]/'data/reservoir_calibration.json'

def numeric(x):return type(x) in (int,float) and math.isfinite(x)
def load(path=DEFAULT_PATH):
    try:
        data=json.loads(Path(path).read_text())
        return data if data.get('schema_version')==1 and isinstance(data.get('roles'),dict) else {}
    except (OSError,ValueError,TypeError):return {}

def levels(channels,path=DEFAULT_PATH):
    calibration=load(path);result={}
    for role,(sensor_id,label) in SENSORS.items():
        sensor=channels.get(sensor_id) or {};cm=sensor.get('distance_cm')
        valid=sensor.get('valid') is True and numeric(cm) and 2<=cm<=400
        cal=calibration.get('roles',{}).get(role) or {}
        empty,full,tolerance=cal.get('empty_cm'),cal.get('full_cm'),cal.get('empty_tolerance_cm',.3)
        empty_ok=numeric(empty) and 2<=empty<=400
        full_ok=empty_ok and numeric(full) and 2<=full<empty-.5
        tolerance=tolerance if numeric(tolerance) and .1<=tolerance<=1 else .3
        percent=None
        if valid and empty_ok:
            if cm>=empty-tolerance:percent=0.0
            elif full_ok:percent=round(max(0.,min(100.,100.*(empty-cm)/(empty-full))),1)
        state=('UNAVAILABLE' if not valid else 'NEEDS_EMPTY' if not empty_ok else
               'EMPTY' if percent==0 else 'NEEDS_FULL' if not full_ok else
               'FULL' if percent>=99 else 'LOW' if percent<=20 else 'OK')
        result[role]={'sensor_id':sensor_id,'sensor_label':label,'distance_cm':cm if valid else None,
            'valid':valid,'percent':percent,'state':state,'empty_cm':empty if empty_ok else None,
            'full_cm':full if full_ok else None,'calibration':'READY' if full_ok else 'EMPTY_ONLY' if empty_ok else 'NOT_CALIBRATED'}
    return result

def save_full(path,role,values):
    if role not in SENSORS:raise ValueError('Vai trò cảm biến không hợp lệ.')
    if len(values)<5 or any(not numeric(x) or not 2<=x<=400 for x in values):raise ValueError('Cần số đo mới, hợp lệ.')
    if max(values)-min(values)>1.0:raise ValueError('Số đo chưa ổn định. Giữ nguyên hộp/bình rồi thử lại.')
    full=round(statistics.median(values),3)
    with LOCK:
        config=load(path);cal=config.get('roles',{}).get(role) or {};empty=cal.get('empty_cm')
        if not numeric(empty):raise ValueError('Chưa lưu mốc cạn của hộp/bình.')
        if full>=empty-max(.8,2*cal.get('empty_tolerance_cm',.3)):
            raise ValueError('Mức đo còn gần đáy. Hãy bổ sung đến mức đầy trước khi lưu.')
        config['roles'][role]={**cal,'full_cm':full,'full_source':'OWNER_CONFIRMED_FULL','full_updated_at':time.time()}
        config['updated_at']=time.time()
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp')
        temp.write_text(json.dumps(config,indent=2));temp.replace(path)
    return full
