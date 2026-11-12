"""Enable private HTTPS access only after the owner logs Jetson into Tailscale."""
import subprocess,json,sys,urllib.request,urllib.error
from pathlib import Path

r=Path('/home/toan/for_cat/evidence/servo_uno_20261103_deploy')
p=subprocess.run(['tailscale','status','--json'],capture_output=True,text=True)
status=json.loads(p.stdout)
if status.get('BackendState')!='Running':
    print('OWNER_LOGIN_REQUIRED:',status.get('AuthURL','Run tailscale up after granting operator permission'))
    sys.exit(2)
name=status.get('Self',{}).get('DNSName','').rstrip('.')
assert name and name.endswith('.ts.net'),'Tailnet DNS name not available'
for path in ['/app','/flutter/flutter_bootstrap.js','/flutter/main.dart.js','/api/status']:
    with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=10) as response:
        assert response.status==200
        response.read(1024)
    print('LOCAL_GET_PASS:',path)
before=subprocess.run(['tailscale','serve','status','--json'],capture_output=True,text=True)
backup=r/'tailscale_serve_before.json'
if not backup.exists(): backup.write_text(before.stdout)
try:
    result=subprocess.run(['tailscale','serve','--bg','--yes','http://127.0.0.1:8000'],capture_output=True,text=True,timeout=30)
except subprocess.TimeoutExpired as exc:
    for stream in (exc.stdout,exc.stderr):
        if stream: print(stream.decode(errors='replace') if isinstance(stream,bytes) else stream)
    print('Serve activation is waiting for owner account confirmation; rerun after enabling Serve/HTTPS.')
    sys.exit(3)
print(result.stdout)
if result.returncode:
    print(result.stderr)
    sys.exit(result.returncode)
after=subprocess.run(['tailscale','serve','status','--json'],capture_output=True,text=True,check=True)
config=json.loads(after.stdout)
assert not any(config.get('AllowFunnel',{}).values()),'Unexpected public Funnel configuration'
(r/'tailscale_serve_after.json').write_text(after.stdout)
verification=[]
listeners=subprocess.run(['ss','-lnt'],capture_output=True,text=True,check=True).stdout
for path in ['/app','/flutter/flutter_bootstrap.js','/api/status']:
    url='https://'+name+path
    try:
        with urllib.request.urlopen(url,timeout=25) as response:
            assert response.status==200
            response.read(1024)
        verification.append({'url':url,'status':200})
        print('HTTPS_GET_PASS:',url)
    except urllib.error.URLError as exc:
        if not isinstance(exc.reason,ConnectionRefusedError) or '%tailscale0:443' not in listeners:
            raise
        verification.append({'url':url,'status':None,'result':'INCONCLUSIVE_SELF_CONNECTION',
                             'reason':'Serve listener bound to tailscale0; verify from another authorized tailnet device'})
        print('SELF_HTTPS_INCONCLUSIVE:',url)
report={'url':'https://'+name+'/app','private_tailnet_only':True,
        'https_serve_configured':True,
        'jetson_https_checks':verification,'phone_4g_verified':False,
        'bridge_stopped_for_pcb_work':True}
(r/'remote_access_result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
