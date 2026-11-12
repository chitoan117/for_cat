from pathlib import Path
import importlib.util,sys,types,tempfile,sqlite3,json
from contextlib import closing
r=Path('D:/Agent_Cat/diagnostics/ai_gate_20261106')
# Serial transport is faked; the production decision method and SQLite are real.
sys.modules['serial']=types.SimpleNamespace(Serial=object)
spec=importlib.util.spec_from_file_location('candidate_bridge',r/'fc_live_bridge.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
clock=[100.0];m.time=types.SimpleNamespace(monotonic=lambda:clock[0])
class Serial:
 def __init__(self):self.commands=[]
 def write(self,b):self.commands.append(b.decode().strip())
 def flush(self):pass
with tempfile.TemporaryDirectory(dir=r) as tmp:
 root=Path(tmp);m.CMD_FILE=root/'cmd';m.FOOD_MODE_FILE=root/'food'
 runner=m.BridgeRunner(root/'test.db');ser=Serial()
 runner.last_status={'bench_state':'READY','signed_g':0}
 with closing(sqlite3.connect(runner.db_path,isolation_level=None)) as db:db.execute('CREATE TABLE ai_latest(id INTEGER PRIMARY KEY,body TEXT)')
 def frame(cls,conf,at,stamp=None,health='ONLINE',boot=None):
  clock[0]=at
  body={'classification':cls,'confidence':conf,'updated_monotonic_ms':at*1000 if stamp is None else stamp,
   'health':health,'host_boot_id':runner.boot_id if boot is None else boot}
  with closing(sqlite3.connect(runner.db_path,isolation_level=None)) as db:db.execute('INSERT OR REPLACE INTO ai_latest VALUES(1,?)',(json.dumps(body),))
  runner.check_commands_and_ai(ser)
 frame('DOG',.9,100)
 frame('DOG',.9,100.5,stamp=100000)
 frame('DOG',.9,101.2,stamp=100000)
 assert '2' not in ser.commands,'Polling one frame must never confirm DOG'
 frame('CAT',.9,102);frame('CAT',.9,102.2)
 assert '1' in ser.commands,'CAT request must still dispatch'
 runner.last_status['bench_state']='CAT OPENING'
 frame('DOG',.9,103);frame('CAT',.9,103.2)
 assert '2' not in ser.commands,'One DOG glitch must not interrupt CAT'
 for t in [104,104.6,105.2]:frame('DOG',.69,t)
 assert '2' not in ser.commands,'Low confidence DOG must not interrupt CAT'
 frame('DOG',.9,106);frame('DOG',.9,106.6)
 frame('DOG',.9,110,stamp=106600)
 assert runner.dog_candidate_frames==0 and '2' not in ser.commands,'Stale data resets confirmation'
 frame('DOG',.9,111);frame('DOG',.9,111.5)
 assert '2' not in ser.commands
 frame('DOG',.9,112.1)
 assert ser.commands.count('2')==1,'Stable high confidence DOG must retain interrupt/alarm behavior'
 frame('DOG',.9,112.2)
 assert ser.commands.count('2')==1,'Cooldown retained'
 frame('NONE',0,113);assert runner.dog_candidate_frames==0
 frame('DOG',.99,114,boot='wrong-boot');assert runner.dog_candidate_frames==0
 m.CMD_FILE.write_text('weight\n');frame('NONE',0,115)
 assert 'weight' in ser.commands,'Manual command flow unchanged'
print('PASS: duplicate/stale/wrong-boot frames;single DOG glitch;confidence boundary;stable DOG;CAT dispatch;cooldown;manual transport')
