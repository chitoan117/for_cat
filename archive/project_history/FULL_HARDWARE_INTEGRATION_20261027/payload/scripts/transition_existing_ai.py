"""Checkpoint and gracefully hand off the existing detector to the same binary+tap."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path('/home/toan/for_cat')
E=ROOT/'evidence/overnight_integration_20261023'
pid=9198
proc=Path('/proc')/str(pid)
binary=ROOT/'jetson/ai/cat_dog_trt'
assert (proc/'exe').resolve()==binary
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='c3651fc3d1331b24a45c6a74b94a883e362fd4ded2412bb8f3ad195f1c443cdc'
command=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()
environment={}
for pair in (proc/'environ').read_bytes().split(b'\0'):
    key,_,value=pair.partition(b'=')
    if key.decode(errors='replace') in ('DISPLAY','XAUTHORITY','LD_LIBRARY_PATH'):
        environment[key.decode()]=value.decode()
receipt={'old_pid':pid,'command':command,'cwd':str((proc/'cwd').resolve()),'selected_environment':environment,
         'binary_unchanged':True,'source_engine_not_modified':True,'transition':'SIGINT then SAME binary --headless --no-snapshot with C++ stdout tap'}
(E/'ai_process_transition.json').write_text(json.dumps(receipt,indent=2))
os.kill(pid,signal.SIGINT)
deadline=time.monotonic()+15
while proc.exists() and time.monotonic()<deadline:time.sleep(.1)
assert not proc.exists(),'old detector did not exit gracefully; no force kill or duplicate start'
subprocess.check_call(['systemctl','--user','start','for-cat-ai.service'])
print('AI PROCESS CHECKPOINTED AND GRACEFULLY TRANSITIONED; SAME BINARY/ENGINE; NO ACTUATOR PATH')
