"""Source-only fork. HX711/LEDC and their existing dependencies copied unchanged."""
import hashlib,json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'POSIX_BIND_DUAL_20261030/firmware/include'
target=ROOT/'include';target.mkdir()
inputs={}
for p in BASE.rglob('*.h'):
    rel=p.relative_to(BASE)
    if rel.parts[0]=='m4' or p.name in ('board_config.h','current_hardware.h','pins.h','dog_warning_protocol.h','uart_v1.h'):
        out=target/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
        inputs[rel.as_posix()]={'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(ROOT/'BASELINE.json').write_text(json.dumps({'files':inputs,'driver_hx711_modified':False,'device_actions':False},indent=2)+'\n')
print(json.dumps({'fork':str(ROOT),'unchanged_source_headers':len(inputs),'image_built':False}))
