import datetime,difflib,hashlib,json,shutil,sys,zipfile
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
SRC=Path(r'D:\DA_KT_NC\feeder_demo');OUT=Path(r'D:\for_cat\FRONTEND_USER_APP_OFFLINE_20261026');assert OUT.is_dir()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
browser=json.loads((OUT/'browser_offline_report.json').read_text(encoding='utf-8'))
assert browser['status']=='PASS' and len(browser['screens'])==36
assert not browser['external_attempts'] and not browser['runtime_errors']
assert '+54: All tests passed!' in (OUT/'flutter_tests.log').read_text(encoding='utf-8')
assert 'No issues found!' in (OUT/'flutter_analyze.log').read_text(encoding='utf-8')
assert '393 passed, 1 deselected' in (OUT/'backend_offline.log').read_text(encoding='utf-8')
for mode in ('real','mock'):assert 'Built' in (OUT/('flutter_release_'+mode+'.log')).read_text(encoding='utf-8')
files=[p for folder in ('lib','test','web','assets') for p in (SRC/folder).rglob('*') if p.is_file()]+[SRC/n for n in ('pubspec.yaml','pubspec.lock','analysis_options.yaml','README.md')]
after={p.relative_to(SRC).as_posix():digest(p) for p in files};before=json.loads((OUT/'frontend_before_sha256.json').read_text())
changes={name:('ADDED' if name not in before else 'MODIFIED') for name,sha in after.items() if before.get(name)!=sha}
changes.update({name:'DELETED' for name in before if name not in after});assert 'DELETED' not in changes.values()
(OUT/'source_after_sha256.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
(OUT/'frontend_changes.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
patch=[]
for name in sorted(changes):
 if Path(name).suffix not in ('.dart','.yaml','.json','.html','.md'):continue
 original=OUT/'frontend_original'/name
 old=original.read_text(encoding='utf-8').splitlines(keepends=True) if original.exists() else []
 new=(SRC/name).read_text(encoding='utf-8').splitlines(keepends=True)
 patch.extend(difflib.unified_diff(old,new,fromfile='before/'+name,tofile='after/'+name))
(OUT/'frontend_changes.patch').write_text(''.join(patch),encoding='utf-8')
for p in files:
 target=OUT/'source_final'/p.relative_to(SRC);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
for mode in ('real','mock'):
 marker={'mode':mode.upper(),'base_href':'/flutter/','target_grams':35,'actuator_execution':False,'actual_dispensed_grams':None,
  'features':['OFFLINE_USER_APP_REVIEW','SCHEDULED_DRY_RUN_WORKER_STATUS','HX711_READ_ONLY_METADATA'],
  'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verification':'OFFLINE_ONLY_NOT_DEPLOYED',
  'flutter_tests_passed':54,'backend_offline_tests_passed':393,'physical':'NOT RUN — HARDWARE REQUIRED','source_sha256':after}
 (OUT/('web_'+mode)/'forcat_build.json').write_text(json.dumps(marker,indent=2,ensure_ascii=False),encoding='utf-8')
sys.path.insert(0,str(OUT/'verification/jetson'))
from app.frontend_assets import resolve_flutter_frontend
assert resolve_flutter_frontend(OUT/'web_real')== (OUT/'web_real').resolve()
try:resolve_flutter_frontend(OUT/'web_mock')
except ValueError:pass
else:raise AssertionError('MOCK artifact must not satisfy existing REAL artifact guard')
repro=OUT/'reproduce';repro.mkdir(exist_ok=True)
TMP=Path(r'C:\Users\chito\AppData\Local\Temp\opencode')
for name in ('prepare_offline_user_app_20261026.py','complete_offline_test_inputs_20261026.py','run_backend_offline_user_app_20261026.py','verify_build_offline_user_app_20261026.py','capture_offline_user_app_20261026.cjs','audit_user_app_font_20261026.py','finalize_offline_user_app_20261026.py'):
 shutil.copy2(TMP/name,repro/name)
for mode in ('real','mock'):
 assets={p.relative_to(OUT/('web_'+mode)).as_posix():digest(p) for p in (OUT/('web_'+mode)).rglob('*') if p.is_file()}
 (OUT/('web_'+mode+'_sha256.json')).write_text(json.dumps(assets,indent=2),encoding='utf-8')
summary={'scope':'OFFLINE_FRONTEND_USER_APP','flutter_tests':54,'backend_offline_passed':393,'backend_linux_pty_not_run':1,
 'archived_web_client_passed':14,'browser_screens':36,'browser_external_requests':0,'browser_runtime_errors':0,
 'real_artifact_guard':'PASS','mock_rejected_by_real_artifact_guard':'PASS','source_changes':changes,
 'backend_production_contract_changes':False,'ssh':False,'deploy':False,'flash':False,'physical':'NOT RUN — HARDWARE REQUIRED'}
(OUT/'COMPLETION.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
bundle=OUT/'frontend_offline_bundle.zip';assert not bundle.exists()
with zipfile.ZipFile(bundle,'x',compression=zipfile.ZIP_DEFLATED) as z:
 for folder in ('source_final','web_real','web_mock','reproduce'):
  for p in (OUT/folder).rglob('*'):
   if p.is_file():z.write(p,p.relative_to(OUT).as_posix())
 for name in ('BAO_CAO_FRONTEND_OFFLINE.md','COMPLETION.json','source_after_sha256.json','frontend_changes.json','frontend_changes.patch','offline_backend_provenance.json'):
  z.write(OUT/name,name)
(OUT/'frontend_offline_bundle.zip.sha256').write_text(digest(bundle)+'  '+bundle.name+'\n',encoding='ascii')
print(json.dumps({'changes':len(changes),'source_files':len(after),'bundle_bytes':bundle.stat().st_size,'screenshots':36,'artifact_guards':'PASS'},indent=2))
