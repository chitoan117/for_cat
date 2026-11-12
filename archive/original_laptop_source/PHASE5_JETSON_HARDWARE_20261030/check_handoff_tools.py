"""Static compatibility and no-side-effect PLAN checks for NEW handoff tools only."""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
for name in ('owner_arm64.py', 'http_readonly_audit.py'):
    ast.parse((ROOT / name).read_text(encoding='utf-8'), feature_version=(3, 6))
    with tempfile.TemporaryDirectory() as temporary:
        cwd = Path(temporary)
        q = subprocess.run([sys.executable, '-B', str(ROOT / name)], cwd=cwd,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        assert q.returncode == 0, q.stderr
        assert json.loads(q.stdout)['mode'] == 'PLAN_ONLY'
        assert list(cwd.iterdir()) == []

spec = importlib.util.spec_from_file_location('owner_handoff_test', ROOT / 'owner_arm64.py')
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
with patch.object(sys, 'argv', ['owner_arm64.py', '--execute', 'BUILD_AND_FILE_REPLAY_ONLY']), \
     patch.object(owner.platform, 'system', return_value='Windows'), \
     patch.object(owner.subprocess, 'run', side_effect=AssertionError('must not execute')), \
     patch.object(owner.Path, 'mkdir', side_effect=AssertionError('must not write')):
    try:
        owner.main()
        raise AssertionError('non-ARM64 execute accepted')
    except ValueError as e:
        assert 'actual Linux ARM64' in str(e)

for bad_base in ('http://user:secret@127.0.0.1:8000', 'http://example.com', 'http://127.0.0.1:8000/api/feed/manual'):
    q = subprocess.run([sys.executable, '-B', str(ROOT / 'http_readonly_audit.py'), '--base', bad_base],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    assert q.returncode == 2
print(json.dumps({'status': 'SIMULATION_PASS', 'scope': 'NEW_HANDOFF_TOOL_GUARDS_ONLY',
                  'Python36_grammar': 'PASS', 'PLAN_no_local_outputs': 2,
                  'non_target_execution_refused_before_commands_or_mkdir': True,
                  'unsafe_HTTP_origins_refused': 3, 'old_Windows_suites_rerun': 0,
                  'ARM64_runtime': 'NOT_RUN', 'hardware_actions': False}, indent=2))
