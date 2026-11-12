import json,subprocess
from pathlib import Path
O=Path(__file__).resolve().parent;c=json.loads((O/'connection.json').read_text())
for name in ('flash_app_only.py',):
 r=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(O/name),'toan@'+c['host']+':'+c['evidence']+'/'+name],capture_output=True,timeout=60);assert r.returncode==0,r.stderr.decode()
source=(Path(r'D:\for_cat\PHYSICAL_RESUME_20261027\verify_browser.cjs')).read_text(encoding='utf-8')
# A new browser instance/tests, no production service pause. Preserve prior tool.
source=source.replace("  // Restrict faults to this new browser page.","  // Restrict faults to this new browser page.")
insert="""
  await call('Page.navigate',{url:BASE+'/app'});await until(s=>s.labels.join('\\n').includes('REAL · Đang kết nối'));
  await click(692,966); // desktop width1024, constrained nav: Hệ thống
  for(let i=0;i<8;i++){
   const s=await snap();
   if(s.labels.join('\\n').includes('HC-SR04 #2')){await call('Input.dispatchMouseEvent',{type:'mouseWheel',x:512,y:500,deltaX:0,deltaY:600});await sleep(400);await shot('four_ultrasonic_upper');break;}
   await call('Input.dispatchMouseEvent',{type:'mouseWheel',x:512,y:500,deltaX:0,deltaY:300});await sleep(300);
  }
  for(let i=0;i<8;i++){
   const s=await snap();
   if(s.labels.join('\\n').includes('JSN-SR04T #2')){await call('Input.dispatchMouseEvent',{type:'mouseWheel',x:512,y:500,deltaX:0,deltaY:600});await sleep(400);await shot('four_ultrasonic_lower');break;}
   await call('Input.dispatchMouseEvent',{type:'mouseWheel',x:512,y:500,deltaX:0,deltaY:300});await sleep(300);
  }
"""
source=source.replace("  // Restrict faults to this new browser page.",insert+"\n  // Restrict faults to this new browser page.")
(O/'verify_browser.cjs').write_text(source,encoding='utf-8')
print('Manual no-I/O flash script staged; browser verification prepared')
