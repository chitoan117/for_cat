"""Candidate systemd entrypoints. Executed ONLY by supervised future cutover.
State writer acquires the canonical lock and confirms readiness BEFORE camera
producer starts. Either child exiting terminates its peer; systemd owns restart.
"""
import sys
sys.dont_write_bytecode=True
import argparse
import os
from pathlib import Path
import select
import signal
import subprocess
import time
from integrity import absolute,read,sha,verify
from runtime_config import environment

def setup(release,build,private,production):
    release=absolute(str(release));build=absolute(str(build));private=absolute(str(private));production=absolute(str(production))
    verify(release);receipt=read(build/'build.json')
    if receipt.get('arm64_build')!='PASS' or receipt['release_manifest_sha256']!=sha(release/'manifest.json'):raise ValueError('build does not match release')
    for name,digest in receipt['binaries'].items():
        if sha(build/name)!=digest:raise ValueError('binary integrity mismatch')
    env=environment(private,production)
    sys.path.insert(0,str(release/'payload/jetson'))
    return env
def writer(database,ready_fd):
    from app.ai_frame_contract import StateTap,WriterLock,MAX_LINE
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    with WriterLock(database):
        tap=StateTap(database,boot)
        if not tap.disconnected():raise RuntimeError('initial canonical state write failed')
        os.write(ready_fd,b'1');os.close(ready_fd)
        try:
            while True:
                line=sys.stdin.buffer.readline(MAX_LINE+1)
                if not line:break
                if not line.endswith(b'\n'):
                    while line and not line.endswith(b'\n'):line=sys.stdin.buffer.readline(MAX_LINE+1)
                    tap.rejected+=1;continue
                try:tap.accept(line.decode('utf-8').rstrip('\r\n'))
                except UnicodeError:tap.rejected+=1
        finally:tap.disconnected()
    # Bounded diagnostics: one summary, no per-frame images/events/log files.
    print('AI_WRITER_STOP storage_errors='+str(tap.storage_errors)+' rejected='+str(tap.rejected),file=sys.stderr)
def stop_child(child):
    if child and child.poll() is None:
        child.terminate()
        try:child.wait(timeout=3)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=3)
def supervise(release,build,private,production,env):
    owned=subprocess.run(['fuser','/dev/video0'],capture_output=True)
    if owned.returncode!=1 or owned.stderr.strip():raise RuntimeError('camera busy or fuser ownership unavailable')
    data_r,data_w=os.pipe();ready_r,ready_w=os.pipe();adapter=producer=None
    interrupted=[False]
    def stop(*_):interrupted[0]=True
    previous={s:signal.signal(s,stop) for s in (signal.SIGTERM,signal.SIGINT)}
    try:
        argv=[sys.executable,'-B',str(release/'tools/managed_runtime.py'),'writer','--release',str(release),
              '--build',str(build),'--private',str(private),'--production-root',str(production),'--ready-fd',str(ready_w)]
        adapter=subprocess.Popen(argv,stdin=data_r,pass_fds=(ready_w,),env=env)
        os.close(data_r);data_r=None;os.close(ready_w);ready_w=None
        if not select.select([ready_r],[],[],5)[0] or os.read(ready_r,1)!=b'1':raise RuntimeError('sole AI writer not ready')
        producer=subprocess.Popen([str(build/'roi_ai_source'),str(production/'jetson/data/events.db'),'-','/dev/video0'],stdout=data_w,env=env)
        os.close(data_w);data_w=None
        while not interrupted[0] and adapter.poll() is None and producer.poll() is None:time.sleep(.1)
        return 0 if interrupted[0] else 1
    finally:
        stop_child(producer);stop_child(adapter)
        for fd in (data_r,data_w,ready_r,ready_w):
            if fd is not None:os.close(fd)
        for s,handler in previous.items():signal.signal(s,handler)
def main():
    p=argparse.ArgumentParser();p.add_argument('role',choices=('ai','api','writer'))
    for name in ('release','build','private','production-root'):p.add_argument('--'+name,required=True)
    p.add_argument('--ready-fd',type=int);args=p.parse_args()
    release=Path(args.release);build=Path(args.build);private=Path(args.private);production=Path(args.production_root)
    env=setup(release,build,private,production);os.environ.clear();os.environ.update(env)
    if args.role=='writer':writer(production/'jetson/data/events.db',args.ready_fd);return
    if args.role=='ai':raise SystemExit(supervise(release,build,private,production,env))
    from app.main import create_app
    import uvicorn
    app=create_app(db_path=production/'jetson/data/events.db',flutter_web_dir=release/'web/real')
    uvicorn.run(app,host='127.0.0.1',port=8000,proxy_headers=False,workers=1,timeout_graceful_shutdown=5)
if __name__=='__main__':main()
