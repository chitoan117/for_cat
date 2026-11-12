"""Manual app-only flash. Default is a no-I/O plan; never run write automatically."""
import argparse,datetime,hashlib,json,re,subprocess,sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-app',action='store_true')
    parser.add_argument('--power-isolated',action='store_true',help='Operator confirms external servo/pump power is disconnected')
    args=parser.parse_args();E=Path(__file__).resolve().parent
    manifest=json.loads((E/'release_manifest.json').read_text());images=E/'host_release/firmware'
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    for name,value in manifest['firmware'].items():
        if sha(images/name)!=value:raise RuntimeError('Firmware checksum mismatch: '+name)
    tool=E/'flash_tool/bin/python'
    if not tool.is_file():raise RuntimeError('Isolated flash tool missing')
    if not args.write_app:
        print(json.dumps({'status':'ESP32 FLASH REQUIRED','serial_opened':False,'flash_performed':False,'image':str(images/'firmware.bin'),'sha256':manifest['firmware']['firmware.bin'],
          'manual_command':[str(tool),str(E/'flash_app_only.py'),'--write-app','--power-isolated']},indent=2));return
    if not args.power_isolated:raise RuntimeError('BLOCKED: disconnect external servo/pump power before bootloader/reset')
    from serial.tools import list_ports
    ports=[p for p in list_ports.comports() if p.vid==0x1a86 and p.pid==0x55d3 and p.serial_number=='5C85066678']
    if len(ports)!=1:raise RuntimeError('BLOCKED: expected one identified ESP32')
    device=ports[0].device
    import urllib.request
    with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:state=json.load(response)
    if state['data_source']!='REAL' or any(state['safety'].get(k) is not False for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution')) or state['safety'].get('actuator_outputs_enabled')!=0:
        raise RuntimeError('BLOCKED: baseline safety not confirmed')
    run=E/('manual_flash_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    receipt={'status':'BLOCKED','device':device,'power_isolated_operator_confirmed':True,'commands':[],'writes':[]}
    def step(name,arguments,reset=False):
        command=[str(tool),'-m','esptool','--chip','esp32s3','--port',device,'--baud','115200','--no-stub','--after','hard-reset' if reset else 'no-reset',*arguments]
        p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        (run/(name+'.log')).write_bytes(p.stdout);receipt['commands'].append({'name':name,'argv':command,'exit':p.returncode})
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2))
        if p.returncode:raise RuntimeError(name+' failed; stop, no recovery erase')
        return p.stdout.decode('utf-8','replace')
    subprocess.run(['systemctl','--user','stop','for-cat-esp32-bridge.service'],check=True)
    try:
        owner=subprocess.run(['fuser',device],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if owner.returncode!=1:raise RuntimeError('BLOCKED: serial not proven unowned')
        identity=step('identity',['flash-id'])
        if 'ESP32-S3' not in identity or not re.search(r'flash size:\s*16MB',identity,re.I):raise RuntimeError('BLOCKED: chip/flash mismatch')
        step('verify_bootloader',['verify-flash','0x0',str(images/'bootloader.bin')])
        step('verify_partitions',['verify-flash','0x8000',str(images/'partitions.bin')])
        before=run/'nvs_before.bin';after=run/'nvs_after.bin'
        step('read_nvs_before',['read-flash','0x9000','0x5000',str(before)])
        receipt['writes'].append({'offset':'0x10000','image_sha256':manifest['firmware']['firmware.bin']})
        step('write_application',['write-flash','0x10000',str(images/'firmware.bin')])
        step('verify_application',['verify-flash','0x10000',str(images/'firmware.bin')])
        step('read_nvs_after',['read-flash','0x9000','0x5000',str(after)],reset=True)
        if len(before.read_bytes())!=0x5000 or sha(before)!=sha(after):raise RuntimeError('BLOCKED: NVS mismatch')
        receipt.update(status='RUNTIME_PASS',nvs_unchanged=True,nvs_sha256=sha(after),physical_validation='NOT_TESTED',acquisition_enabled=False)
    except Exception as error:
        receipt['error']=str(error);raise
    finally:
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2))
        subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True)
    print(json.dumps({'status':receipt['status'],'evidence':str(run),'next':'Wait for baseline/safety check; do not enable all channels'},indent=2))

if __name__=='__main__':main()
