"""Checksum-guarded backend-only update. Default is comparison, not application.

No serial/camera/service/flash operations. Git index is read/snapshotted, never
staged/restored/reset. Unexpected target edits cause an all-files preflight abort.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile

ALLOWED = {
    'jetson/app/device_state.py', 'jetson/app/ai_state.py', 'jetson/app/system_state.py',
    'jetson/tests/test_device_state_api.py', 'jetson/tests/test_system_state.py',
    'jetson/tests/test_state_cache_resilience.py',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def git(project, *args):
    result = subprocess.run(['git', *args], cwd=project, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=20,
                            env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    if result.returncode:
        raise RuntimeError('git inspection failed: ' + result.stderr.decode('utf-8', 'replace'))
    return result.stdout


def inside(root, path):
    return path == root or root in path.parents


def inspect(project, bundle):
    project, bundle = Path(project).resolve(), Path(bundle).resolve()
    if not (project / '.git').exists() or not (project / 'jetson/app/main.py').is_file():
        raise RuntimeError('not the expected project checkout')
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or set(manifest.get('files', {})) != ALLOWED:
        raise RuntimeError('unexpected update scope/schema')
    statuses = {}
    for name, record in manifest['files'].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('unsafe update path')
        target, payload = project / name, bundle / 'payload' / name
        if target.is_symlink() or payload.is_symlink() or not inside(project, target.parent.resolve()):
            raise RuntimeError('symlink/external update target: ' + name)
        if not target.parent.is_dir():
            raise RuntimeError('expected source parent missing: ' + name)
        if sha(payload) != record['after_sha256']:
            raise RuntimeError('payload checksum mismatch: ' + name)
        actual = sha(target)
        if target.exists() and not target.is_file():
            raise RuntimeError('target is not a source file: ' + name)
        if actual == record['after_sha256']:
            statuses[name] = 'ALREADY_APPLIED'
        elif actual == record['before_sha256']:
            statuses[name] = 'READY'
        else:
            raise RuntimeError('source conflict; preserve user work and compare manually: ' + name)
    return project, bundle, manifest, statuses


def atomic_write(path, data, mode=None):
    descriptor, temporary = tempfile.mkstemp(prefix='.offline-update-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply_updates(project, bundle, *, apply=False, writer=atomic_write):
    project, bundle, manifest, statuses = inspect(project, bundle)
    index_name = Path(git(project, 'rev-parse', '--git-path', 'index').decode().strip())
    index = index_name if index_name.is_absolute() else project / index_name
    index_before = sha(index)
    result = {'mode': 'APPLY' if apply else 'CHECK_ONLY', 'files': statuses,
              'head': git(project, 'rev-parse', '--verify', 'HEAD').decode().strip() if
                      subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=project,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0 else 'UNBORN',
              'git_index_before': index_before, 'services_restarted': False,
              'hardware_operations': False, 'linux_validation': 'PENDING_JETSON'}
    if not apply or all(value == 'ALREADY_APPLIED' for value in statuses.values()):
        return result
    evidence_parent = project / 'evidence'
    if not inside(project, evidence_parent.resolve()):
        raise RuntimeError('external evidence directory; abort before source writes')
    evidence_parent.mkdir(exist_ok=True)
    evidence = evidence_parent / ('offline_source_update_' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    evidence.mkdir()
    (evidence / 'git_status.before.txt').write_bytes(git(project, 'status', '--short'))
    (evidence / 'git_diff.before.patch').write_bytes(git(project, 'diff', '--binary'))
    (evidence / 'git_staged.before.patch').write_bytes(git(project, 'diff', '--cached', '--binary'))
    originals, applied = {}, []
    for name, value in statuses.items():
        if value != 'READY':
            continue
        path = project / name
        originals[name] = (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) if path.exists() else (None, None)
        if path.exists():
            saved = evidence / 'originals' / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
    try:
        for name, value in statuses.items():
            if value != 'READY':
                continue
            target = project / name
            if sha(target) != manifest['files'][name]['before_sha256']:
                raise RuntimeError('source changed concurrently: ' + name)
            writer(target, (bundle / 'payload' / name).read_bytes(), originals[name][1])
            applied.append(name)
        if sha(index) != index_before:
            raise RuntimeError('Git index changed concurrently; user index is not overwritten')
    except Exception as error:
        conflicts = []
        for name in reversed(applied):
            target = project / name
            if sha(target) != manifest['files'][name]['after_sha256']:
                conflicts.append(name)
                continue  # preserve any concurrent user edit, keep backup for manual merge
            data, mode = originals[name]
            if data is None:
                target.unlink()  # only a file absent before THIS transaction
            else:
                atomic_write(target, data, mode)
        (evidence / 'failed.json').write_text(json.dumps({'error': str(error), 'concurrent_edits_preserved': conflicts}, indent=2), encoding='utf-8')
        raise
    result['evidence'] = str(evidence)
    result['git_index_after'] = sha(index)
    result['applied_files'] = applied
    (evidence / 'receipt.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        result = apply_updates(args.project, Path(__file__).resolve().parent, apply=args.apply)
        print(json.dumps(result, indent=2))
        print('No hardware/service action. Linux tests and operator-controlled restart remain required.')
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(2, 'SOURCE_UPDATE_ABORTED: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
