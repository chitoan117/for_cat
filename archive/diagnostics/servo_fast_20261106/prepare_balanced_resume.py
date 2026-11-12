from pathlib import Path
r=Path(__file__).parent;out=r/'balanced'
s=(r/'align_trial.py').read_text().replace('/evidence/servo_fast_20261106','/evidence/servo_balanced_20261106')
s=s.replace("f.write('0\\ninspect_ok\\nmode\\nservo_position\\n')", "f.write('0\\ninspect_ok\\nstart\\nmode\\nservo_position\\n')")
s=s.replace('open_ms=750','open_ms=900').replace('close_ms=1050','close_ms=1450').replace('exited=1','exited=0')
s=s.replace("'automatic_ai_demo_exited_for_supervised_trial':True", "'automatic_mode_restored':True")
s=s.replace("trial_ready.json", "resume_verified.json")
(out/'resume_balanced.py').write_text(s)
print('Prepared no-motion profile verification and automatic-mode restore.')
