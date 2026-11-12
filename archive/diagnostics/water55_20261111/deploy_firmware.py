from pathlib import Path
from contextlib import closing
import hashlib,json,os,sqlite3,struct,subprocess,time,zlib
import serial
R=Path('/home/toan/for_cat/evidence/water55_20261111')
ROOT=Path('/home/toan/for_cat/jetson');DB=ROOT/'data/events.db'
USB=Path('/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00');UART='/dev/ttyTHS1'
BRIDGE=ROOT/'tools/fc_live_bridge.py'
TOOL='/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/flash_tool/bin/esptool.py'
META=json.loads((R/'integrity.json').read_text());OLD=Path('/home/toan/for_cat/evidence/backup30_20261111/esp32.ino.bin').read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
def service(action,*names):subprocess.run(['systemctl','--user',action,*names],check=True,timeout=20)
def snapshot():
    with closing(sqlite3.connect(DB,timeout=2)) as db:return json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
def wait_status(predicate,timeout=15):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        s=snapshot()
        if 0<=time.monotonic()*1000-s['updated_monotonic_ms']<2500 and predicate(s):return s
        time.sleep(.15)
    raise RuntimeError('No fresh matching telemetry')
def queue(commands):
    dest=Path('/tmp/for_cat_cmd.txt');end=time.monotonic()+8
    while dest.exists() and time.monotonic()<end:time.sleep(.1)
    assert not dest.exists(),'Pending command; no overwrite allowed'
    p=Path('/tmp/backup30_%d.txt'%os.getpid());p.write_text(commands+'\n')
    try:os.link(p,dest)
    finally:p.unlink()
def open_serial(port):
    s=serial.Serial(None,115200,timeout=.1,write_timeout=.5,rtscts=False,dsrdtr=False)
    s.dtr=False;s.rts=False;s.port=port;s.open();return s
def run(label,args):
    with (R/(label+'.log')).open('w') as f:
        p=subprocess.run([TOOL,'--chip','esp32s3','--port',str(USB.resolve()),'--baud','921600','--before','default-reset','--after','no-reset']+args,stdout=f,stderr=subprocess.STDOUT,timeout=180)
    assert p.returncode==0,label+': '+(R/(label+'.log')).read_text()[-1500:]
    print(label+': PASS',flush=True)
def boot_stopped(label):
    lines=[];pending=bytearray();frame=None;position=None;stop=False
    with open_serial(UART) as s:
        with open_serial(str(USB.resolve())) as reset:
            reset.rts=True;time.sleep(.1);reset.rts=False
        end=time.monotonic()+17;last=0
        while time.monotonic()<end:
            if time.monotonic()-last>.6:
                s.write(b'0\njetson_ping\nservo_position\nmode\nhx_diag\n');last=time.monotonic()
            pending.extend(s.read(4096))
            while b'\n' in pending:
                raw,_,tail=pending.partition(b'\n');pending=bytearray(tail)
                line=raw.decode('utf8',errors='replace').strip();lines.append(line)
                if 'EXIT 0' in line:stop=True
                if 'SERVO ESTIMATE=' in line and 'moving=0' in line:position=line
                if line.startswith('{'):
                    try:
                        msg=json.loads(line)
                        if msg.get('type')=='status' and msg.get('demo_exited') is True:frame=msg
                    except ValueError:pass
            if stop and position and frame:break
            assert len(pending)<16384,'Oversized UART fragment'
    (R/(label+'.log')).write_text('\n'.join(lines)+'\n')
    assert stop and position and frame,'Stopped boot not verified on UART'
    (R/(label+'_frame.json')).write_text(json.dumps(frame,indent=2))
    print(json.dumps({'stop_ack':stop,'servo':position,'uart_status':True}),flush=True);return frame
def same_cal(before,after):
    for k in ('tare_counts','grams_per_count'):assert abs(before[k]-after[k])<1e-8,(k,before[k],after[k])
def main():
    assert USB.exists() and USB.resolve().is_char_device(),'Programming USB missing'
    assert sha(OLD)==META['before_app'] and sha(BRIDGE.read_bytes())==META['bridge_expected'],'Baseline changed'
    assert sha((R/'esp32.ino.bin').read_bytes())==(R/'app.sha256').read_text().strip()
    assert not (R/'before_flash.bin').exists(),'Already attempted; inspect evidence'
    pre=wait_status(lambda s:s['device']==UART);fc=pre['telemetry']['fc_live']
    assert fc['bench_state'] in ('READY','CAT FAULT*','MASS OK GATE?','EXIT0') and not fc.get('dog_running'),'Device busy'
    assert fc.get('meal_phase') not in ('CAPTURING','OBSERVING')
    with closing(sqlite3.connect(DB,timeout=2)) as db:assert db.execute('SELECT count(*) FROM feed_dry_run_requests WHERE decision IS NULL').fetchone()[0]==0
    (R/'preflight.json').write_text(json.dumps(pre,indent=2))
    queue('0');sent=time.monotonic()*1000
    wait_status(lambda s:s['updated_monotonic_ms']>sent and s['telemetry']['fc_live'].get('demo_exited') is True)
    service('stop','for-cat-api.service','for-cat-esp32-bridge.service')
    wrote=False;boot_ok=False
    try:
        for p in (UART,str(USB.resolve())):assert subprocess.run(['fuser',p],capture_output=True).returncode==1,'Serial still owned'
        run('backup_flash',['read-flash','0','0x150000',str(R/'before_flash.bin')])
        raw=(R/'before_flash.bin').read_bytes();assert len(raw)==0x150000
        assert raw[0x10000:0x10000+len(OLD)]==OLD,'Actual app differs from baseline'
        assert raw[0x8000:0x8c00]==(R/'esp32.ino.partitions.bin').read_bytes(),'Partition table differs'
        seq=[]
        for off in (0xe000,0xf000):
            e=raw[off:off+32];seq.append(struct.unpack_from('<I',e)[0]);assert struct.unpack_from('<I',e,24)[0]==0xffffffff
            assert struct.unpack_from('<I',e,28)[0]==zlib.crc32(e[:4],0xffffffff)
        assert seq==[1,0],seq
        (R/'nvs_before.bin').write_bytes(raw[0x9000:0xe000]);wrote=True
        run('write_app',['write-flash','0x10000',str(R/'esp32.ino.bin')])
        run('verify_app',['verify-flash','0x10000',str(R/'esp32.ino.bin')])
        run('read_nvs',['read-flash','0x9000','0x5000',str(R/'nvs_after.bin')])
        assert (R/'nvs_before.bin').read_bytes()==(R/'nvs_after.bin').read_bytes(),'Calibration/state NVS changed during flash'
        frame=boot_stopped('boot_new');boot_ok=True;same_cal(fc,frame)
        assert frame.get('pir_configured') is False
        assert abs(frame['pump_on_cm']-5.7)<.001 and abs(frame['pump_off_cm']-5.5)<.001
        assert frame['pump_max_run_ms']==10000 and frame['pump_auto_enabled'] is False
        assert frame['pump_auto_running'] is False
        queue('0\nbackup_on\nmode\nservo_position')
        service('start','for-cat-esp32-bridge.service')
        sent=time.monotonic()*1000
        after=wait_status(lambda s:s['updated_monotonic_ms']>sent and s['device']==UART and s['telemetry']['fc_live'].get('demo_exited') is True and s['telemetry']['fc_live'].get('backup_enabled') is True)
        same_cal(fc,after['telemetry']['fc_live'])
        assert sha(BRIDGE.read_bytes())==META['bridge_expected'],'Bridge unexpectedly changed'
        (R/'paused_after_flash.json').write_text(json.dumps(after,indent=2))
        result={'app_sha256':sha((R/'esp32.ino.bin').read_bytes()),'readback_verified':True,'nvs_preserved_during_flash':True,'calibration_preserved':True,'backup_enabled':True,'water_thresholds_cm':[5.7,5.5],'target_g':35,'feeding_paused':True,'movement_commands_sent':False,'water_enable_not_tested':True}
        (R/'flash_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    except BaseException:
        service('stop','for-cat-esp32-bridge.service')
        if wrote:
            (R/'restore_old_app.bin').write_bytes(OLD)
            run('rollback_app',['write-flash','0x10000',str(R/'restore_old_app.bin')])
            run('verify_rollback',['verify-flash','0x10000',str(R/'restore_old_app.bin')])
        boot_stopped('boot_restore')
        queue('0');service('start','for-cat-esp32-bridge.service');raise
    finally:service('start','for-cat-api.service')
if __name__=='__main__':main()
