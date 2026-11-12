from pathlib import Path
import json,hashlib,shutil
r=Path(__file__).parent;out=r/'balanced'
owner={'owner_report':'Đóng đúng mốc sau 3 lượt','opening_report':'Opening900ms correct',
 'physical_cycles':3,'open_us':1350,'open_ms':900,'close_us':1600,'close_ms':1450,'neutral_us':1500,
 'feedback_sensor':False,'mechanical_stop_does_not_cut_servo_power':True}
(out/'owner_acceptance.json').write_text(json.dumps(owner,ensure_ascii=False,indent=2),encoding='utf-8')
src=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert src.read_bytes()==(r/'esp32/esp32.ino').read_bytes(),'Source changed during physical trial'
(out/'before_source.sha256').write_text(hashlib.sha256(src.read_bytes()).hexdigest())
for name in ['esp32.ino.bin','esp32.ino.partitions.bin']:
 shutil.copy2(out/'build'/name,out/name)
(out/'app.sha256').write_text(hashlib.sha256((out/'esp32.ino.bin').read_bytes()).hexdigest())
print(json.dumps(owner,ensure_ascii=True,indent=2))
