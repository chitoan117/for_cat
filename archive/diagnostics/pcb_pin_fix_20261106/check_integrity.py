from pathlib import Path
import re,json,hashlib
r=Path(__file__).parent
old=(r/'before.ino').read_text();new=(r/'esp32/esp32.ino').read_text()
def block(s,marker):
 a=s.index(marker); b=s.index('{',a); n=1;e=b+1
 while n:
  if s[e]=='{':n+=1
  elif s[e]=='}':n-=1
  e+=1
 return s[a:e]
for marker in ['class Hx711Median3 {','class Hx711ReferenceDisplay {','class Hx711 {','class HxAdapter {']:
 assert block(old,marker)==block(new,marker),marker+' changed'
mapping={name: [int(v) for v in re.search(r'\b'+name+r'\.begin\(\{\{(\d+),true\},\{(\d+),true\}',new).groups()] for name in ['hc','hc2','bowl_d1','tank_d2']}
assert mapping=={'hc':[12,13],'hc2':[16,17],'bowl_d1':[14,15],'tank_d2':[18,19]}
assert 's.closing_lead_g = 0;' in new and 'CLOSE_AT_G = 35.0f' in new
assert 'cat_inspect_required' in new and 'uint16_t close_ms = 1000' in new
for label in ['E1 MEO:','E2 THUC AN:','D1 CHEN:','D2 BINH:']:
 assert label in block(new,'void updateOLED(uint32_t now) {')
result={'hx_driver_filter_conversion_byte_identical':True,'physical_pin_mapping':mapping,'oled_all_four_roles':True,'close_threshold_g':35,'servo_ms':[1100,1000],'pump_feature_added':False}
(r/'integrity_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
