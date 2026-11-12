from pathlib import Path
import hashlib,json,subprocess,shutil,py_compile,time,urllib.request,os
r=Path(__file__).parent;base=Path('/home/toan/for_cat/jetson')
plan=json.loads((r/'backend_plan.json').read_text())
files={'main.py':base/'app/main.py','system_state.py':base/'app/system_state.py',
 'fc_live_bridge.py':base/'tools/fc_live_bridge.py','meal_observation_routes.py':base/'app/api/meal_observation_routes.py'}
backup=r/'backend_before_install';backup.mkdir(exist_ok=False)
for name,path in files.items():
    expected=plan[name]['before']
    assert (hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None)==expected,'Changed live source '+name
    assert hashlib.sha256((r/'backend'/name).read_bytes()).hexdigest()==plan[name]['after']
    py_compile.compile(str(r/'backend'/name),doraise=True)
    if path.exists():shutil.copy2(path,backup/name)
units=['for-cat-api.service','for-cat-esp32-bridge.service']
subprocess.run(['systemctl','--user','stop']+units,check=True)
try:
    for name,path in files.items():shutil.copy2(r/'backend'/name,path)
    # STOP is handled before AI by the existing single serial owner after reset.
    pending=Path('/tmp/for_cat_cmd.txt')
    if pending.exists():
        assert pending.read_text().strip()=='0','Unexpected pending command; not overwritten'
    else:
        p=Path('/tmp/forcat_meal_backend_stop_'+str(os.getpid())+'.txt');p.write_text('0\n')
        try:os.link(str(p),str(pending))
        finally:p.unlink()
    subprocess.run(['systemctl','--user','start']+units,check=True)
    last=None
    for _ in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/api/meal-observation',timeout=2) as f:last=json.load(f)
            if last.get('live',{}).get('meal_schema_version')==2:break
        except Exception:pass
        time.sleep(.5)
    else:raise AssertionError('New API/fresh schema2 telemetry not ready: '+repr(last))
    fc=last['live'];assert abs(fc['tare_counts']-(-699593))<.001,'Scale tare changed'
    assert abs(fc['grams_per_count']-(-.000945082600219258))<1e-12,'Scale factor changed'
    (r/'backend_deployment.json').write_text(json.dumps({'healthy':True,'live':last,'source_hashes':plan},indent=2))
    print(json.dumps({'healthy':True,'phase':fc['meal_phase'],'selected_food':fc['selected_food'],'tare_counts':fc['tare_counts'],'records':len(last['records'])}),flush=True)
except BaseException:
    subprocess.run(['systemctl','--user','stop']+units)
    for name,path in files.items():
        if (backup/name).exists():shutil.copy2(backup/name,path)
        elif path.exists():path.unlink()
    subprocess.run(['systemctl','--user','start']+units)
    raise
