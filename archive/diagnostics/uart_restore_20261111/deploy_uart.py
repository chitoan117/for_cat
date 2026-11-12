"""Restore matching UART firmware + Jetson port; keep reserve web/calibration intact."""
from pathlib import Path
from contextlib import closing
import hashlib,json,os,py_compile,sqlite3,struct,subprocess,time,zlib,serial
R=Path(__file__).resolve().parent;ROOT=Path('/home/toan/for_cat/jetson');DB=ROOT/'data/events.db'
USB=Path('/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00');UART='/dev/ttyTHS1'
BRIDGE=ROOT/'tools/fc_live_bridge.py';DROP=Path.home()/'.config/systemd/user/for-cat-esp32-bridge.service.d/uart.conf'
OLD=Path('/home/toan/for_cat/evidence/usb_return_20261111/esp32.ino.bin').read_bytes()
TOOL='/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/flash_tool/bin/esptool.py'
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
    raise RuntimeError('No fresh matching UART bridge status')
def queue(commands):
    p=Path('/tmp/for_cat_cmd.txt');assert not p.exists(),'Command inbox occupied'
    tmp=Path('/tmp/uart_restore_%s.txt'%os.getpid());tmp.write_text(commands+'\n')
    try:os.link(tmp,p)
    finally:tmp.unlink()
def open_serial(port):
    if port.startswith('/dev/ttyTHS'):return serial.Serial(port,115200,timeout=.1,write_timeout=.5,rtscts=False,dsrdtr=False)
    s=serial.Serial(None,115200,timeout=.1,write_timeout=.5,rtscts=False,dsrdtr=False)
    s.dtr=False;s.rts=False;s.port=port;s.open();return s
def run(label,args):
    with (R/(label+'.log')).open('w') as log:
        proc=subprocess.run([TOOL,'--chip','esp32s3','--port',str(USB.resolve()),'--baud','921600','--before','default-reset','--after','no-reset']+args,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    assert proc.returncode==0,(label,(R/(label+'.log')).read_text()[-1400:])
    print(label+': PASS',flush=True)
def boot_stopped():
    frame=None;position=None;stop=False;lines=[];pending=bytearray()
    with open_serial(UART) as s:
        with open_serial(str(USB.resolve())) as reset:reset.rts=True;time.sleep(.1);reset.rts=False
        end=time.monotonic()+16;last=0
        while time.monotonic()<end:
            if time.monotonic()-last>.4:
                s.write(b'0\npump_auto off\npump_off\njetson_ping\nservo_position\nmode\nhx_diag\n');last=time.monotonic()
            pending.extend(s.read(4096))
            while b'\n' in pending:
                raw,_,tail=pending.partition(b'\n');pending=bytearray(tail)
                line=raw.decode('utf8',errors='replace').strip();lines.append(line)
                if 'EXIT 0' in line:stop=True
                if 'SERVO ESTIMATE=' in line and 'moving=0' in line:position=line
                if line.startswith('{'):
                    try:
                        obj=json.loads(line)
                        if obj.get('type')=='status' and obj.get('demo_exited') is True:frame=obj
                    except ValueError:pass
            if stop and position and frame:break
            assert len(pending)<16384
    (R/'boot_uart.log').write_text('\n'.join(lines)+'\n')
    assert stop and position and frame,'No UART stop ACK/status; inspect physical TX/RX/GND'
    (R/'boot_uart_frame.json').write_text(json.dumps(frame,indent=2))
    assert frame['pump_auto_enabled'] is False and frame['pump_auto_running'] is False
    assert abs(frame['pump_on_cm']-5.7)<.001 and abs(frame['pump_off_cm']-5.5)<.001
    return frame
assert USB.exists() and USB.resolve().is_char_device(),'Programming USB absent'
assert sha(OLD)==META['before_app'] and sha(BRIDGE.read_bytes())==META['bridge_before'],'Baseline changed'
assert sha((R/'esp32.ino.bin').read_bytes())==META['after_app']==(R/'app.sha256').read_text().strip()
assert sha((R/'fc_live_bridge.py').read_bytes())==META['bridge_after']
py_compile.compile(str(R/'fc_live_bridge.py'),doraise=True)
assert not (R/'before_flash.bin').exists(),'Flash already attempted; inspect evidence'
cached=snapshot();(R/'cached_before.json').write_text(json.dumps(cached,indent=2))
(R/'before_bridge.py').write_bytes(BRIDGE.read_bytes());(R/'before_uart.conf').write_bytes(DROP.read_bytes())
service('stop','for-cat-api.service','for-cat-esp32-bridge.service')
wrote=False;changed=False
try:
    for port in (UART,str(USB.resolve())):assert subprocess.run(['fuser',port],capture_output=True).returncode==1,'Serial port owned'
    with closing(sqlite3.connect(DB,timeout=2)) as db:assert db.execute('SELECT count(*) FROM feed_dry_run_requests WHERE decision IS NULL').fetchone()[0]==0,'Pending feed requests'
    inbox=Path('/tmp/for_cat_cmd.txt')
    if inbox.exists():inbox.rename(R/'pending_cmd_before_switch.txt')
    run('backup_flash',['read-flash','0','0x150000',str(R/'before_flash.bin')])
    raw=(R/'before_flash.bin').read_bytes();assert len(raw)==0x150000
    assert raw[0x10000:0x10000+len(OLD)]==OLD,'Actual app differs from current USB image'
    assert raw[0x8000:0x8c00]==(R/'esp32.ino.partitions.bin').read_bytes()
    seq=[]
    for off in (0xe000,0xf000):
        entry=raw[off:off+32];seq.append(struct.unpack_from('<I',entry)[0])
        assert struct.unpack_from('<I',entry,24)[0]==0xffffffff and struct.unpack_from('<I',entry,28)[0]==zlib.crc32(entry[:4],0xffffffff)
    assert seq==[1,0]
    (R/'nvs_before.bin').write_bytes(raw[0x9000:0xe000]);wrote=True
    run('write_uart_app',['write-flash','0x10000',str(R/'esp32.ino.bin')])
    run('verify_uart_app',['verify-flash','0x10000',str(R/'esp32.ino.bin')])
    run('read_nvs',['read-flash','0x9000','0x5000',str(R/'nvs_after.bin')])
    assert (R/'nvs_before.bin').read_bytes()==(R/'nvs_after.bin').read_bytes(),'NVS changed during programming'
    changed=True;BRIDGE.write_bytes((R/'fc_live_bridge.py').read_bytes());DROP.write_text('[Service]\nEnvironment="FORCAT_ESP32_PORT=/dev/ttyTHS1"\n');service('daemon-reload')
    runtime_ok=False;error=None
    try:
        frame=boot_stopped();runtime_ok=True
        queue('0\nbackup_on\nmode\npump_status')
        service('start','for-cat-esp32-bridge.service')
        live=wait_status(lambda s:s['device']==UART and s['telemetry']['fc_live'].get('demo_exited') is True)
        (R/'paused_uart.json').write_text(json.dumps(live,indent=2))
        for key in ('tare_counts','grams_per_count'):assert abs(frame[key]-cached['telemetry']['fc_live'][key])<1e-8,key
    except (AssertionError,RuntimeError) as exc:
        runtime_ok=False;error=str(exc)
        service('stop','for-cat-esp32-bridge.service')
        # Keep the requested UART image, but halt in ROM before backup boot grace.
        run('hold_in_rom',['read-flash','0x10000','0x100',str(R/'hold_app_header.bin')])
        service('start','for-cat-esp32-bridge.service')
    result={'app_sha256':META['after_app'],'bridge_sha256':META['bridge_after'],'port':UART,'rx_gpio':41,'tx_gpio':42,'baud':115200,'app_readback_verified':True,'nvs_byte_preserved':True,'uart_bidirectional':runtime_ok,'feeding_paused':True,'water_enabled':False,'actuator_test_sent':False,'runtime_error':error,'held_in_rom':not runtime_ok,'external_power_test_pending':True}
    (R/'flash_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
except BaseException:
    service('stop','for-cat-esp32-bridge.service')
    if changed:
        BRIDGE.write_bytes((R/'before_bridge.py').read_bytes());DROP.write_bytes((R/'before_uart.conf').read_bytes());service('daemon-reload')
    if wrote:
        (R/'restore_usb_app.bin').write_bytes(OLD)
        run('restore_usb_app',['write-flash','0x10000',str(R/'restore_usb_app.bin')])
        run('verify_restore',['verify-flash','0x10000',str(R/'restore_usb_app.bin')])
    service('start','for-cat-esp32-bridge.service');raise
finally:service('start','for-cat-api.service')
