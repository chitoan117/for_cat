import datetime,json,urllib.request
from pathlib import Path
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=8) as r:s=json.load(r)
assert s['data_source']=='REAL'
result={'observed_at':s['observed_at'],'HC_SR04_1':s['ultrasonic']['HC_SR04_1'],
 'other_channels':{k:{'enabled':v['enabled'],'distance_cm':v['distance_cm']} for k,v in s['ultrasonic'].items() if k!='HC_SR04_1'},'safety':s['safety']}
path=Path(EVIDENCE)/('hc1_read_now_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json');path.write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
