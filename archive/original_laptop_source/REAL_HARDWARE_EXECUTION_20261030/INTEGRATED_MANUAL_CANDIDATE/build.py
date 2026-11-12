"""Windows ESP32-S3 build only; optional pump variant needs measured owner evidence.
Never invokes upload, Serial, reset, flash or service APIs. Every output is NEW.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1] / 'HARDWARE_PHYSICAL_BRINGUP_20261029'
FW = ROOT / 'firmware'
PIO = Path('C:/Users/chito/.platformio/penv/Scripts/python.exe')
ESPTOOL = Path('C:/Users/chito/.platformio/packages/tool-esptoolpy/esptool.py')
sys.path.insert(0, str(BASE / 'tools'))
from image_layout import partitions, image_header, app_partition

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--label', required=True)
p.add_argument('--pump-observation', type=Path)
a = p.parse_args()
if not a.label.replace('_', '').isalnum():
    p.error('simple NEW label required')
level = -1
observation_sha = None
if a.pump_observation:
    observed = json.loads(a.pump_observation.read_text(encoding='utf-8')).get('USER_OBSERVED', {})
    level = observed.get('f5305s_off_level')
    if type(level) is not int or level not in (0, 1) or observed.get('boot_off_verified') is not True or not observed.get('observer'):
        raise ValueError('actual measured OFF0/1, boot OFF bias verification and observer required')
    observation_sha = sha(a.pump_observation)
profile = 'manual_station_safe' if level == -1 else 'manual_station_reviewed'
out = ROOT / ('build_' + a.label)
out.mkdir()
project = FW
if level != -1:
    project = out / 'conditional_project'
    project.mkdir()
    for folder in ('include', 'src'):
        shutil.copytree(FW / folder, project / folder)
    shutil.copyfile(FW / 'kit_metadata.py', project / 'kit_metadata.py')
    (project / 'platformio.ini').write_text((FW / 'platformio.ini').read_text() +
        '\n[env:manual_station_reviewed]\nbuild_flags = ${env.build_flags} -DMANUAL_PUMP_OFF_LEVEL=' + str(level) + '\n')
result = {'build': 'FAIL', 'profile': profile, 'pump_off_level': level,
          'pump_observation_sha256': observation_sha, 'commands': [],
          'physical_pass': False, 'flash_performed': False, 'APP_FLASH': 'NO_GO'}


def run(argv, label, timeout=120):
    record = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'command': [str(x) for x in argv]}
    q = subprocess.run(record['command'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=timeout, env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'})
    (out / (label + '.log')).write_bytes(q.stdout)
    record.update(exit_code=q.returncode, log=label + '.log')
    result['commands'].append(record)
    if q.returncode:
        raise RuntimeError(label + ' failed; preserve output')
    return q.stdout.decode('utf-8', 'replace')


try:
    result['python'] = run([PIO, '--version'], 'python').strip()
    result['platformio'] = run([PIO, '-m', 'platformio', '--version'], 'platformio').strip()
    run([PIO, '-m', 'platformio', 'run', '--project-dir', project, '-e', profile], 'compile', 1200)
    built = project / '.pio/build' / profile
    meta = json.loads((built / 'flash_layout.json').read_text())
    offset = int(meta['application_offset'], 0)
    table = built / 'partitions.bin'
    layout = partitions(table.read_bytes())
    partition = app_partition(layout, offset)
    assert table.read_bytes() == (BASE / 'artifacts/diag_four_ultrasonic/partitions.bin').read_bytes(), 'partition table changed'
    image = built / 'firmware.bin'
    header = image_header(image.read_bytes()[:24])
    assert header['flash_size_code'] == 4 and image.stat().st_size <= partition['size']
    assert 'BOARD_HAS_PSRAM' not in repr(meta['cppdefines'])
    assert 'FORR_REAL_S3_NO_PSRAM' in repr(meta['cppdefines'])
    assert 'MANUAL_STATION_HOST_TEST' not in repr(meta['cppdefines'])
    data = image.read_bytes()
    assert struct.unpack_from('<I', data, 32)[0] == 0xabcd5432
    secure_version = struct.unpack_from('<I', data, 36)[0]
    run([PIO, ESPTOOL, '--chip', 'esp32s3', 'image-info', image], 'image_info')
    artifacts = out / 'artifacts'
    artifacts.mkdir()
    for name in ('firmware.bin', 'firmware.elf'):
        shutil.copyfile(built / name, artifacts / name)
    result.update(build='VERIFIED_PASS_BUILD_ONLY', image=str(artifacts / 'firmware.bin'),
                  image_bytes=image.stat().st_size, image_sha256=sha(image),
                  image_header=header, secure_version=secure_version,
                  build_app_offset=offset, actual_running_offset='NOT_VERIFIED_NO_FLASH_ADDRESS_AUTHORIZED',
                  partition_table_sha256=sha(table), partitions=layout,
                  application_partition=partition, partition_table_unchanged=True,
                  build_metadata=meta, source_manifest={})
    for path in [project / 'platformio.ini', project / 'kit_metadata.py'] + [p for d in ('src', 'include') for p in (project / d).rglob('*') if p.is_file()]:
        result['source_manifest'][path.relative_to(project).as_posix()] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    # Check all locked snapshot inputs are still unchanged on disk.
    baseline = json.loads((ROOT / 'BASELINE_SNAPSHOT.json').read_text())
    for rel, expected in baseline['files'].items():
        assert sha(Path(baseline['source']) / rel) == expected, rel
    result['locked_baseline_inputs_unchanged'] = len(baseline['files'])
except Exception as e:
    result['error'] = type(e).__name__ + ': ' + str(e)
    raise
finally:
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: result.get(k) for k in ('build', 'profile', 'image', 'image_bytes', 'image_sha256',
      'pump_off_level', 'build_app_offset', 'secure_version', 'partition_table_unchanged', 'APP_FLASH')}, indent=2))
