from pathlib import Path
import ast,hashlib,importlib.util,json,shutil,sqlite3,subprocess,tempfile,os
r=Path(__file__).parent
target=Path('/home/toan/for_cat/jetson/tools/fc_live_bridge.py')
candidate=r/'fc_live_bridge.py'
old=target.read_bytes()
assert hashlib.sha256(old).hexdigest()=='0a61041a2bae26d1adb6725246a35c18f6f10e7d3dad59cc7e5f4bd9138d6a5c','Live bridge changed; do not overwrite'
def methods(data):
    tree=ast.parse(data)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BridgeRunner')
    return {n.name:ast.dump(n,include_attributes=False) for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
a=methods(old); b=methods(candidate.read_bytes())
assert set(a)==set(b)
assert [k for k in a if a[k]!=b[k]]==['handle_status'],'Unexpected dispatch/control change'
spec=importlib.util.spec_from_file_location('forcat_bridge_metadata_candidate',str(candidate))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='bridge_metadata_',dir=str(r)) as tmp:
    database=Path(tmp)/'events.db'
    runner=module.BridgeRunner(database)
    for calibrated,closed,expected in [(False,None,'UNKNOWN'),(True,None,'UNKNOWN'),(True,False,'UNKNOWN'),(True,True,'CLOSED')]:
        runner.handle_status({'type':'status','ms':1000,'calibrated':calibrated,'physical_closed':closed,
                              'raw_valid':False,'raw':None,'hx_health':'FAULT','grams':None,'signed_g':None,
                              'bench_state':'READY','oled_ok':False},'/dev/OFFLINE_TEST_ONLY')
        with sqlite3.connect(str(database)) as connection:
            value=json.loads(connection.execute('select body from esp32_latest where id=1').fetchone()[0])
        t=value['telemetry']
        assert t['sensors']['hx711']['firmware_calibrated']==calibrated
        assert t['safety']['servo_state']==expected
        assert t['fc_live']['grams'] is None
        assert all(s['distance_cm'] is None for s in t['ultrasonic'].values())
backup=r/'fc_live_bridge.before.py'
assert not backup.exists(),'Backup already exists; inspect before rerunning'
shutil.copy2(str(target),str(backup))
subprocess.run(['systemctl','--user','stop','for-cat-esp32-bridge.service'],check=True)
temp=target.with_name(target.name+'.forcat-audit-tmp')
assert not temp.exists(),'Unexpected existing staging file'
temp.write_bytes(candidate.read_bytes())
temp.chmod(target.stat().st_mode & 0o777)
os.replace(str(temp),str(target))
subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True)
report={'metadata_tests':'4 cases PASS; null mass/distance preserved',
        'control_methods_unchanged':True,'deployed_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'motor_commands_sent':False}
(r/'bridge_metadata_result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
