"""New source fork only. No rebuild/overwrite of either locked APP image."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent
BRIDGE=PARENT/'OFFLINE_BRIDGE_SERVO_PREP_20261030/bridge'
AUTO=PARENT/'AUTONOMOUS_INTEGRATION_20261030'
MANUAL=PARENT/'INTEGRATED_MANUAL_CANDIDATE'
inputs={}
for dest,source in (('bridge',BRIDGE),('backend',AUTO/'backend')):
    target=ROOT/dest;target.mkdir()
    for p in source.iterdir():
        if p.is_file() and p.suffix in ('.h','.cpp','.py'):
            shutil.copyfile(p,target/p.name);inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
fw=ROOT/'firmware';fw.mkdir()
for folder in ('include','src','test'):
    for p in (MANUAL/'firmware'/folder).rglob('*'):
        if p.is_file():
            rel=p.relative_to(MANUAL/'firmware');target=fw/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(p,target);inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('feed_link.h',):
    p=AUTO/'firmware/include'/name;shutil.copyfile(p,fw/'include'/name);inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('dispense_bench.h','servo_bench.h'):
    p=AUTO/'firmware/include/m4'/name;shutil.copyfile(p,fw/'include/m4'/name);inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
p=AUTO/'bridge/sole_owner_feed_link.h';shutil.copyfile(p,ROOT/'bridge'/p.name);inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copyfile(MANUAL/'firmware/kit_metadata.py',fw/'kit_metadata.py')
shutil.copyfile(MANUAL/'manual_console.py',ROOT/'manual_console_dual.py')
images={str(MANUAL/'build_safe_txatomic/artifacts/firmware.bin'):'77faf09775e55731b08c511ac852273b9839963c081ebe924035f8f9aecaac93',
        str(AUTO/'firmware_build_inert_macro_fixed/artifacts/firmware.bin'):'867707f7b260224b04a797d05142615d51ac83bfef22e6011dba573f2aeb8882'}
for p,digest in images.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest
(ROOT/'BASELINE.json').write_text(json.dumps(dict(inputs=inputs,locked_images=images),indent=2)+'\n')
print(json.dumps(dict(workspace=str(ROOT),source_inputs=len(inputs),locked_images_match=2)))
