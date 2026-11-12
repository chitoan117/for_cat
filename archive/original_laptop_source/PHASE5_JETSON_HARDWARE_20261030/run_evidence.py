"""Capture one explicit command without shell/password handling; preserve NEW logs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label', required=True)
    p.add_argument('--input', type=Path)
    p.add_argument('--timeout', type=int, default=120)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    if not a.label.replace('_', '').replace('-', '').isalnum():
        p.error('simple unique evidence label required')
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command:
        p.error('command required')
    evidence = ROOT / 'evidence'
    evidence.mkdir(exist_ok=True)
    target = evidence / a.label
    target.mkdir()  # no overwrite, including earlier failed attempts
    data = a.input.read_bytes() if a.input else None
    record = {
        'source': 'ACTUAL_COMMAND_EXECUTION', 'command': command,
        'stdin_file': str(a.input) if a.input else None,
        'stdin_sha256': hashlib.sha256(data).hexdigest() if data is not None else None,
        'started_utc': datetime.now(timezone.utc).isoformat(),
    }
    try:
        q = subprocess.run(command, input=data, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, cwd=ROOT, timeout=a.timeout)
        output, code = q.stdout, q.returncode
    except subprocess.TimeoutExpired as e:
        output, code = (e.stdout or b'') + b'\nLOCAL_COMMAND_TIMEOUT\n', 124
    except OSError as e:
        output, code = (type(e).__name__ + ': ' + str(e)).encode(), 127
    (target / 'output.log').write_bytes(output)
    record.update(finished_utc=datetime.now(timezone.utc).isoformat(), exit_code=code,
                  output_sha256=hashlib.sha256(output).hexdigest())
    (target / 'command.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(output.decode('utf-8', 'replace'))
    print(json.dumps({'evidence': str(target), 'exit_code': code}))
    return code


if __name__ == '__main__':
    sys.exit(main())
