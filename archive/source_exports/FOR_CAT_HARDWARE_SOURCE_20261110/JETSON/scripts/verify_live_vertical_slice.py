"""Read-only REAL serial/AI -> REST/WS -> Chromium DOM evidence. No simulated input."""
import datetime
import json
from pathlib import Path
import subprocess
import urllib.request
import time
import base64
import os
import signal
import sys

from websockets.sync.client import connect

ROOT=Path('/home/toan/for_cat')
availability='--verify-current-availability' in sys.argv
OUT=ROOT/'evidence/overnight_integration_20261023'/('availability_recovery' if availability else 'vertical_slice')
OUT.mkdir(exist_ok=True)
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'LIVE_JETSON_NOT_SYNTHETIC','rest':{},'websocket':[],'browser':{}}
deadline=time.monotonic()+35
while True:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:
            startup=json.load(response)
    except OSError:
        if time.monotonic()>=deadline:raise
        time.sleep(.25)
        continue
    if startup['esp32']['connected'] and (availability or startup['ai']['health']=='ONLINE'):break
    if time.monotonic()>=deadline:raise RuntimeError('real AI state not ONLINE: '+json.dumps(startup['ai']))
    time.sleep(.5)
for host in ('127.0.0.1','192.168.123.18'):
    with urllib.request.urlopen('http://'+host+':8000/api/status',timeout=5) as response:
        report['rest'][host]=json.load(response)
    assert report['rest'][host]['data_source']=='REAL'
with connect('ws://127.0.0.1:8000/api/ws/state',open_timeout=5,close_timeout=2) as ws:
    for _ in range(8):
        state=json.loads(ws.recv(timeout=5))
        assert state['data_source']=='REAL'
        assert state['safety']['actuator_execution'] is False
        report['websocket'].append(state)
profile=OUT/('chromium_realtime_'+str(int(time.time())))
profile.mkdir()
with (OUT/'chromium_realtime.log').open('wb') as browser_log:
    browser=subprocess.Popen(['chromium-browser','--headless','--disable-gpu','--no-sandbox',
                              '--disable-dev-shm-usage','--no-first-run','--no-default-browser-check',
                              '--remote-debugging-port=0','--user-data-dir='+str(profile),
                              'http://127.0.0.1:8000/kiosk'],stdout=browser_log,stderr=browser_log)
    try:
        deadline=time.monotonic()+20
        while not (profile/'DevToolsActivePort').exists():
            assert time.monotonic()<deadline and browser.poll() is None,'Chromium CDP startup failed'
            time.sleep(.1)
        port=int((profile/'DevToolsActivePort').read_text().splitlines()[0])
        with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/json/list',timeout=5) as response:targets=json.load(response)
        target=next(t for t in targets if t['type']=='page')
        with connect(target['webSocketDebuggerUrl'],open_timeout=5,close_timeout=2) as cdp:
            serial=0
            def call(method,params):
                global serial
                serial+=1;cdp.send(json.dumps({'id':serial,'method':method,'params':params}))
                while True:
                    data=json.loads(cdp.recv(timeout=10))
                    if data.get('id')==serial:
                        assert 'error' not in data,data
                        return data.get('result',{})
            def evaluate(expression):
                return call('Runtime.evaluate',{'expression':expression,'returnByValue':True}).get('result',{}).get('value')
            for view in ('kiosk','app'):
                if view=='app':call('Page.navigate',{'url':'http://127.0.0.1:8000/app'})
                deadline=time.monotonic()+20
                while True:
                    body=evaluate("document.getElementById('raw-state') && document.getElementById('raw-state').textContent")
                    state=json.loads(body) if body else None
                    if state and state['esp32']['connected'] and (availability or state['ai']['health']=='ONLINE'):break
                    assert time.monotonic()<deadline,'Browser real state did not arrive'
                    time.sleep(.2)
                dom=evaluate('document.documentElement.outerHTML')
                (OUT/(view+'.dom.html')).write_text(dom)
                screenshot=call('Page.captureScreenshot',{'format':'png'})
                (OUT/(view+'.png')).write_bytes(base64.b64decode(screenshot['data']))
                first_uptime=state['esp32']['monotonic_ms']
                time.sleep(2)
                later=json.loads(evaluate("document.getElementById('raw-state').textContent"))
                report['browser'][view]={'real_mode_visible':'REAL · backend live' in dom,
                                        'esp32_connected_visible':'id="esp32">ESP32_CONNECTED' in dom,
                                        'distance_visible':bool(__import__('re').search(r'id="approach">[0-9]+\.[0-9]+ cm',dom)),
                                        'ai_visible':any('id="ai">'+label in dom for label in ('CAT','DOG','NONE')),
                                        'grams_null_visible':'grams: null' in dom,
                                        'first_rendered_state':state,'later_without_refresh':later,
                                        'uptime_advanced_without_refresh':later['esp32']['monotonic_ms']>first_uptime}
                (OUT/'evidence.partial.json').write_text(json.dumps(report,indent=2))
                assert all(report['browser'][view][k] for k in ['real_mode_visible','esp32_connected_visible','grams_null_visible','uptime_advanced_without_refresh'])
                if not availability:
                    assert report['browser'][view]['distance_visible'] and report['browser'][view]['ai_visible']
                else:
                    assert state['ai']['classification']=='UNKNOWN' or report['browser'][view]['ai_visible']
                    if not state['approach']['valid']:assert 'id="approach">—' in dom
            if '--exercise-stale' in sys.argv:
                pid=int(subprocess.check_output(['systemctl','--user','show','for-cat-esp32-bridge.service','-p','MainPID','--value']).strip())
                assert pid>1 and 'esp32_bridge' in str((Path('/proc')/str(pid)/'exe').resolve())
                os.kill(pid,signal.SIGSTOP)
                try:
                    deadline=time.monotonic()+10
                    while True:
                        paused=json.loads(evaluate("document.getElementById('raw-state').textContent"))
                        if paused and paused['esp32']['health']=='ESP32_STALE':break
                        assert time.monotonic()<deadline,'UI did not mark stopped bridge stale'
                        time.sleep(.2)
                    assert paused['approach']['distance_cm'] is None and paused['weight']['raw_counts'] is None
                    report['real_link_stale_test']={'method':'SIGSTOP receiver only; NOT a physical USB unplug',
                                                    'stale_rendered_state':paused,'actuator_execution':False}
                finally:
                    os.kill(pid,signal.SIGCONT)
                deadline=time.monotonic()+10
                while True:
                    recovered=json.loads(evaluate("document.getElementById('raw-state').textContent"))
                    if recovered and recovered['esp32']['connected']:break
                    assert time.monotonic()<deadline,'UI recovery after receiver resume failed'
                    time.sleep(.2)
                report['real_link_stale_test']['recovered_rendered_state']=recovered
                assert recovered['safety']['servo_armed'] is False and recovered['safety']['pump_armed'] is False
    finally:
        browser.terminate()
        browser.wait(timeout=10)
(OUT/'evidence.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'rest_health':{key:value['esp32'] for key,value in report['rest'].items()},
                  'ai':report['websocket'][-1]['ai'],'ws_frames':len(report['websocket']),
                  'ws_uptimes':sorted(set(s['esp32'].get('monotonic_ms') for s in report['websocket'])),
                  'ws_distances':sorted(set(s['approach']['distance_cm'] for s in report['websocket'] if s['approach']['valid'])),
                  'browser':{view:{key:value for key,value in details.items() if key not in ('first_rendered_state','later_without_refresh')} for view,details in report['browser'].items()},
                  'receiver_stale_recovery_verified':'real_link_stale_test' in report},indent=2))
