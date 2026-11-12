"""Future approved lease only: bounded RX-only capture, no auto reset or TX.
Opening the UART may still glitch reset lines: this is a device-impacting action.
"""
from __future__ import print_function
import argparse
import json
import os
from pathlib import Path
import sys
import time
import readiness as r
from serial_window import approval

def validate_lease(path,runner=r.command,identity=r.host_identity):
    path=Path(path)
    if (path/'lease_closing.json').exists() or (path/'lease_closed.json').exists():raise ValueError('lease closing/closed')
    v=json.loads((path/'lease_open.json').read_text())
    approval_data=v['approval']
    # Reuse the same validation without persisting or rewriting the approved file.
    if v.get('state')!='SERIAL_RELEASED_FOR_OWNER' or 'boot_capture' not in approval_data.get('allowed_actions',[]):raise ValueError('no boot-capture lease')
    from datetime import datetime,timezone
    expires=datetime.strptime(approval_data['valid_until_utc'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc)>=expires:raise ValueError('lease expired')
    os.kill(int(v['pid']),0) # process existence only, no signal sent
    cur,raw=r.show(r.UNIT,runner);owners,_=r.holders(runner)
    if raw['code'] or cur.get('ActiveState') not in ('inactive','failed') or owners or identity()!=r.PORT:raise ValueError('port/unit identity not ready')
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',choices=('OWNER_APPROVED_BOOT_CAPTURE',))
    p.add_argument('--lease',type=Path);p.add_argument('--seconds',type=int,default=60);a=p.parse_args()
    if not a.execute:
        print(json.dumps({'mode':'PLAN_ONLY','RX_only':True,'automatic_reset':False,'serial_opened':False,
            'future_open_may_reset':True,'APP_FLASH':'NO_GO'}));return
    if sys.platform!='linux' or not a.lease or not 10<=a.seconds<=180:raise ValueError('Linux, active lease and10..180s required')
    validate_lease(a.lease)
    import fcntl
    with (a.lease/'.capture.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        out=r.new_dir(a.lease/('boot_capture_'+str(int(time.time()))))
        r.write_new(out/'capture_context.json',{'created_utc':r.utc(),'by_id':r.BYID,'seconds':a.seconds,
            'auto_reset':False,'RX_only':True,'max_bytes':2097152,'owner_must_observe_current_boot':True})
        import serial # intentionally imported only inside explicit device execution
        total=0;started=time.monotonic()
        with (out/'raw.bin').open('xb') as raw, (out/'chunks.jsonl').open('x') as chunks:
            port=serial.Serial(port=None,baudrate=115200,timeout=.2,exclusive=True)
            try:
                port.dtr=False;port.rts=False;port.port=r.BYID;port.open()
                print('RX capture open. Only an owner-approved normal-boot reset may now be performed; keep GPIO0 normal.')
                while time.monotonic()-started<a.seconds:
                    data=port.read(min(4096,2097152-total))
                    if data:
                        raw.write(data);raw.flush();total+=len(data)
                        chunks.write(json.dumps({'utc':r.utc(),'offset':total-len(data),'bytes':len(data)})+'\n');chunks.flush()
                    if total>=2097152:raise ValueError('capture budget reached; retain raw data')
            finally:port.close()
        r.write_new(out/'result.json',{'bytes':total,'raw_sha256':r.sha(out/'raw.bin'),
            'running_partition':'NOT_AUTO_INFERRED_REVIEW_RAW_CURRENT_BOOT','TX_commands':0,'physical_pass':False})
        print(str(out))

if __name__=='__main__':main()
