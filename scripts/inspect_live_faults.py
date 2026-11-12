import datetime,json,pathlib,subprocess,urllib.request
R=pathlib.Path('/home/toan/for_cat');E=R/'evidence/overnight_integration_20261023'
data={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':{}}
for name,args in {'usb':['lsusb'],'camera_owner':['fuser','-v','/dev/video0'],
                  'camera_nodes':['sh','-c','ls -l /dev/video* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null'],
                  'ai_unit':['systemctl','--user','status','for-cat-ai.service','--no-pager'],
                  'processes':['ps','-eo','pid,ppid,args'], 'kernel':['dmesg']}.items():
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
    text=p.stdout.decode('utf-8','replace')
    data['commands'][name]={'exit':p.returncode,'output':text}
    if name=='kernel':text='\n'.join(line for line in text.splitlines() if any(key in line for key in ('usb ','uvcvideo','ttyACM','cdc_acm','ch34')))
    if name=='processes':text='\n'.join(line for line in text.splitlines() if any(key in line for key in ('cat_dog','ai_state','esp32_bridge','run_api')))
    print(name+'\n'+text)
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:data['system_state']=json.load(response)
(E/'live_fault_observation.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data['system_state'],indent=2))
