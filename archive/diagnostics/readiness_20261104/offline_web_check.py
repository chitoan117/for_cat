from pathlib import Path
import asyncio,base64,json,os,subprocess,time,urllib.request,urllib.parse
import websockets

r=Path(__file__).parent
gui=os.environ.copy()
pid=subprocess.check_output(['pgrep','-u',str(os.getuid()),'-x','lxsession'],text=True).split()[0]
for item in Path('/proc',pid,'environ').read_bytes().split(b'\0'):
    key,sep,value=item.partition(b'=')
    if sep and key.decode() in ['DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS']: gui[key.decode()]=value.decode()
profile=str(r/'offline-test-profile')
log=(r/'offline_browser.log').open('a')
browser=subprocess.Popen(['/usr/bin/chromium-browser','--app=about:blank','--start-maximized','--no-first-run',
    '--no-default-browser-check','--user-data-dir='+profile,'--disable-gpu','--disable-dev-shm-usage',
    '--disable-background-networking','--disable-component-update','--disable-sync',
    '--remote-debugging-address=127.0.0.1','--remote-debugging-port=9224'],env=gui,stdout=log,stderr=log,start_new_session=True)
try:
    pages=[]
    for attempt in range(25):
        try:
            pages=json.load(urllib.request.urlopen('http://127.0.0.1:9224/json',timeout=2))
            if any(p.get('type')=='page' for p in pages): break
        except OSError: pass
        time.sleep(1)
    target=next(p for p in pages if p.get('type')=='page')
    async def test():
        report={'scope':'Browser page requests restricted to loopback; LAN/SSH not disconnected',
                'blocked_external_requests':[],'blocked_write_requests':[],'exceptions':[],
                'loaded_urls':[],'websocket_urls':[]}
        async with websockets.connect(target['webSocketDebuggerUrl'],max_size=8*1024*1024) as ws:
            async def send(i,method,params=None):
                await ws.send(json.dumps({'id':i,'method':method,'params':params or {}}))
            await send(1,'Runtime.enable')
            await send(2,'Network.enable')
            await send(3,'Page.enable')
            await send(4,'Fetch.enable',{'patterns':[{'urlPattern':'*','requestStage':'Request'}]})
            await send(5,'Page.navigate',{'url':'http://127.0.0.1:8000/app'})
            next_id=10
            deadline=time.monotonic()+35
            evaluation_sent=False
            screenshot_sent=False
            while time.monotonic()<deadline:
                if not evaluation_sent and time.monotonic()>deadline-10:
                    await send(1000,'Runtime.evaluate',{'expression':"JSON.stringify({title:document.title,text:document.body.innerText,views:document.querySelectorAll('flutter-view').length})",'returnByValue':True})
                    evaluation_sent=True
                try: msg=json.loads(await asyncio.wait_for(ws.recv(),timeout=1))
                except asyncio.TimeoutError: continue
                method=msg.get('method')
                p=msg.get('params',{})
                if method=='Fetch.requestPaused':
                    req=p['request']; url=req['url']; parsed=urllib.parse.urlsplit(url)
                    allowed=(parsed.hostname=='127.0.0.1' and parsed.port==8000)
                    write=req.get('method') not in ['GET','HEAD','OPTIONS']
                    if not allowed or write:
                        report['blocked_write_requests' if write else 'blocked_external_requests'].append(url)
                        await send(next_id,'Fetch.failRequest',{'requestId':p['requestId'],'errorReason':'BlockedByClient'})
                    else:
                        report['loaded_urls'].append(url)
                        await send(next_id,'Fetch.continueRequest',{'requestId':p['requestId']})
                    next_id+=1
                elif method=='Runtime.exceptionThrown': report['exceptions'].append(p)
                elif method=='Network.webSocketCreated': report['websocket_urls'].append(p.get('url'))
                elif msg.get('id')==1000:
                    report['page']=json.loads(msg['result']['result']['value'])
                    await send(1001,'Page.captureScreenshot',{'format':'png'})
                    screenshot_sent=True
                elif msg.get('id')==1001:
                    (r/'offline_page.png').write_bytes(base64.b64decode(msg['result']['data']))
                    break
            report['passed']=bool(report.get('page',{}).get('views') and 'Bữa ăn' in report.get('page',{}).get('text','') and not report['exceptions'] and not report['blocked_write_requests'])
            report['no_external_assets_required']=report['passed'] and not report['blocked_external_requests']
            (r/'offline_web_result.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
            print(json.dumps({k:v for k,v in report.items() if k not in ['loaded_urls','exceptions']},indent=2,ensure_ascii=False),flush=True)
            assert report['passed'],'Offline browser check failed'
    asyncio.run(test())
finally:
    # Only this isolated test profile is stopped; user's main browser stays open.
    browser.terminate()
    try: browser.wait(timeout=8)
    except subprocess.TimeoutExpired: print('Test browser close still pending; inspect its isolated profile')
