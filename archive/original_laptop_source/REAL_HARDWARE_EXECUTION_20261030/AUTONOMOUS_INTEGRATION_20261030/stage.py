"""New integration sandbox only. Copy source, never old binaries/caches or devices."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[1]
MANUAL = ROOT.parent/'INTEGRATED_MANUAL_CANDIDATE'
R2 = WS/'CANDIDATE_R2_OFFLINE_HARDENING_20261030'
fw = ROOT/'firmware'; fw.mkdir()
inputs = {}
for folder in ('include', 'test'):
    for p in sorted((MANUAL/'firmware'/folder).rglob('*')):
        if p.is_file():
            rel = p.relative_to(MANUAL/'firmware'); target=fw/rel
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,target)
            inputs[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('dispense_bench.h','servo_bench.h'):
    p=R2/'candidate/firmware/include/m4'/name
    shutil.copyfile(p,fw/'include/m4'/name); inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copyfile(MANUAL/'firmware/kit_metadata.py',fw/'kit_metadata.py')
backend=ROOT/'backend'; backend.mkdir()
p=R2/'candidate/backend/app/serial_link/protocol.py'
text=p.read_text().replace('from app.config import MAX_PAYLOAD','MAX_PAYLOAD = 256')
text=text.replace('    NACK = 7','    NACK = 7\n    HELLO = 64\n    CONFIGURE = 65\n    ARM = 66\n    FEED = 67\n    HEARTBEAT = 68\n    ABORT = 69\n    QUERY = 70\n    DOG = 71\n    RESULT = 72\n    CAPABILITIES = 73\n    INSPECT = 74')
(backend/'wire.py').write_text(text);inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('history_model.dart','real_backend.dart'):
    p=Path('D:/DA_KT_NC/feeder_demo/lib')/name
    inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
shared=ROOT/'flutter_shared';shutil.copytree(R2/'candidate/flutter_shared',shared)
for p in (R2/'candidate/flutter_shared').rglob('*'):
    if p.is_file():inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT/'BASELINE.json').write_text(json.dumps({'inputs':inputs,'manual_image':str(MANUAL/'build_safe_txatomic/artifacts/firmware.bin'),
    'manual_sha256':'77faf09775e55731b08c511ac852273b9839963c081ebe924035f8f9aecaac93'},indent=2)+'\n')
print(json.dumps({'sandbox':str(ROOT),'source_inputs':len(inputs),'devices_opened':False}))
