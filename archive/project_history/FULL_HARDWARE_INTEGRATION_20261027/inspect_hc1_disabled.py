import datetime,json,urllib.request
from pathlib import Path
E=Path(EVIDENCE)
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=8) as r:s=json.load(r)
baseline=json.loads((E/'hc1_after_sensor_5v_20261027T043932670884Z/final_state.json').read_text())
result={'observed_at':s['observed_at'],'esp32':s['esp32'],'baseline_40cm_esp32':baseline['esp32'],
 'current_hc1':s['ultrasonic']['HC_SR04_1'],'safety':s['safety'],
 'mcu_uptime_decreased':s['esp32']['monotonic_ms']<baseline['esp32']['monotonic_ms']}
p=E/('hc1_disabled_inspection_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json');p.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
