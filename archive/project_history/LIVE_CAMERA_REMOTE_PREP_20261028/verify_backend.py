"""Only new camera/security tests and impacted empty-feed-body contract cases."""
from pathlib import Path
import subprocess
import sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
args=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider','-o',
      'pythonpath='+(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson').as_posix()+' '+ROOT.as_posix(),
      str(OUT/'test_live_camera.py'),
      str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/tests/test_release_api_contract.py')+'::test_manual_feed_empty_body_contract',
      str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/tests/test_release_defects.py')+'::test_body_cannot_bypass_feed_bound_with_content_length_zero']
p=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(OUT/'backend_focused.log').write_bytes(p.stdout)
print(p.stdout.decode('utf-8','replace'));raise SystemExit(p.returncode)
