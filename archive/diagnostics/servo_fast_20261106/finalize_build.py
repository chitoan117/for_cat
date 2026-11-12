from pathlib import Path
import hashlib,shutil,json
r=Path(__file__).parent
for name in ['esp32.ino.bin','esp32.ino.partitions.bin']:
 shutil.copy2(r/'build'/name,r/name)
(r/'app.sha256').write_text(hashlib.sha256((r/'esp32.ino.bin').read_bytes()).hexdigest())
old=(r/'before.ino').read_text();new=(r/'esp32/esp32.ino').read_text()
def block(s,marker):
 a=s.index(marker);b=s.index('{',a);n=1;e=b+1
 while n:
  if s[e]=='{':n+=1
  if s[e]=='}':n-=1
  e+=1
 return s[a:e]
for marker in ['class Hx711Median3 {','class Hx711ReferenceDisplay {','class Hx711 {','class HxAdapter {','bool beginAllSensors() {','void tick(const Sample& s, uint32_t now) {']:
 assert block(old,marker)==block(new,marker),'Unexpected logic change:'+marker
result={'hx_and_distance_drivers_unchanged':True,'feed_state_machine_unchanged':True,
 'open_us':1350,'open_ms':750,'close_us':1600,'close_ms':1050,'neutral_us':1500,
 'physical_confirmation':'PENDING','app_sha256':(r/'app.sha256').read_text()}
(r/'profile.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
