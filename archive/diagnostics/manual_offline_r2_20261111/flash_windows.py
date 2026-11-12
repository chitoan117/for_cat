"""Program the owner-confirmed, VIN-off ESP32 on the laptop; no application motion."""
from pathlib import Path
import hashlib,json,struct,subprocess,time,zlib
R=Path(__file__).resolve().parent;OUT=R/'windows_flash';OUT.mkdir(exist_ok=True)
CLI=Path('C:/Users/chito/AppData/Local/Programs/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe')
TOOL=Path('C:/Users/chito/AppData/Local/Arduino15/packages/esp32/tools/esptool_py/5.3.1/esptool.exe')
META=json.loads((R/'integrity.json').read_text());OLD=(R.parent/'manual_20261111/esp32.ino.bin').read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
ports=json.loads(subprocess.check_output([str(CLI),'board','list','--format','json'],text=True,timeout=30))
matches=[]
for entry in ports.get('detected_ports',[]):
    port=entry['port'];p=port.get('properties',{})
    if p.get('serialNumber')=='5C85066678' and p.get('vid','').lower()=='0x1a86' and p.get('pid','').lower()=='0x55d3':matches.append(port['address'])
assert len(matches)==1,'Expected unique owner ESP32 USB serial5C85066678'
PORT=matches[0];assert PORT.startswith('COM')
assert sha(OLD)==META['before_app']
assert sha((R/'esp32.ino.bin').read_bytes())==META['after_app']
assert not (OUT/'before_flash.bin').exists(),'A flash backup exists; inspect before retrying'
(OUT/'port_inventory.json').write_text(json.dumps(ports,indent=2))
def run(label,args):
    with (OUT/(label+'.log')).open('w',encoding='utf8') as log:
        p=subprocess.run([str(TOOL),'--chip','esp32s3','--port',PORT,'--baud','921600','--before','default-reset','--after','no-reset']+args,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    assert p.returncode==0,label+': '+(OUT/(label+'.log')).read_text(encoding='utf8',errors='replace')[-1400:]
    print(label+': PASS',flush=True)
result={'port':PORT,'usb_serial':'5C85066678','owner_confirmed_vin_off_usb_laptop':True,'app_sha256':META['after_app'],'source_sha256':META['source_after'],'programmed':False}
wrote=False
try:
    run('backup_flash',['read-flash','0','0x150000',str(OUT/'before_flash.bin')])
    raw=(OUT/'before_flash.bin').read_bytes();assert len(raw)==0x150000
    assert raw[0x10000:0x10000+len(OLD)]==OLD,'Actual firmware differs from expected current UART581 image'
    assert raw[0x8000:0x8c00]==(R/'esp32.ino.partitions.bin').read_bytes(),'Partition table changed'
    seq=[]
    for off in (0xe000,0xf000):
        entry=raw[off:off+32];seq.append(struct.unpack_from('<I',entry)[0])
        assert struct.unpack_from('<I',entry,24)[0]==0xffffffff
        assert struct.unpack_from('<I',entry,28)[0]==zlib.crc32(entry[:4],0xffffffff)
    assert seq==[1,0],seq
    (OUT/'nvs_before.bin').write_bytes(raw[0x9000:0xe000])
    wrote=True;run('write_app',['write-flash','0x10000',str(R/'esp32.ino.bin')])
    run('verify_app',['verify-flash','0x10000',str(R/'esp32.ino.bin')])
    run('read_nvs',['read-flash','0x9000','0x5000',str(OUT/'nvs_after.bin')])
    assert (OUT/'nvs_before.bin').read_bytes()==(OUT/'nvs_after.bin').read_bytes(),'NVS changed during programming'
    result.update(programmed=True,actual_baseline_verified=True,partition_and_ota_verified=True,app_readback_verified=True,nvs_byte_preserved=True,no_auto_zero=True,existing_six_headers_unchanged=True,offline_inspection_hold_ms=5000,transport='UART1 RX41 TX42 115200',manual_wait_fresh_hx_ms=3000,manual_added_mass_target_g=35,manual_weight_timeout_ms=25000,jetson_bridge_update_pending=True,physical_runtime_test_pending=True,after_flash_mode='no-reset; remain in bootloader until power cycle',motor_or_pump_test_sent=False)
except BaseException as exc:
    result['error']=str(exc)
    if wrote:
        (OUT/'restore_old_app.bin').write_bytes(OLD)
        run('rollback_old_app',['write-flash','0x10000',str(OUT/'restore_old_app.bin')])
        run('verify_rollback',['verify-flash','0x10000',str(OUT/'restore_old_app.bin')])
        result['old_app_restored']=True
    raise
finally:
    (OUT/'flash_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
