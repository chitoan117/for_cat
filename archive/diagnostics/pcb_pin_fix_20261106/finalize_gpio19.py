from pathlib import Path
import shutil,hashlib
r=Path(__file__).parent
test=r/'test_servo.py';s=test.read_text()
marker="h+=r'''\nuint32_t expectedDuty"
extra="""h+='#define GPIO_IS_VALID_GPIO(p) ((p)>=0&&(p)<=48)\\n#define GPIO_IS_VALID_OUTPUT_GPIO(p) GPIO_IS_VALID_GPIO(p)\\n'
h+='namespace current_hardware {constexpr int SERVO_SIGNAL=6,PUMP_CONTROL=7,D2_WATER_ECHO=19;}\\nstruct TestPins {\\n'
h+=block('  bool inputAllowed(int pin) const override {').replace(' override','')+'\\n'
h+=block('  bool outputAllowed(int pin) const override {').replace(' override','')+'\\n};\\n'
"""
assert marker in s;s=s.replace(marker,extra+marker)
s=s.replace('int main(){','int main(){ TestPins pins; assert(pins.inputAllowed(19)&&!pins.outputAllowed(19)&&!pins.inputAllowed(20)&&!pins.inputAllowed(6)&&!pins.inputAllowed(7));')
test.write_text(s)
out=r/'final';out.mkdir(exist_ok=True)
template=(r/'deploy_servo.py').read_text()
template=template.replace("r=Path('/home/toan/for_cat/evidence/pcb_pin_fix_20261106')","r=Path('/home/toan/for_cat/evidence/pcb_pin_fix_20261106_gpio19')")
template=template.replace('/evidence/servo_tune_20261106/esp32.ino.bin','/evidence/pcb_pin_fix_20261106/esp32.ino.bin')
template=template.replace('8ceb43f5f4939d75b50e25bef8bd226c91c5eaffb4106959f62aaf90a346113a','e1c8519d02234cd975ad92f75c7edfc1d2ca77a70b7626f3d5f5f86e10629738')
(out/'deploy_servo.py').write_text(template)
for name in ['resume_verify.py','verify_pcb_uart.py','enable_readings.py']:
 (out/name).write_text((r/name).read_text().replace('/evidence/pcb_pin_fix_20261106','/evidence/pcb_pin_fix_20261106_gpio19'))
shutil.copy2(r/'esp32/esp32.ino',out/'esp32.ino')
print('Final GPIO19 policy and tests prepared.')
