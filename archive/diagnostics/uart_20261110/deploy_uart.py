"""Guarded app-only UART migration. No feed/pump/physical-position commands."""
from pathlib import Path
from contextlib import closing
import hashlib,json,os,sqlite3,struct,subprocess,sys,time,zlib
import serial

R=Path('/home/toan/for_cat/evidence/uart_20261110')
ROOT=Path('/home/toan/for_cat/jetson')
BRIDGE=ROOT/'tools/fc_live_bridge.py'
DROP=Path.home()/'.config/systemd/user/for-cat-esp32-bridge.service.d/uart.conf'
USB=Path('/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00')
UART='/dev/ttyTHS1'
DB=ROOT/'data/events.db'
TOOL='/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/flash_tool/bin/esptool.py'
META=json.loads((R/'integrity_prebuild.json').read_text())
OLD=Path('/home/toan/for_cat/evidence/portion_settle_20261110/esp32.ino.bin').read_bytes()
sha=lambda x:hashlib.sha256(x).hexdigest()

def service(action,*names):
    subprocess.run(['systemctl','--user',action,*names],check=True,timeout=20)

def snapshot():
    with closing(sqlite3.connect(DB,timeout=2)) as db:
        row=db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()
        return json.loads(row[0])

def queue(commands):
    inbox=Path('/tmp/for_cat_cmd.txt')
    deadline=time.monotonic()+8
    while inbox.exists() and time.monotonic()<deadline: time.sleep(.1)
    assert not inbox.exists(),'Pending command inbox; no overwrite permitted'
    temp=Path('/tmp/forcat_uart_%s.txt'%os.getpid())
    temp.write_text(commands+'\n')
    try:os.link(temp,inbox)
    finally:temp.unlink()

def wait_status(predicate,timeout=12):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        s=snapshot()
        if 0<=time.monotonic()*1000-s['updated_monotonic_ms']<2500 and predicate(s):return s
        time.sleep(.2)
    raise RuntimeError('Fresh expected device telemetry not observed')

def run(label,args):
    base=[TOOL,'--chip','esp32s3','--port',str(USB.resolve()),'--baud','921600','--before','default-reset','--after','no-reset']
    with (R/(label+'.log')).open('w') as f:
        p=subprocess.run(base+args,stdout=f,stderr=subprocess.STDOUT,timeout=180)
    if p.returncode:raise RuntimeError(label+': '+(R/(label+'.log')).read_text()[-1600:])
    print(label+': PASS',flush=True)

def open_serial(port):
    s=serial.Serial(None,115200,timeout=.1,write_timeout=.5,dsrdtr=False,rtscts=False)
    s.dtr=False;s.rts=False;s.port=port;s.open()
    return s

def boot_stopped(new):
    # New application traffic is UART1; USB is retained only for the reset.
    endpoint=UART if new else str(USB.resolve())
    s=open_serial(endpoint)
    try:
        if new:
            with open_serial(str(USB.resolve())) as reset:
                reset.rts=True;time.sleep(.1);reset.rts=False
        else:
            s.rts=True;time.sleep(.1);s.rts=False
        start=time.monotonic();last_send=0;lines=[];stopped=False;position=None;frame=None
        # Fail/rollback before the independent 30-second backup boot grace.
        while time.monotonic()-start<16:
            now=time.monotonic()
            if now-last_send>.4:
                s.write(b'0\njetson_ping\nservo_position\nmode\nhx_diag\n');last_send=now
            line=s.readline().decode('utf8',errors='replace').strip()
            if not line:continue
            lines.append(line)
            if 'EXIT 0' in line:stopped=True
            if 'SERVO ESTIMATE=' in line and 'moving=0' in line and 'feedback=NONE' in line:position=line
            if line.startswith('{'):
                try:
                    msg=json.loads(line)
                    if msg.get('demo_exited') is True:frame=msg
                except ValueError:pass
            if stopped and position and frame:break
        (R/('boot_new.log' if new else 'boot_restore.log')).write_text('\n'.join(lines)+'\n')
        assert stopped and position and frame,'Stopped app not verified on '+endpoint
        (R/('uart_boot_frame.json' if new else 'restore_boot_frame.json')).write_text(json.dumps(frame,indent=2))
        print(json.dumps({'endpoint':endpoint,'stop_ack':stopped,'position':position,'bidirectional_telemetry':True}),flush=True)
        return frame
    finally:s.close()

def check_calibration(before,after):
    for k in ('tare_counts','grams_per_count'):
        assert abs(before[k]-after[k])<1e-8,(k,before[k],after[k])

def main():
    assert sha(OLD)==META['before_app']
    assert sha(BRIDGE.read_bytes())==META['bridge_before'],'Live bridge changed since staging'
    assert sha((R/'fc_live_bridge.py').read_bytes())==META['bridge_after']
    assert sha((R/'esp32.ino.bin').read_bytes())==(R/'app.sha256').read_text().strip()
    assert USB.exists() and USB.resolve().is_char_device(),'Programming USB absent'
    assert Path(UART).is_char_device() and os.access(UART,os.R_OK|os.W_OK)
    assert subprocess.run(['systemctl','is-active','--quiet','nvgetty.service']).returncode!=0
    assert subprocess.run(['fuser',UART],capture_output=True).returncode==1,'UART still owned'
    assert not DROP.exists(),'Existing UART override needs explicit reconciliation'
    assert not (R/'before_flash.bin').exists(),'Migration already attempted; inspect evidence first'
    pre=wait_status(lambda s:True)
    fc=pre['telemetry']['fc_live']
    assert not fc.get('dog_running') and fc.get('meal_phase') not in ('CAPTURE','OBSERVE')
    assert fc['bench_state'] in ('READY','CAT DONE','DONE','CAT FAULT*','EXIT0','MASS OK GATE?'),fc['bench_state']
    with closing(sqlite3.connect(DB,timeout=2)) as db:
        assert db.execute('SELECT count(*) FROM feed_dry_run_requests WHERE decision IS NULL').fetchone()[0]==0
    (R/'preflight.json').write_text(json.dumps(pre,indent=2))
    (R/'before_bridge.py').write_bytes(BRIDGE.read_bytes())
    (R/'before_units.txt').write_text(subprocess.check_output(['systemctl','--user','cat','for-cat-esp32-bridge.service'],text=True))
    queue('0')
    wait_status(lambda s:s['telemetry']['fc_live'].get('demo_exited') is True)
    service('stop','for-cat-api.service','for-cat-esp32-bridge.service')
    flash_started=False;new_verified=False;bridge_changed=False
    try:
        assert subprocess.run(['fuser',str(USB.resolve())],capture_output=True).returncode==1
        run('read_backup',['read-flash','0','0x150000',str(R/'before_flash.bin')])
        b=(R/'before_flash.bin').read_bytes()
        assert len(b)==0x150000 and b[0x10000:0x10000+len(OLD)]==OLD,'Actual app differs from baseline'
        assert b[0x8000:0x8c00]==(R/'esp32.ino.partitions.bin').read_bytes()
        seq=[]
        for off in (0xe000,0xf000):
            entry=b[off:off+32];n=struct.unpack_from('<I',entry)[0]
            assert struct.unpack_from('<I',entry,24)[0]==0xffffffff
            assert struct.unpack_from('<I',entry,28)[0]==zlib.crc32(entry[:4],0xffffffff)
            seq.append(n)
        assert seq==[1,0],seq
        (R/'nvs_before.bin').write_bytes(b[0x9000:0xe000])
        flash_started=True
        run('write_uart_app',['write-flash','0x10000',str(R/'esp32.ino.bin')])
        run('verify_uart_app',['verify-flash','0x10000',str(R/'esp32.ino.bin')])
        run('read_nvs_after',['read-flash','0x9000','0x5000',str(R/'nvs_after.bin')])
        assert (R/'nvs_before.bin').read_bytes()==(R/'nvs_after.bin').read_bytes(),'NVS changed during programming'
        frame=boot_stopped(True)
        check_calibration(fc,frame)
        new_verified=True
        # Only activate Jetson routing after actual bidirectional UART succeeds.
        bridge_changed=True
        BRIDGE.write_bytes((R/'fc_live_bridge.py').read_bytes())
        DROP.parent.mkdir(parents=True,exist_ok=True)
        DROP.write_bytes((R/'bridge-uart.conf').read_bytes())
        service('daemon-reload')
        queue('0\nservo_position\nmode\nhx_diag')
        service('start','for-cat-esp32-bridge.service')
        activated=time.monotonic()*1000
        live=wait_status(lambda s:s['device']==UART and s['updated_monotonic_ms']>activated and s['telemetry']['fc_live'].get('demo_exited') is True)
        check_calibration(fc,live['telemetry']['fc_live'])
        (R/'live_uart_usb_connected.json').write_text(json.dumps(live,indent=2))
        result={'app_sha256':sha((R/'esp32.ino.bin').read_bytes()),'bridge_sha256':sha(BRIDGE.read_bytes()),'app_readback_verified':True,'nvs_byte_identical':True,'uart_bidirectional_verified':True,'port':UART,'rx_gpio':41,'tx_gpio':42,'baud':115200,'feeding_paused':True,'actuator_test_commands_sent':False,'external_power_usb_removed_test_pending':True}
        (R/'flash_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    except BaseException:
        # Restore original app and bridge together; never leave mismatched ports.
        service('stop','for-cat-esp32-bridge.service')
        if bridge_changed:
            BRIDGE.write_bytes((R/'before_bridge.py').read_bytes())
            DROP.unlink(missing_ok=True);service('daemon-reload')
        if flash_started:
            (R/'restore_old_app.bin').write_bytes(OLD)
            run('rollback_old_app',['write-flash','0x10000',str(R/'restore_old_app.bin')])
            run('verify_rollback',['verify-flash','0x10000',str(R/'restore_old_app.bin')])
        boot_stopped(False)
        queue('0')
        service('start','for-cat-esp32-bridge.service')
        raise
    finally:
        service('start','for-cat-api.service')
    print('UART migration verified with USB retained for programming. Feeding remains paused pending separate-power check.',flush=True)

if __name__=='__main__':main()
