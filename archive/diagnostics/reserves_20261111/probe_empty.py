from pathlib import Path
import json,time,urllib.request,statistics,hashlib
R=Path('/home/toan/for_cat/evidence/reserves_20261111');R.mkdir(exist_ok=True)
samples=[];seen=set();end=time.monotonic()+22
while len(samples)<15 and time.monotonic()<end:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=4) as r:s=json.load(r)
    us=s.get('ultrasonic',{});e2=us.get('HC_SR04_2',{});d2=us.get('JSN_SR04T_2',{})
    stamps=(e2.get('last_update'),d2.get('last_update'))
    if s.get('esp32',{}).get('connected') is True and e2.get('valid') is True and d2.get('valid') is True and stamps not in seen:
        seen.add(stamps);samples.append({'e2':e2['distance_cm'],'d2':d2['distance_cm'],'stamps':stamps})
    time.sleep(.25)
assert len(samples)>=10,'Insufficient fresh E2/D2 samples'
config={'schema_version':1,'updated_at':time.time(),'roles':{}}
for role,key in (('food','e2'),('water','d2')):
    values=[s[key] for s in samples];median=statistics.median(values);span=max(values)-min(values)
    assert span<=1.0,(role,'Unstable empty level',span)
    config['roles'][role]={'empty_cm':median,'full_cm':None,'empty_tolerance_cm':round(max(.3,max(abs(x-median) for x in values)+.1),3),'source':'OWNER_CONFIRMED_EMPTY_20261111'}
result={'owner_declared_both_empty':True,'samples':samples,'calibration':config}
(R/'empty_probe.json').write_text(json.dumps(result,indent=2))
(R/'reservoir_calibration.json').write_text(json.dumps(config,indent=2))
print(json.dumps({'samples':len(samples),'calibration':config},indent=2))
