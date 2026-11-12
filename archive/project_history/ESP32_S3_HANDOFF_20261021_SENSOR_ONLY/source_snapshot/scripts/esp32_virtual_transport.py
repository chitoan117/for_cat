"""Bounded process-pipe virtual serial. Both device and Jetson wire parsers stay real."""
import json
import queue
import struct
import subprocess
import threading
import time
from pathlib import Path


class FirmwareDevice:
    def __init__(self, binary, state_file=None):
        self.binary = str(Path(binary).resolve())
        self.state_file = state_file
        self.lock = threading.RLock()
        self.late = None  # one bounded late frame across virtual reconnect
        self.start()

    def start(self):
        self.mailbox = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.proc = subprocess.Popen([self.binary] + ([str(self.state_file)] if self.state_file else []),
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def reader():
            try:
                while not self.stop.is_set():
                    header = self.proc.stdout.read(4)
                    if len(header) != 4:
                        raise ConnectionError("firmware process disconnected")
                    size, = struct.unpack("<I", header)
                    if size > 65536:
                        raise ConnectionError("firmware reply exceeded bound")
                    data = self.proc.stdout.read(size)
                    if len(data) != size:
                        raise ConnectionError("truncated host bridge reply")
                    self.mailbox.put(data, timeout=2)
            except (OSError, ValueError, ConnectionError, queue.Full) as exc:
                try:
                    self.mailbox.put_nowait(ConnectionError(str(exc)))
                except queue.Full:
                    pass

        self.thread = threading.Thread(target=reader, daemon=True)
        self.thread.start()

    def rpc(self, op, body=b""):
        if len(body) > 8192:
            raise ValueError("host RPC body exceeds bound")
        with self.lock:
            try:
                self.proc.stdin.write(struct.pack("<BH", op, len(body)) + body)
                self.proc.stdin.flush()
                result = self.mailbox.get(timeout=3)
            except (OSError, ValueError, queue.Empty) as exc:
                raise ConnectionError("firmware host process unavailable") from exc
            if isinstance(result, Exception):
                raise result
            return result

    def feed(self, data, advance=0):
        if len(data) > 4096 or not 0 <= advance <= 10000:
            raise ValueError("virtual input bound")
        return self.rpc(1, struct.pack("<I", advance) + data)

    def tick(self, milliseconds):
        return self.rpc(2, struct.pack("<I", milliseconds))

    def fault(self, name, value):
        self.rpc(4, (name + " " + str(value)).encode("ascii"))

    def stats(self):
        return json.loads(self.rpc(3))

    def close(self):
        self.stop.set()
        if self.proc.poll() is None:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)
        for pipe in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            pipe.close()
        self.thread.join(timeout=3)

    def restart(self):
        self.close()
        self.start()


class ProcessSerialPort:
    def __init__(self, device, tx=lambda value: value, rx=lambda value: value,
                 chunk=64, delay=0, silence=False, disconnect=False, **options):
        self.device, self.tx, self.rx = device, tx, rx
        if not 1 <= chunk <= 4096 or not 0 <= delay <= 5:
            raise ValueError("virtual transport bounds")
        self.chunk, self.delay, self.silence, self.disconnect = chunk, delay, silence, disconnect
        self.closed = False
        self.buffer = bytearray()
        self.ready = 0

    def reset_input_buffer(self):
        self.buffer.clear()

    def write(self, raw):
        if self.closed or self.disconnect:
            raise OSError("injected disconnect")
        data = self.tx(raw)
        reply = bytearray()
        for start in range(0, len(data), self.chunk):
            reply.extend(self.device.feed(data[start:start + self.chunk]))
        if self.silence:
            return len(raw)
        reply = self.rx(bytes(reply))
        if self.device.late is not None and time.monotonic() >= self.device.late[1]:
            reply = self.device.late[0] + reply
            self.device.late = None
        if len(reply) + len(self.buffer) > 8192:
            raise ValueError("virtual status queue bound")
        self.buffer.extend(reply)
        self.ready = time.monotonic() + self.delay
        if self.delay:
            self.device.late = (bytes(self.buffer), self.ready)
        return len(raw)

    def read(self, count):
        if self.closed or self.disconnect:
            raise OSError("injected disconnect")
        if time.monotonic() < self.ready or not self.buffer:
            time.sleep(0.001)
            return b""
        part = bytes(self.buffer[:min(count, self.chunk)])
        del self.buffer[:len(part)]
        if not self.buffer and self.delay:
            self.device.late = None
        return part

    def close(self):
        self.closed = True  # link closure is not a device reboot


def factory(device, **faults):
    return lambda **options: ProcessSerialPort(device, **faults, **options)
