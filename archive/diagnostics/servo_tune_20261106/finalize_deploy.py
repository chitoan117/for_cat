from pathlib import Path
import json
r=Path(__file__).parent
h=(r.parent/'servo_button_20261106/deploy_servo.py').read_text(encoding='utf-8')
h=h.replace("r=Path('/home/toan/for_cat/evidence/servo_button_20261106')","r=Path('/home/toan/for_cat/evidence/servo_tune_20261106')")
h=h.replace("Path('/home/toan/for_cat/evidence/servo_relative_20261106/esp32.ino.bin')","Path('/home/toan/for_cat/evidence/servo_button_20261106/esp32.ino.bin')")
h=h.replace('d7054e255babead6620ddb9cbb67ebe8ddd080b0c335d10254efce05f79eea89','b88c1aa94df1e1a617405a56effd53a4930bc27246db125b26446bc98dc0984b')
(r/'deploy_servo.py').write_text(h,encoding='utf-8')
owner={'open_ms':1100,'close_ms':1000,'open_us':1400,'close_us':1600,'neutral_us':1500,'physical_cycles_tested_by_owner':5,'owner_confirmation':'Đóng về đúng mốc sau 5 chu kỳ','feedback_sensor':False}
(r/'owner_acceptance.json').write_text(json.dumps(owner,ensure_ascii=False,indent=2),encoding='utf-8')
v=(r.parent/'servo_button_20261106/resume_verify.py').read_text(encoding='utf-8')
v=v.replace("r=Path('/home/toan/for_cat/evidence/servo_button_20261106')","r=Path('/home/toan/for_cat/evidence/servo_tune_20261106')")
v=v.replace("'physical_button_retest_pending':True","'owner_confirmed_5_cycles_before_flash':True")
v=v.replace("assert any('V14 MODE: exited=0'", "assert any('close_ms=1000' in x for x in lines)\nassert any('V14 MODE: exited=0'")
(r/'resume_verify.py').write_text(v,encoding='utf-8')
print('Prepared exact-baseline deployment and owner acceptance record.')
