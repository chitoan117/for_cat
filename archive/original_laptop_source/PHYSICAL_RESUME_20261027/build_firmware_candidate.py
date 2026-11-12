import json,subprocess,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent;PROJ=OUT/'firmware_candidate/esp32';assert PROJ.is_dir()
sys.stdout.reconfigure(encoding='utf-8')
cmd=[r'C:\Users\chito\.platformio\penv\Scripts\python.exe','-m','platformio','run','--project-dir',str(PROJ),'-e','diag_four_ultrasonic']
p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=360)
(OUT/'firmware_candidate/platformio_build.log').write_bytes(p.stdout)
print(p.stdout.decode('utf-8','replace'));raise SystemExit(p.returncode)
