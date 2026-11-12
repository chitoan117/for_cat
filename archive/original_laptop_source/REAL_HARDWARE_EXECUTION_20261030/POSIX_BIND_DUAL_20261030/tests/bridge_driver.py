"""Owns one TEST Bridge process, never a second tty owner or device process."""
import json
from pathlib import Path
import subprocess


class BridgeDriver:
    def __init__(self, exe, directory, ledger, enabled=True, review_changes=None,dual=False):
        self.directory=Path(directory);self.ledger=ledger
        self.review=dict(scope='OWNER_APPROVED_SOLE_OWNER_FEED_LINK',approved_by='OFFLINE_FIXTURE_ONLY',mode='MOCK',
            maintenance_tx=True,valid_until_unix_ms=1790009000000,producer_id='offline-automation',review_binding='0'*64,
            actuation=True,servo_reviewed=True,power_reviewed=True,calibration_reviewed=True,journal_reviewed=True,closure_reviewed=True)
        self.review.update(review_changes or {})
        self.review_file=self.directory/'review.json';self.review_file.write_text(json.dumps(self.review))
        command=[str(exe),str(self.directory/'bridge.db'),str(ledger.path),str(self.review_file)]+(['--fake-enabled'] if enabled else [])+(['--dual'] if dual else [])
        self.command=command
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.observation=dict(grams=100,healthy=True,calibrated=True,fresh=True,closed=True,closure_available=not dual,connected=True)
        self.last=None;self.drive(1000)

    def drive(self, now, **changes):
        transient={k:changes.pop(k) for k in ('ascii','reboot','short_write') if k in changes}
        self.observation.update(changes)
        message=dict(self.observation,now=now,**transient)
        self.process.stdin.write(json.dumps(message)+'\n');self.process.stdin.flush()
        line=self.process.stdout.readline()
        if not line:raise RuntimeError('Bridge failed: '+self.process.stderr.read())
        self.last=json.loads(line)
        with (self.directory/'bridge_loop_trace.jsonl').open('a') as f:
            f.write(json.dumps(dict(input=message,output=self.last))+'\n')
        return self.last

    def close(self):
        self.process.stdin.close();self.process.wait(timeout=5)
        stderr=self.process.stderr.read();self.process.stdout.close();self.process.stderr.close()
        if self.process.returncode:raise RuntimeError(stderr)
