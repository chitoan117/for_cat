"""Only the new portable preview queue/stamp adapter, no camera SDK or old tests."""
from pathlib import Path
import subprocess
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
(OUT/'native').mkdir(exist_ok=True)
args=[ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++14','-O1','-Wall','-Wextra','-Wpedantic','-Werror',
      '-I'+str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device'),
      '-I'+str(ROOT/'OFFLINE_REVIEW_20261024/project/jetson/ai'),OUT/'test_preview_queue.cpp','-o',OUT/'native/test_preview_queue.exe']
for cmd,log in ((args,'preview_compile.log'),([OUT/'native/test_preview_queue.exe'],'preview_test.log')):
 p=subprocess.run([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
 (OUT/log).write_bytes(p.stdout)
 if p.returncode:raise RuntimeError(p.stdout.decode('utf-8','replace'))
print(p.stdout.decode('utf-8','replace'))
