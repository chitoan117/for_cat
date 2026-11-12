"""Offline-only release verification. No network/device/service operations."""
import datetime,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path

BASE=Path(r'D:\for_cat');SRC=Path(r'D:\DA_KT_NC\feeder_demo')
OLD=BASE/'FRONTEND_USER_APP_OFFLINE_20261026';OUT=BASE/'OFFLINE_RC_20261026';V=OLD/'verification'
assert OUT.is_dir() and V.is_dir()
sys.stdout.reconfigure(encoding='utf-8')
result={'status':'RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':[],
        'scope':'OFFLINE_ONLY','hardware':'NOT RUN — HARDWARE REQUIRED','linux_pty':'NOT RUN — LINUX/NATIVE REQUIRED',
        'ssh':False,'deploy':False,'production_contract_changed':False}
resume='--finish-only' in sys.argv
if resume:
    result=json.loads((OUT/'regression_result.json').read_text(encoding='utf-8'))
    for name in ('flutter_analyze','flutter_tests','flutter_build_real','flutter_build_mock','backend_offline','js_regression'):
        assert any(c['name']==name and c['returncode']==0 for c in result['commands']),name+' must already pass'
    result.pop('error',None);result['status']='RUNNING'
    result['resume_reason']='Only diff harness LF/CRLF warnings and remaining freeze/artifact checks; no application source edits.'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def frozen_frontend():
    known=json.loads((OLD/'source_after_sha256.json').read_text())
    actual={name:sha(SRC/name) for name in known}
    extras=[str(p.relative_to(SRC)) for folder in ('lib','test','web','assets') for p in (SRC/folder).rglob('*') if p.is_file() and p.relative_to(SRC).as_posix() not in known]
    assert actual==known and not extras,'Frontend differs from reviewed checkpoint; audit before release'
    return actual
def protected_sources():
    selected={}
    for folder in ('jetson/app','jetson/device','jetson/ai','ai','models','config','deploy/systemd'):
        root=BASE/folder
        if not root.exists():continue
        for p in root.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.cpp','.h','.json','.service','.conf','.ini','.sh','.engine','.onnx','.pt'):
                selected[p.relative_to(BASE).as_posix()]=sha(p)
    return selected
def run(name,args,cwd=SRC,env=None,allowed=(0,)):
    p=subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    (OUT/(name+'.log')).write_bytes(p.stdout)
    body=p.stdout.decode('utf-8','replace');result['commands'].append({'name':name,'argv':args,'cwd':str(cwd),'returncode':p.returncode})
    print(name+': exit '+str(p.returncode),flush=True)
    assert p.returncode in allowed,body
    return body
try:
    front=frozen_frontend();protected=protected_sources()
    (OUT/'frozen_source_sha256.json').write_text(json.dumps(front,indent=2),encoding='utf-8')
    if resume:
        assert json.loads((OUT/'protected_local_before_sha256.json').read_text())==protected
    else:
        (OUT/'protected_local_before_sha256.json').write_text(json.dumps(protected,indent=2),encoding='utf-8')
    for label,root in (('workspace',BASE),('frontend',SRC)):
        p=subprocess.run(['git','rev-parse','--show-toplevel'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        assert p.returncode!=0,'Unexpected Git worktree; inspect before proceeding'
        (OUT/('git_'+label+'.log')).write_bytes(p.stdout)
    if not resume:
        run('flutter_analyze',[r'D:\dev\flutter\bin\flutter.bat','analyze','--no-pub'])
        text=run('flutter_tests',[r'D:\dev\flutter\bin\flutter.bat','test','--no-pub'])
        result['flutter_passed']=int(re.search(r'\+(\d+): All tests passed!',text).group(1))
    for mode in (() if resume else ('real','mock')):
        run('flutter_build_'+mode,[r'D:\dev\flutter\bin\flutter.bat','build','web','--release','--no-pub','--no-wasm-dry-run','--no-web-resources-cdn','--base-href=/flutter/','--dart-define=FEEDER_MODE='+mode,'--output='+str(OUT/('web_'+mode))])
        marker=json.loads((OLD/('web_'+mode)/'forcat_build.json').read_text(encoding='utf-8'))
        marker['verification']='OFFLINE_RELEASE_CANDIDATE_NOT_DEPLOYED'
        (OUT/('web_'+mode)/'forcat_build.json').write_text(json.dumps(marker,indent=2,ensure_ascii=False),encoding='utf-8')
        result['build_'+mode]='PASS'
    env={**os.environ,'PYTHONPATH':str(V/'jetson')+os.pathsep+str(V),'PYTHONDONTWRITEBYTECODE':'1'}
    if not resume:
        text=run('backend_offline',[sys.executable,'-m','pytest','jetson/tests','-q','-ra','-k','not test_worker_request_is_consumed_by_existing_cpp_arbiter_on_synthetic_pty'],cwd=V,env=env)
        result['backend_passed']=int(re.search(r'(\d+) passed',text).group(1))
        result['backend_deselected']=int(re.search(r'(\d+) deselected',text).group(1))
        js=BASE/'SCHEDULED_WORKER_20261026/web_regression_source/jetson/tests/web/feed_preview.test.cjs'
        text=run('js_regression',['node','--test','--test-reporter=tap',str(js)],cwd=js.parents[3])
        result['js_passed']=int(re.search(r'# pass (\d+)',text).group(1));assert '# fail 0' in text
    for name in front:
        target=OUT/'source_final'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/name,target)
    text=run('frontend_diff_check',['git','diff','--no-index','--check','--',str(OLD/'frontend_original'),str(OUT/'source_final')],cwd=BASE,allowed=(0,1))
    lines=text.splitlines()
    expected_warning=re.compile(r"^warning: in the working copy of '.+', LF will be replaced by CRLF the next time Git touches it$")
    diagnostics=[line for line in lines if line.strip() and not expected_warning.fullmatch(line)]
    assert not diagnostics,'Whitespace/diff-check diagnostics require review: '+str(diagnostics)
    result['diff_line_ending_warnings']=sum(bool(expected_warning.fullmatch(line)) for line in lines)
    assert frozen_frontend()==front and protected_sources()==protected,'Frozen/protected source changed'
    (OUT/'protected_local_after_sha256.json').write_text(json.dumps(protected_sources(),indent=2),encoding='utf-8')
    browser=json.loads((OLD/'browser_offline_report.json').read_text(encoding='utf-8'))
    assert browser['status']=='PASS' and not browser['external_attempts'] and not browser['runtime_errors']
    assert len(browser['screens'])==36
    shots={s['name']+'.png':sha(OLD/'screenshots'/(s['name']+'.png')) for s in browser['screens']}
    (OUT/'screenshot_sha256.json').write_text(json.dumps(shots,indent=2),encoding='utf-8')
    result.update(screenshots=36,screenshots_scope='INHERITED_REVIEWED_IDENTICAL_SOURCE_NOT_RECAPTURED',source_freeze='PASS',protected_local_sources='UNCHANGED',diff_check='PASS')
    sys.path.insert(0,str(V/'jetson'))
    from app.frontend_assets import resolve_flutter_frontend
    assert resolve_flutter_frontend(OUT/'web_real')==(OUT/'web_real').resolve()
    try:resolve_flutter_frontend(OUT/'web_mock')
    except ValueError:pass
    else:raise AssertionError('MOCK passed REAL artifact guard')
    result['artifact_guards']='PASS'
    result['status']='PASS'
except Exception as e:
    result['status']='FAIL';result['error']=str(e);raise
finally:
    result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (OUT/'regression_result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='commands'},indent=2,ensure_ascii=False))
