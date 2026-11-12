"""Run specified focused tests, retaining their full log in this session."""
import json
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
names=sys.argv[1:]
if not names or any('/' in n or '\\' in n or not n.startswith('test_') or not n.endswith('.py') for n in names):
    raise SystemExit('Supply local focused test filenames')
p=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',*[str(HERE/n) for n in names]],capture_output=True,timeout=180)
stem='_'.join(Path(n).stem for n in names)
(HERE/(stem+'.log')).write_bytes(p.stdout+p.stderr)
print((p.stdout+p.stderr).decode('utf-8','replace'))
(HERE/(stem+'_result.json')).write_text(json.dumps({'returncode':p.returncode,'physical_pass':False,'tests':names},indent=2)+'\n',encoding='utf-8')
raise SystemExit(p.returncode)
