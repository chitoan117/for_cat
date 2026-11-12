"""One-shot offline source snapshot, preserves all prior overnight/qualified files."""
import hashlib
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
KIT=ROOT/'HARDWARE_PHYSICAL_BRINGUP_20261029';WEB=KIT/'web_hardware'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'candidate'
    if out.exists():raise ValueError('candidate already exists; never overwrite review work')
    out.mkdir();records={}
    pairs=[(p,'bridge/'+p.name) for p in (WEB/'bridge_candidate').iterdir() if p.suffix in ('.h','.cpp')]
    pairs += [(WEB/'diagnostics.py','diagnostics.py'),
              (WEB/'flutter/hardware_diagnostics_panel.dart','flutter/hardware_diagnostics_panel.dart'),
              (WEB/'flutter/pubspec.yaml','flutter/pubspec.yaml')]
    for source,rel in pairs:
        target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        records[rel]={'source':str(source),'sha256':sha(source)}
    (HERE/'SOURCE_BASELINE.json').write_text(json.dumps(records,indent=2)+'\n')
    for name in ('fixtures','evidence','tests'):(HERE/name).mkdir(exist_ok=True)
    print(json.dumps({'snapshot_files':len(records),'production_or_locked_files_changed':False}))
if __name__=='__main__':main()
