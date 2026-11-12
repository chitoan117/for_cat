"""Read-only Nano inventory. Never opens camera/UART or changes services/DB."""
import importlib.metadata
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
from integrity import read,sha,verify

SERVICES=('for-cat-ai.service','for-cat-api.service','for-cat-esp32-bridge.service')
ENGINE='/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine'
ENGINE_SHA='48fe40017461d2e4edab33c47b30194b84ba7714e32e6d3d2aa4649f5b7471fb'
ENV_KEYS=('SYSTEM_STATE_PROVIDER','CAMERA_PROVIDER','AI_RUNTIME','ESP32_TRANSPORT','AI_SHADOW_MODE')
def query(argv):
    try:
        p=subprocess.run([str(x) for x in argv],capture_output=True,text=True,timeout=20)
        return {'argv':[str(x) for x in argv],'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    except (OSError,subprocess.TimeoutExpired) as e:return {'argv':[str(x) for x in argv],'code':None,'error':type(e).__name__}
def service_info(name,runner=query):
    result=runner(['systemctl','--user','show',name,'--property=ActiveState,SubState,MainPID,FragmentPath,DropInPaths,ExecStartPre,ExecStartPost,ExecStop,ExecStopPost,Type'])
    fields={}
    for line in result.get('stdout','').splitlines():
        if '=' in line:k,v=line.split('=',1);fields[k]=v
    return {'query':result,'fields':fields}
def schema_check(db_path,contract):
    result={'exists':Path(db_path).is_file(),'compatible':False,'conflicts':[],'missing_tables':[]}
    if not result['exists']:return result
    try:
        with sqlite3.connect(Path(db_path).resolve().as_uri()+'?mode=ro',uri=True,timeout=.2) as db:
            db.execute('PRAGMA query_only=ON')
            result['user_version']=db.execute('PRAGMA user_version').fetchone()[0]
            result['python_sqlite_version']=sqlite3.sqlite_version
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table,expected in contract['tables'].items():
                if table not in tables:result['missing_tables'].append(table);continue
                # Names are package-owned, verified manifest entries, not user SQL.
                actual={r[1]:(r[2].upper(),r[5]) for r in db.execute('PRAGMA table_info("'+table+'")')}
                for col in expected['columns']:
                    if actual.get(col['name'])!=(col['type'],col['pk']):result['conflicts'].append(table+'.'+col['name'])
                expected_names={c['name'] for c in expected['columns']}
                for col in db.execute('PRAGMA table_info("'+table+'")'):
                    if col[1] not in expected_names and col[3] and col[4] is None and not col[5]:result['conflicts'].append(table+'.'+col[1]+' EXTRA_REQUIRED_COLUMN')
            result['compatible']=not result['conflicts']
    except sqlite3.Error as e:result['error']=type(e).__name__
    return result
def inventory(release,production,runner=query):
    release=Path(release).resolve();production=Path(production).resolve();manifest=verify(release)
    commands=[['g++','--version']]+[['pkg-config','--modversion',p] for p in ('opencv4','json-c','sqlite3')]
    commands += [['ldconfig','-p'],['fuser','/dev/video0'],['v4l2-ctl','--list-devices'],['id']]
    results=[runner(c) for c in commands]
    libs=results[4].get('stdout','')
    headers={n:any(Path(p).is_file() for p in paths) for n,paths in {
        'tensorrt':['/usr/include/aarch64-linux-gnu/NvInfer.h','/usr/include/NvInfer.h'],
        'cuda':['/usr/local/cuda-10.2/include/cuda_runtime_api.h','/usr/local/cuda/include/cuda_runtime_api.h']}.items()}
    engine=production/'models/tensorrt/yolov8n_320_fp16.engine'
    services={s:service_info(s,runner) for s in SERVICES}
    effective={}
    pid=services[SERVICES[1]]['fields'].get('MainPID','0')
    try:
        raw=Path('/proc/'+str(int(pid))+'/environ').read_bytes().split(b'\0')
        env=dict(p.decode(errors='replace').split('=',1) for p in raw if b'=' in p)
        effective={k:env.get(k) for k in ENV_KEYS}
    except (OSError,ValueError):effective={'status':'UNREADABLE_NOT_ASSUMED'}
    py={n:importlib.util.find_spec(n) is not None for n in ('fastapi','starlette','uvicorn','pydantic')}
    versions={n:importlib.metadata.version(n) for n,ok in py.items() if ok}
    pydantic2=versions.get('pydantic','0').split('.')[0].isdigit() and int(versions.get('pydantic','0').split('.')[0])>=2
    cuda_home=next((p for p in ('/usr/local/cuda-10.2','/usr/local/cuda') if Path(p+'/include/cuda_runtime_api.h').is_file()),None)
    # Plain import is side-effect-free; no create_app or hardware startup.
    env={**os.environ,'PYTHONPATH':str(release/'payload/jetson'),'PYTHONDONTWRITEBYTECODE':'1'}
    imported=None
    try:
        p=subprocess.run([sys.executable,'-B','-c','import app.main, app.ai_frame_contract, app.ai_state'],
                         cwd=release,env=env,capture_output=True,text=True,timeout=30)
        imported={'code':p.returncode,'error':p.stderr[-4000:]}
    except (OSError,subprocess.TimeoutExpired) as e:imported={'error':type(e).__name__}
    mem={}
    try:mem=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapFree:')))
    except OSError:pass
    disk=shutil.disk_usage(release)
    dependencies=all(r.get('code')==0 for r in results[:4]) and all(headers.values()) and 'libnvinfer.so' in libs and 'libcudart.so' in libs
    enough_resources=disk.free>=512*1024*1024 and int(mem.get('MemAvailable','0 kB').split()[0])>=262144
    schema=schema_check(production/'jetson/data/events.db',read(release/'schema/contract.json'))
    return {'kind':'FORCAT_READ_ONLY_PREFLIGHT_V2','architecture':platform.machine(),'python':sys.version.split()[0],
        'python_executable':sys.executable,'python_dependencies':py,'python_versions':versions,'package_import':imported,
        'queries':results,'headers':headers,'cuda_home':cuda_home,'services':services,'effective_backend_env_allowlist':effective,
        'engine_exists':engine.is_file(),'engine_sha256':sha(engine) if engine.is_file() else None,
        'engine_matches_expected':engine.is_file() and sha(engine)==ENGINE_SHA,'engine_contract':'NOT_VERIFIED_UNTIL_PROBE',
        'camera_permissions':{'exists':Path('/dev/video0').exists(),'readable':os.access('/dev/video0',os.R_OK),'writable':os.access('/dev/video0',os.W_OK)},
        'serial_path_observation':{'ttyACM0_exists':Path('/dev/ttyACM0').exists(),'opened':False},
        'memory':mem,'disk_free_bytes':disk.free,'database_schema':schema,
        'minimum_build_resources':enough_resources,
        'python_sqlite_version':sqlite3.sqlite_version,
        'build_preconditions':platform.machine()=='aarch64' and sys.version_info>=(3,11) and sqlite3.sqlite_version_info>=(3,24) and pydantic2 and dependencies and enough_resources and all(py.values()) and imported.get('code')==0,
        'release_manifest_sha256':sha(release/'manifest.json'),'camera_opened':False,'production_changed':False,
        'known_blocker':'HX711_REFERENCE firmware is not diag_current_hardware: valid bridge telemetry=0 until separate supervised acceptance',
        'ARM64_TENSORRT_BUILD_PASS':'NOT_VERIFIED','ESP32_TELEMETRY_PASS':'NOT_VERIFIED','physical_pass':False}
