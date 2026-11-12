import os,subprocess,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
OUT=Path(r'D:\for_cat\FRONTEND_USER_APP_OFFLINE_20261026');V=OUT/'verification';assert V.is_dir()
cmd=[sys.executable,'-m','pytest','jetson/tests','-q','-ra','-k','not test_worker_request_is_consumed_by_existing_cpp_arbiter_on_synthetic_pty']
p=subprocess.run(cmd,cwd=V,env={**os.environ,'PYTHONPATH':str(V/'jetson')+os.pathsep+str(V)},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
(OUT/'backend_offline.log').write_bytes(p.stdout);print(p.stdout.decode('utf-8','replace'));raise SystemExit(p.returncode)
