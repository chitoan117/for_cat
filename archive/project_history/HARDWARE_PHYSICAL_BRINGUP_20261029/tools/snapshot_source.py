"""Copy current authoritative Windows firmware; never touches the qualified RC."""
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
KIT=Path(__file__).resolve().parents[1]
UPSTREAM=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    target=KIT/'firmware'
    if target.exists():raise ValueError('snapshot exists; do not overwrite user work')
    target.mkdir()
    for name in ('src','include','test'):shutil.copytree(UPSTREAM/name,target/name)
    shutil.copyfile(UPSTREAM/'platformio.ini',target/'platformio.ini')
    files={p.relative_to(UPSTREAM).as_posix():{'upstream':str(p),'sha256':sha(p)} for name in ('src','include','test') for p in (UPSTREAM/name).rglob('*') if p.is_file()}
    files['platformio.ini']={'upstream':str(UPSTREAM/'platformio.ini'),'sha256':sha(UPSTREAM/'platformio.ini')}
    # Tie headers to the accepted post-Phase4 RC, without modifying that release.
    rc=ROOT/'PRODUCTION_INTEGRATION_20261029/release_candidate_v2'
    prior=json.loads((rc/'manifest.json').read_text())
    for name,meta in prior['files'].items():
        if name.startswith('firmware_include/'):
            rel='include/'+name[len('firmware_include/'):]
            if sha(UPSTREAM/rel)!=meta['sha256']:raise ValueError('authoritative header differs from accepted RC: '+rel)
    data={'kind':'PHYSICAL_KIT_SOURCE_REFERENCE','upstream':str(UPSTREAM),'source_before_kit_changes':files,
          'accepted_rc_manifest_sha256':sha(rc/'manifest.json'),'rc_directory_unchanged':True,
          'remote_source_declared':'/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/stage/firmware/esp32',
          'remote_source_comparison':'NOT_PERFORMED_NO_SSH','board_config_actual_path':'include/board_config.h',
          'physical_pass':False}
    (KIT/'SOURCE_REFERENCE.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print('Copied authoritative source; kit-only edits will be recorded separately')
if __name__=='__main__':main()
