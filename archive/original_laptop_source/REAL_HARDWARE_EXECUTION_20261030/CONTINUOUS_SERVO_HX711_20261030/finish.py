"""Record source integrity only; no suite/firmware/device operation."""
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;P=ROOT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tests=json.loads((ROOT/'tests_sensor_edges_fixed/result.json').read_text())
assert tests['status']=='PASS_OFFLINE' and tests['new_case_count']==21
baseline=json.loads((ROOT/'BASELINE.json').read_text())
for rel,meta in baseline['files'].items():
    assert sha(ROOT/'include'/rel)==meta['sha256'] and sha(Path(meta['source']))==meta['sha256'],rel
images={P/'INTEGRATED_MANUAL_CANDIDATE/build_safe_txatomic/artifacts/firmware.bin':'77faf09775e55731b08c511ac852273b9839963c081ebe924035f8f9aecaac93',
 P/'AUTONOMOUS_INTEGRATION_20261030/firmware_build_inert_macro_fixed/artifacts/firmware.bin':'867707f7b260224b04a797d05142615d51ac83bfef22e6011dba573f2aeb8882',
 P/'POSIX_BIND_DUAL_20261030/dual_build_global_stop/artifacts/firmware.bin':'01c056e04679c6a182a0c8475b151400706455137c9ea329c9600b145e706232'}
for path,digest in images.items():assert sha(path)==digest,path
for rel,digest in tests['source_sha256'].items():assert sha(ROOT/rel)==digest,rel
result=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS_OFFLINE',new_logic_cases=21,
    hx711_driver_unchanged=True,copied_headers_unchanged=len(baseline['files']),legacy_images_unchanged=3,
    firmware_image_built=False,flashed=False,loads_activated=False,old_suites_rerun=False,physical_pass=False,
    position_feedback_default='UNAVAILABLE',unverified_supervised_outcome='MEASURED_NEEDS_OWNER_CONFIRMATION',
    selected_evidence='tests_sensor_edges_fixed/result.json',
    changed_code={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'include/continuous_servo.h',ROOT/'include/continuous_dispense.h',ROOT/'include/continuous_hx_adapter.h')})
with (ROOT/'RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
