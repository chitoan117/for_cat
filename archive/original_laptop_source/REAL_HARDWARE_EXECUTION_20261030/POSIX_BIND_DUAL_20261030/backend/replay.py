"""File/process transport for real C++ code, ALWAYS MOCK provenance. No tty API."""
import json
from pathlib import Path
import subprocess


class WorkerTransport:
    source = 'MOCK'

    def __init__(self, executable, *, enabled=True, trace=None):
        self.process = subprocess.Popen([str(executable)] + (['--fake-enabled'] if enabled else []),
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.observation = dict(grams=100, healthy=True, calibrated=True, fresh=True,
                                calibration_id=7, closure_available=True, closed=True)
        self.last = None
        self.sent = []
        self.drop_ack = False
        self.drop_ack_for = None
        self.trace = Path(trace) if trace else None

    def _step(self, data):
        self.process.stdin.write(json.dumps(data, allow_nan=False)+'\n'); self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('C++ worker failed: ' + self.process.stderr.read())
        self.last = json.loads(line)
        if self.trace:
            with self.trace.open('a') as f:
                f.write(json.dumps({'input': data, 'device': self.last, 'source': 'MOCK', 'physical_pass': False})+'\n')
        packets = [bytes.fromhex(x) for x in self.last['packets']]
        packets = [x for x in packets if not (x[7] == 6 and (self.drop_ack or (self.drop_ack_for is not None and len(x)>24 and x[23] == self.drop_ack_for)))]
        return packets

    def exchange(self, data, now):
        self.sent.append(bytes(data))
        return self._step(dict(self.observation, now=now, hex=data.hex()))

    def tick(self, now, **changes):
        self.observation.update(changes)
        return self._step(dict(self.observation, now=now))

    def reboot(self, now):
        return self._step(dict(self.observation, now=now, reboot=True))

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=5)
        if self.process.returncode:
            raise RuntimeError(self.process.stderr.read())
        self.process.stdout.close(); self.process.stderr.close()
