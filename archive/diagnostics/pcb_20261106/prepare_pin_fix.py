from pathlib import Path
import zipfile, hashlib, json, re, shutil

r=Path('D:/Agent_Cat/diagnostics/pcb_pin_fix_20261106');r.mkdir(exist_ok=True)
project=Path('C:/Users/chito/Downloads/pet_feeder.pdsprj')
with zipfile.ZipFile(project) as z:
    name=next(n for n in z.namelist() if n.endswith('ROOT.LYT'))
    layout=z.read(name)
assert layout==Path('D:/Agent_Cat/diagnostics/pcb_20261106/ROOT.LYT').read_bytes(), 'PCB changed: recheck nets before editing'
(r/'pcb_evidence.json').write_text(json.dumps({'project':str(project),'layout_sha256':hashlib.sha256(layout).hexdigest(),'matches_previously_inspected_pad_net_records':True,'pins':{'E1':[12,13],'E2':[16,17],'D1':[14,15],'D2':[18,19]}},indent=2))
base=Path('D:/Agent_Cat/diagnostics/servo_tune_20261106/1000/deployed/esp32/esp32.ino')
s=base.read_text(encoding='utf-8');(r/'before.ino').write_bytes(base.read_bytes())
(r/'local_pending_before.ino').write_bytes(Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino').read_bytes())
s=s.replace('jsn_food','bowl_d1').replace('jsn_water','tank_d2')
s=s.replace('JSN_WATER_ECHO = 10','D2_WATER_ECHO = 19').replace('{{18,true},{10,true}','{{18,true},{19,true}').replace('digitalRead(10)','digitalRead(19)')
s=s.replace('CAT_MIN_CM = 5.0f','CAT_MIN_CM = 2.0f').replace('CAT_MAX_CM = 20.0f','CAT_MAX_CM = 30.0f')
s=s.replace('CLOSE_AT_G = 30.0f;  // 30..40g acceptable; close on crossing 30g','CLOSE_AT_G = 35.0f;  // Target: close on the first measured added-mass sample >=35g.')
s=s.replace('2.0f, 450.0f','2.0f, 400.0f')
a=s.index('float currentWaterPercent(uint32_t now) {');b=s.index('\nbool beginAllSensors()',a)
s=s[:a]+'''// D1=bowl, D2=reservoir. Old water geometry belonged to a different role.
// Water percentage and pump commissioning are explicitly deferred by owner.
float currentWaterPercent(uint32_t now) {
  (void)now;
  return NAN;
}
'''+s[b:]
s=s.replace('drawDistance("FOOD: ", recentCm(bowl_d1, now)','drawDistance("FOOD E2: ", recentCm(hc2, now)')
s=s.replace('drawDistance("HC1 CAT: "','drawDistance("E1 CAT: "').replace('drawDistance("HC2:     "','drawDistance("E2 FOOD: "').replace('drawDistance("JSN FOOD:"','drawDistance("D1 BOWL: "').replace('drawDistance("JSN H2O: "','drawDistance("D2 TANK: "')
s=s.replace('CAT/HC2/FOOD/WATER cm=','E1_CAT/E2_FOOD/D1_BOWL/D2_TANK cm=')
# Stable legacy keys remain for the installed bridge; explicit PCB keys remove ambiguity.
marker='  out.print(",\\\"water_level_percent\\\":");'
assert marker in s
s=s.replace(marker,'''  out.print(",\\\"pcb_profile\\\":\\\"HCSR04_E1_E2_D1_D2_PINFIX\\\",\\\"pcb_e1_cat_cm\\\":");
  number(recentCm(hc,s.now_ms));
  out.print(",\\\"pcb_e2_food_cm\\\":"); number(recentCm(hc2,s.now_ms));
  out.print(",\\\"pcb_d1_bowl_cm\\\":"); number(recentCm(bowl_d1,s.now_ms));
  out.print(",\\\"pcb_d2_tank_cm\\\":"); number(recentCm(tank_d2,s.now_ms));
'''+marker)
s=s.replace('    stageWaterCalibration(!std::strcmp(line, "water_full"), s.now_ms);','    reply(0,false,"WATER_CALIBRATION_DEFERRED_NEW_PCB_D1_BOWL_D2_TANK");')
s=s.replace('<=20cm','<=30cm').replace('5..20cm','2..30cm').replace('30..40g','35g target').replace('WAIT 30-40g','WAIT 35g')
s=s.replace('JSN FOOD 14/15; JSN WATER 18/10','D1 BOWL 14/15; D2 TANK 18/19').replace('JSN WATER uses TRIG18 ECHO10','D2 TANK uses TRIG18 ECHO19').replace('18/10','18/19')
s=s.replace('GPIO10 is JSN water ECHO input, NOT a separate water-input output.','PCB D2 ECHO J3_20=GPIO19. USB-UART only; native USB D- shares GPIO19.')
s=s.replace('// JSN #1 - food bin distance','// HC-SR04 D1: drinking bowl').replace('// JSN #2 - water surface distance','// HC-SR04 D2: water reservoir').replace('// HC-SR04 #2','// HC-SR04 E2: food reservoir')
s=s.replace('HC1/HC2/JSN1/JSN2/PIR','E1/E2/D1/D2/PIR').replace('HC1/HC2/JSN','E1/E2/D1/D2')
assert 'uint16_t close_ms = 1000' in s and 'D2_WATER_ECHO = 19' in s
(r/'esp32').mkdir(exist_ok=True);(r/'esp32/esp32.ino').write_text(s,encoding='utf-8')
shutil.copy2('D:/Agent_Cat/diagnostics/servo_tune_20261106/1000/deployed/test_servo.py',r/'test_servo.py')
print('Prepared firmware-only pin fix; PCB bytes rechecked; pump control not added.')
