"""Sole UART owner for the isolated fc-cr-test-1 firmware (not old Bridge)."""
import argparse
import binascii
import datetime
import json
import math
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time

def frame(boot, seq, device_ms, op, *args):
    payload=' '.join(map(str,('FC1',boot,seq,device_ms,op,*args))).encode('ascii')
    return payload+b'*'+f'{binascii.crc_hqx(payload,0xffff):04X}\n'.encode()

def inference(data, now_ns, previous):
    """Same-host monotonic timestamp, original inference seq, no refreshed replay."""
    obj=json.loads(data)
    if obj.get('schema')!='fc-cat-1':raise ValueError('AI schema')
    seq=obj['source_seq']; captured=obj['captured_monotonic_ns']; confidence=obj['confidence']
    if type(seq) is not int or not previous<seq<=0xffffffff:raise ValueError('AI sequence')
    if type(captured) is not int or not 0<=now_ns-captured<=500_000_000:raise ValueError('AI age')
    if type(confidence) not in (int,float) or not math.isfinite(confidence) or not 0<=confidence<=1:raise ValueError('AI confidence')
    if obj['label'] not in ('CAT','NONE','DOG','OTHER'):raise ValueError('AI label')
    return seq,(now_ns-captured)//1_000_000,round(confidence*1000),int(obj['label']=='CAT')

def ensure_free(port):
    active=subprocess.run(['systemctl','--user','is-active','for-cat-esp32-bridge.service'],capture_output=True,text=True)
    if active.returncode==0:raise RuntimeError('Bridge is active; UART has not been handed over')
    if active.returncode not in (3,4):raise RuntimeError('Cannot determine Bridge ownership')
    owners=subprocess.run(['fuser',os.path.realpath(port)],capture_output=True,text=True)
    if owners.returncode!=1:raise RuntimeError('UART busy or fuser check failed: '+owners.stdout+owners.stderr)

def main():
    import serial
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port',default='/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00')
    ap.add_argument('--ai-socket',required=True,help='new private Unix datagram socket path')
    ap.add_argument('--log',required=True,help='new JSONL log; existing files refused')
    a=ap.parse_args()
    if sys.platform!='linux':raise RuntimeError('Live sender requires Linux Jetson')
    if Path(a.ai_socket).exists():raise RuntimeError('AI socket path already exists; not replacing it')
    ensure_free(a.port)
    # Never truncate previous meal evidence. Open/log/socket before taking UART.
    with open(a.log,'x',encoding='utf-8') as log, socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as ai:
        ai.bind(a.ai_socket);os.chmod(a.ai_socket,0o600);ai.setblocking(False)
        port=serial.Serial(port=None,baudrate=115200,timeout=0,write_timeout=0,exclusive=True)
        port.dtr=False;port.rts=False;port.port=a.port
        try:
            port.open() # Opening still may reset some adapters/boards: see README.
            status=None;status_at=0;seq=0;source_seq=0;last_hb=0;pending={};rx=bytearray();last_state=None
            def write(data):
                if port.write(data)!=len(data):raise RuntimeError('Partial UART write: outcome unknown; no retry')
            def send(op,*args):
                nonlocal seq
                if status is None or time.monotonic()-status_at>0.5:raise ValueError('No fresh device status')
                if seq>=0xffffffff:raise RuntimeError('Sequence exhausted; stop/reconcile')
                seq+=1;write(frame(status['boot'],seq,status['ms'],op,*args))
                if op not in ('HB','CAT'):pending[seq]=op
            print('Commands: inspect closed | arm A | arm B | stop | quit. No motion on startup.')
            while True:
                readable,_,_=select.select([port.fileno(),ai,sys.stdin],[],[],0.02)
                if port.fileno() in readable:
                    data=port.read(4096)
                    if not data:raise RuntimeError('UART disconnected')
                    rx.extend(data)
                    if len(rx)>16384:raise RuntimeError('Unbounded device line')
                    while b'\n' in rx:
                        raw,_,tail=rx.partition(b'\n');rx=bytearray(tail)
                        try:obj=json.loads(raw)
                        except (ValueError,UnicodeError):continue
                        log.write(json.dumps(dict(received_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),host_monotonic_ns=time.monotonic_ns(),device=obj))+'\n');log.flush()
                        if obj.get('type')=='status' and obj.get('schema')=='fc-cr-test-1':
                            if status and obj['boot']!=status['boot']:
                                raise RuntimeError('Device reboot: pending outcome needs inspection; no re-arm')
                            status=obj;status_at=time.monotonic();seq=max(seq,obj['seq'])
                            if obj['state']!=last_state:
                                last_state=obj['state'];print(json.dumps(obj))
                        elif obj.get('type')=='ack' and obj.get('seq') in pending:
                            print(pending.pop(obj['seq']),json.dumps(obj))
                if ai in readable:
                    # Bounded draining; source age and source seq reject queued/replayed frames.
                    for _ in range(16):
                        try:data=ai.recv(2048)
                        except BlockingIOError:break
                        try:
                            values=inference(data,time.monotonic_ns(),source_seq)
                            send('CAT',*values);source_seq=values[0]
                        except (ValueError,KeyError,TypeError) as exc:print('AI frame rejected:',exc,file=sys.stderr)
                if sys.stdin in readable:
                    command=sys.stdin.readline()
                    if not command:break
                    words=command.strip().split()
                    try:
                        if words==['quit']:break
                        if words==['stop']:write(b'STOP\n')
                        elif words==['inspect','closed']:send('INSPECT','CLOSED')
                        elif words in (['arm','A'],['arm','B']):send('ARM',words[1])
                        else:print('Unknown command')
                    except ValueError as exc:print(exc,file=sys.stderr)
                if time.monotonic()-last_hb>=0.3:
                    try:send('HB');last_hb=time.monotonic()
                    except ValueError:pass
        finally:
            if port.is_open:
                try:port.write(b'\nSTOP\n')
                except (OSError,serial.SerialException):pass
                port.close()
            os.unlink(a.ai_socket)

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:pass
    except Exception as exc:print(str(exc),file=sys.stderr);sys.exit(1)
