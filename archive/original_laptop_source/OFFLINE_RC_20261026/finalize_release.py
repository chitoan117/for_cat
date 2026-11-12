"""Validate release docs/static demo and package only offline handoff artifacts."""
import hashlib,json,re,shutil,subprocess,sys,time,urllib.error,urllib.request,zipfile
from pathlib import Path

BASE=Path(__file__).resolve().parent.parent;OUT=BASE/'OFFLINE_RC_20261026';OLD=BASE/'FRONTEND_USER_APP_OFFLINE_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return p.read_text(encoding='utf-8')
r=json.loads(read(OUT/'regression_result.json'));assert r['status']=='PASS'
assert (r['flutter_passed'],r['backend_passed'],r['js_passed'])==(54,393,14)
docs=[BASE/'docs'/n for n in ('PROJECT_STATUS_20261026.md','NEXT_PHYSICAL_SESSION.md','DEMO_SCRIPT_VI.md','DEFENSE_QA_VI.md','ARCHITECTURE_OVERVIEW.md','CURRENT_PROJECT_STATE.md')]+[BASE/'OFFLINE_RELEASE_20261026.md']
for p in docs:
    body=read(p);assert body.endswith('\n'),str(p)+' missing EOF newline'
    assert not any(line.rstrip()!=line for line in body.splitlines()),str(p)+' trailing whitespace'
    assert body.count('```')%2==0,str(p)+' unclosed code fence'
matrix=read(docs[0]);allowed={'PASS','DRY_RUN_PASS','SOFTWARE_READY','NOT_TESTED','BLOCKED','NOT_WIRED','NOT_CALIBRATED','UNKNOWN','PHYSICAL_PASS'}
rows=[line.split('|')[1:-1] for line in matrix.splitlines() if line.startswith('| ') and len(line.split('|'))==7]
items=[]
for row in rows:
    if row[0].strip()=='Hạng mục':continue
    assert all(cell.strip() in allowed for cell in row[1:4]),row
    items.append(row[0].strip())
assert len(items)==25
checklist=read(docs[1]);steps=re.split(r'^## (\d+)\. ',checklist,flags=re.M)
assert [int(steps[i]) for i in range(1,len(steps),2)]==list(range(1,21))
for i in range(2,len(steps),2):
    assert all(key in steps[i] for key in ('Mục tiêu','PASS criteria','FAIL criteria','Lệnh/log cần lưu','Safety note'))
qa=read(docs[3]);questions=re.findall(r'^### (\d+)\. ',qa,flags=re.M)
assert [int(q) for q in questions]==list(range(1,37))
architecture=read(docs[4]);assert architecture.count('```mermaid')==5 and architecture.count('```text')==5
known=json.loads(read(OUT/'frozen_source_sha256.json'))
assert known=={name:sha(Path(r'D:\DA_KT_NC\feeder_demo')/name) for name in known}
provenance=json.loads(read(OLD/'offline_backend_provenance.json'));verified=[]
for name in ('jetson/app/scheduled_worker.py','jetson/app/meal_plans.py','jetson/app/dry_run_requests.py','jetson/app/api/meal_plan_routes.py','jetson/app/hx711_calibration.py'):
    source=provenance['overlays'][name]
    source=Path(source['source']) if isinstance(source,dict) else Path(source)/name
    assert sha(source)==sha(OLD/'verification'/name),name+' changed from checkpoint'
    verified.append(name)
smokes=[]
for mode in ('real','mock'):
    child=subprocess.Popen([sys.executable,str(OUT/'serve_demo.py'),'--mode',mode,'--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
    try:
        line=child.stdout.readline();match=re.search(r'http://127\.0\.0\.1:(\d+)/app',line);assert match,line
        origin='http://127.0.0.1:'+match.group(1)
        def get(path):
            with urllib.request.urlopen(origin+path,timeout=5) as response:return response.read()
        assert b'<base href="/flutter/">' in get('/app?fixture=cat')
        assert len(get('/flutter/main.dart.js'))>100000
        assert json.loads(get('/flutter/forcat_build.json'))['mode']==mode.upper()
        try:get('/api/status')
        except urllib.error.HTTPError as e:assert e.code==404
        else:raise AssertionError('Static demo fabricated backend response')
        request=urllib.request.Request(origin+'/api/feed/preview',data=b'{}',headers={'Content-Type':'application/json'})
        try:urllib.request.urlopen(request,timeout=5)
        except urllib.error.HTTPError as e:assert e.code==501
        else:raise AssertionError('Static demo accepted write endpoint')
        smokes.append({'mode':mode,'static_assets':'PASS','no_backend_404':'PASS','no_write_endpoint_501':'PASS'})
    finally:
        child.terminate();stdout,stderr=child.communicate(timeout=10)
        (OUT/('demo_smoke_'+mode+'.log')).write_text(line+stdout+stderr,encoding='utf-8')
guards={'status':'PASS','status_matrix_rows':25,'checklist_steps':20,'qa_questions':36,'mermaid_ascii_diagrams':5,
        'source_frozen_files':len(known),'checkpoint_modules_unchanged':verified,'static_demo_smoke':smokes,
        'compiled_js_matches_reviewed_screenshots':{m:sha(OUT/('web_'+m)/'main.dart.js')==sha(OLD/('web_'+m)/'main.dart.js') for m in ('real','mock')}}
assert all(guards['compiled_js_matches_reviewed_screenshots'].values()),'New builds differ: inspect before reusing browser screenshots'
(OUT/'release_checks.json').write_text(json.dumps(guards,indent=2),encoding='utf-8')
for p in docs:
    target=OUT/'release_docs'/p.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
files=set(docs)
for folder in ('source_final','web_real','web_mock','release_docs'):
    files.update(p for p in (OUT/folder).rglob('*') if p.is_file())
files.update(p for p in OUT.iterdir() if p.is_file() and p.suffix in ('.py','.json','.log','.md'))
for name in ('source_after_sha256.json','frontend_changes.json','frontend_changes.patch','offline_backend_provenance.json','browser_offline_report.json','BAO_CAO_FRONTEND_OFFLINE.md','COMPLETION.json'):
    files.add(OLD/name)
screens=json.loads(read(OUT/'screenshot_sha256.json'))
for name,checksum in screens.items():
    p=OLD/'screenshots'/name;assert sha(p)==checksum;files.add(p)
manifest={p.relative_to(BASE).as_posix():sha(p) for p in sorted(files)}
assert not any(Path(name).suffix in ('.db','.engine','.onnx','.pt') for name in manifest)
manifest_path=OUT/'release_manifest_sha256.json'
manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8');files.add(manifest_path)
bundle=OUT/'offline_release_candidate_20261026.zip';assert not bundle.exists(),'Keep existing release immutable; inspect before replacing'
with zipfile.ZipFile(bundle,'x',compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):z.write(p,p.relative_to(BASE).as_posix())
with zipfile.ZipFile(bundle) as z:assert z.testzip() is None
bundle.with_suffix('.zip.sha256').write_text(sha(bundle)+'  '+bundle.name+'\n',encoding='ascii')
print(json.dumps({'status':'OFFLINE RELEASE CANDIDATE 2026-10-26 — READY','manifest_files':len(manifest),'bundle_bytes':bundle.stat().st_size,**guards},indent=2,ensure_ascii=False))
