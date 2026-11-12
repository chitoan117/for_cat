"""Complete new ESP32 test application from unchanged HX/LEDC and CR logic."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'CONTINUOUS_SERVO_HX711_20261030'
fw=ROOT/'firmware';fw.mkdir();shutil.copytree(BASE/'include',fw/'include')
inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'include').rglob('*') if p.is_file()}
source=ROOT.parent/'POSIX_BIND_DUAL_20261030/firmware'
for name in ('serial_port.h',):
    shutil.copyfile(source/'include'/name,fw/'include'/name);inputs[str(source/'include'/name)]=hashlib.sha256((source/'include'/name).read_bytes()).hexdigest()
shutil.copyfile(source/'kit_metadata.py',fw/'kit_metadata.py')
shutil.copytree(source/'test',fw/'test')
(ROOT/'BASELINE.json').write_text(json.dumps(dict(inputs=inputs,hx711_driver_modified=False),indent=2)+'\n')
print('Created complete source fork; no image/Serial/device operation.')
