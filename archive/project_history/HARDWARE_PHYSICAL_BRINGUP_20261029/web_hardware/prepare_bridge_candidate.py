"""Copy only; candidate is separate from production source and accepted RCv2."""
import json
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'tools'))
from image_layout import sha
def main():
    upstream=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device'
    target=HERE/'bridge_candidate'
    if target.exists():raise ValueError('candidate exists; do not overwrite')
    shutil.copytree(upstream,target)
    data={p.relative_to(upstream).as_posix():{'source':str(p),'sha256':sha(p)} for p in upstream.rglob('*') if p.is_file()}
    (HERE/'bridge_source_reference.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print('Prepared separate bridge candidate source; no build/deploy/serial operation')
if __name__=='__main__':main()
