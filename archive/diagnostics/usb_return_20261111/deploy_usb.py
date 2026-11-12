"""Owner-authorized USB migration while the old UART link is unavailable."""
from pathlib import Path
from contextlib import closing
import hashlib,json,os,sqlite3,struct,subprocess,time,zlib,serial
R=Path(__file__).resolve().parent;ROOT=Path('/home/toan/for_cat/jetson');DB=ROOT/'data/events.db'
USB=Path('/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00')
BRIDGE=ROOT/'tools/fc_live_bridge.py'
DROP=Path.home()/'.config/systemd/user/for-cat-esp32-bridge.service.d/uart.conf'
TOOL='/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/flash_tool/bin/esptool.py'
OLD=Path('/home/toan/for_cat/evidence/water55_20261111/esp32.ino.bin').read_bytes()
META=json.loads((R/'integrity.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
def service(action,*units):subprocess.run(['systemctl','--user',action,*units],check=True,timeout=20)
def snapshot():
    with closing(sqlite3.connect(DB,timeout=2)) as db:return json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
def wait_status(predicate,timeout=15):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        s=snapshot()
        if 0<=time.monotonic()*1000-s['updated_monotonic_ms']<2500 and predicate(s):return s
        time.sleep(.2)
    raise RuntimeError('Fresh USB bridge status not observed')
def run(label,args):
    with (R/(label+'.log')).open('w') as log:
        p=subprocess.run([TOOL,'--chip','esp32s3','--port',str(USB.resolve()),'--baud','921600','--before','default-reset','--after','no-reset']+args,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    assert p.returncode==0,(label,(R/(label+'.log')).read_text()[-1200:])
    print(label+': PASS',flush=True)
def boot_usb_stopped():
    port=serial.Serial(None,115200,timeout=.1,write_timeout=.5,rtscts=False,dsrdtr=False)
    port.dtr=False;port.rts=False;port.port=str(USB.resolve());port.open()
    lines=[];pending=bytearray();frame=None;stopped=False;position=None
    with port:
        port.rts=True;time.sleep(.1);port.rts=False
        end=time.monotonic()+17;last=0
        while time.monotonic()<end:
            if time.monotonic()-last>.4:
                port.write(b'0\npump_auto off\npump_off\njetson_ping\nservo_position\nmode\nhx_diag\n');last=time.monotonic()
            pending.extend(port.read(4096))
            while b'\n' in pending:
                raw,_,tail=pending.partition(b'\n');pending=bytearray(tail)
                line=raw.decode('utf8',errors='replace').strip();lines.append(line)
                if 'EXIT 0' in line:stopped=True
                if 'SERVO ESTIMATE=' in line and 'moving=0' in line:position=line
                if line.startswith('{'):
                    try:
                        value=json.loads(line)
                        if value.get('type')=='status' and value.get('demo_exited') is True:frame=value
                    except ValueError:pass
            if stopped and frame and position:break
            assert len(pending)<16384
    (R/'boot_usb.log').write_text('\n'.join(lines)+'\n')
    assert stopped and frame and position,'No stopped app ACK/telemetry over USB'
    (R/'boot_usb_frame.json').write_text(json.dumps(frame,indent=2))
    assert frame.get('pir_configured') is False
    assert frame['pump_auto_enabled'] is False and frame['pump_auto_running'] is False
    assert abs(frame['pump_on_cm']-5.7)<.001 and abs(frame['pump_off_cm']-5.5)<.001
    return frame
def queue(commands):
    p=Path('/tmp/for_cat_cmd.txt');assert not p.exists(),'Command inbox occupied'
    tmp=Path('/tmp/usb_return_%s.txt'%os.getpid());tmp.write_text(commands+'\n')
    try:os.link(tmp,p)
    finally:tmp.unlink()
assert USB.exists() and USB.resolve().is_char_device(),'Programming USB absent'
assert sha(OLD)==META['before_app'] and sha(BRIDGE.read_bytes())==META['bridge_before']
assert sha((R/'fc_live_bridge.py').read_bytes())==META['bridge_after']
assert sha((R/'esp32.ino.bin').read_bytes())==(R/'app.sha256').read_text().strip()
assert not (R/'before_flash.bin').exists(),'Already attempted; inspect evidence'
cached=snapshot();(R/'cached_before.json').write_text(json.dumps(cached,indent=2))
(R/'before_bridge.py').write_bytes(BRIDGE.read_bytes())
if DROP.exists():(R/'before_uart.conf').write_bytes(DROP.read_bytes())
service('stop','for-cat-api.service','for-cat-esp32-bridge.service')
wrote=False;changed=False
try:
    assert subprocess.run(['fuser',str(USB.resolve())],capture_output=True).returncode==1,'USB in use'
    with closing(sqlite3.connect(DB,timeout=2)) as db:
        assert db.execute('SELECT count(*) FROM feed_dry_run_requests WHERE decision IS NULL').fetchone()[0]==0,'Pending feeding requests need review'
    inbox=Path('/tmp/for_cat_cmd.txt')
    if inbox.exists():inbox.rename(R/'pending_cmd_before_switch.txt')
    run('backup_flash',['read-flash','0','0x150000',str(R/'before_flash.bin')])
    raw=(R/'before_flash.bin').read_bytes()
    assert len(raw)==0x150000 and raw[0x10000:0x10000+len(OLD)]==OLD,'Actual image differs from current581 baseline'
    assert raw[0x8000:0x8c00]==(R/'esp32.ino.partitions.bin').read_bytes()
    seq=[]
    for off in (0xe000,0xf000):
        entry=raw[off:off+32];seq.append(struct.unpack_from('<I',entry)[0])
        assert struct.unpack_from('<I',entry,24)[0]==0xffffffff and struct.unpack_from('<I',entry,28)[0]==zlib.crc32(entry[:4],0xffffffff)
    assert seq==[1,0]
    (R/'nvs_before.bin').write_bytes(raw[0x9000:0xe000]);wrote=True
    run('write_app',['write-flash','0x10000',str(R/'esp32.ino.bin')])
    run('verify_app',['verify-flash','0x10000',str(R/'esp32.ino.bin')])
    run('read_nvs',['read-flash','0x9000','0x5000',str(R/'nvs_after.bin')])
    assert (R/'nvs_before.bin').read_bytes()==(R/'nvs_after.bin').read_bytes(),'NVS changed during flash'
    frame=boot_usb_stopped()
    for key in ('tare_counts','grams_per_count'):
        assert abs(frame[key]-cached['telemetry']['fc_live'][key])<1e-8,key
    changed=True;BRIDGE.write_bytes((R/'fc_live_bridge.py').read_bytes())
    DROP.parent.mkdir(parents=True,exist_ok=True);DROP.write_text('[Service]\nEnvironment="FORCAT_ESP32_PORT='+str(USB)+'"\n')
    service('daemon-reload')
    queue('0\nbackup_on\nmode\npump_status')
    service('start','for-cat-esp32-bridge.service')
    after=wait_status(lambda s:s['device']==str(USB) and s['telemetry']['fc_live'].get('demo_exited') is True)
    fc=after['telemetry']['fc_live']
    assert fc['backup_enabled'] is True and fc['pump_auto_enabled'] is False
    result={'app_sha256':sha((R/'esp32.ino.bin').read_bytes()),'bridge_sha256':sha(BRIDGE.read_bytes()),'usb_bidirectional':True,'port':str(USB),'baud':115200,'app_readback_verified':True,'nvs_byte_preserved':True,'calibration_preserved':True,'feeding_paused':True,'water_enabled':False,'pump_enable_sent':False,'actuator_test_sent':False,'old_uart_link_was_unavailable':True}
    (R/'usb_after.json').write_text(json.dumps(after,indent=2));(R/'flash_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
except BaseException:
    service('stop','for-cat-esp32-bridge.service')
    if changed:
        BRIDGE.write_bytes((R/'before_bridge.py').read_bytes())
        if (R/'before_uart.conf').exists():DROP.write_bytes((R/'before_uart.conf').read_bytes())
        else:DROP.unlink(missing_ok=True)
        service('daemon-reload')
    if wrote:
        (R/'restore_old_app.bin').write_bytes(OLD)
        run('restore_old_app',['write-flash','0x10000',str(R/'restore_old_app.bin')])
        run('verify_restore',['verify-flash','0x10000',str(R/'restore_old_app.bin')])
    service('start','for-cat-esp32-bridge.service');raise
finally:service('start','for-cat-api.service')
