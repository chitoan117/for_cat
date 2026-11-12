"""GET-only local/remote verification; no feeding, producer uploads or UART."""
import json
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from runtime_config import validate

def fetch(url,headers=None):
    request=Request(url,headers=headers or {},method='GET')
    try:
        with urlopen(request,timeout=10) as response:
            data=response.read(1048577)
            if len(data)>1048576:raise ValueError('verification response budget')
            return response.status,dict(response.headers),data
    except HTTPError as e:return e.code,dict(e.headers),e.read(4096)
def evaluate(state,camera,health,mjpeg):
    reasons=[]
    ai=state.get('ai',{})
    if health.get('status')!='ok':reasons.append('API_HEALTH')
    if ai.get('health')!='ONLINE' or ai.get('data_source')!='REAL' or ai.get('simulated') is not False or ai.get('ai_schema_version')!=1:reasons.append('REAL_FRAMED_AI_UNAVAILABLE')
    if ai.get('classification') not in ('CAT','DOG','NONE') or ai.get('frame_metadata_available') is not True:reasons.append('AI_FRAME_CONTRACT')
    age=ai.get('age_seconds')
    if type(age) not in (int,float) or not 0<=age<=1.5:reasons.append('AI_STALE')
    if camera.get('status')!='CAMERA_ONLINE' or camera.get('source')!='REAL' or camera.get('simulated') is not False:reasons.append('REAL_CAMERA_OFFLINE')
    if camera.get('actuator_execution') is not False:reasons.append('CAMERA_CONTROL_CONTRACT')
    if not camera.get('producer_epoch') or camera.get('producer_epoch')!=ai.get('producer_epoch'):reasons.append('EPOCH_MISMATCH_RETRY_AFTER_RESTART')
    if camera.get('frame_slots')!=1 or camera.get('buffered_bytes',1048577)>524288 or camera.get('max_viewers')!=4:reasons.append('VIDEO_BUDGET')
    if state.get('safety',{}).get('actuator_execution') is not False or state.get('feed',{}).get('actuator_execution') is not False:reasons.append('ACTUATOR_AUTHORITY_VIOLATION')
    if any(state.get('safety',{}).get(k) is True for k in ('servo_armed','pump_armed','auto_feed','auto_water')):reasons.append('ACTUATOR_ARMED')
    if b'Content-Type: image/jpeg' not in mjpeg or b'\xff\xd8' not in mjpeg or b'--frame--' not in mjpeg:reasons.append('MJPEG_CONTRACT')
    telemetry=state.get('esp32',{}).get('connected') is True and state.get('esp32',{}).get('health')=='ESP32_CONNECTED'
    return {'camera_api_contract':'PASS' if not reasons else 'FAIL','reasons':reasons,
            'system_acceptance':'BLOCKED_ESP32_TELEMETRY' if not telemetry else 'PENDING_PHYSICAL_REVIEW',
            'ESP32_TELEMETRY_PASS':'NOT_VERIFIED','JETSON_REAL_CAMERA_PASS':'NOT_VERIFIED',
            'TAILSCALE_REMOTE_PASS':'NOT_VERIFIED','ACTUATOR_PHYSICAL_PASS':'NOT_VERIFIED'}
def verify_http(private,remote=False,get=fetch):
    config=validate(private);host=config['FORCAT_TAILSCALE_HOSTNAME']
    base='https://'+host if remote else 'http://127.0.0.1:8000'
    users=__import__('json').loads(__import__('pathlib').Path(config['FORCAT_ACCESS_POLICY_FILE']).read_text())['users']
    headers={} if remote else {'Host':host,'x-forwarded-proto':'https','tailscale-user-login':next(iter(users))}
    # watch=true creates bounded preview demand, not a camera owner/control request.
    results={}
    for key,path in [('health','/api/v1/health'),('state','/api/status'),('camera','/api/v1/camera/status?watch=true'),('mjpeg','/api/v1/camera/mjpeg?frames=1')]:
        code,_,body=get(base+path,headers)
        if code!=200:return {'camera_api_contract':'FAIL','reason':key+'_HTTP_'+str(code),'remote_network_pass':'NOT_VERIFIED'}
        results[key]=body if key=='mjpeg' else json.loads(body)
    report=evaluate(results['state'],results['camera'],results['health'],results['mjpeg'])
    if not remote:
        unauthorized=get(base+'/api/v1/camera/status',{})[0]
        if unauthorized!=403:report['camera_api_contract']='FAIL';report['reasons'].append('UNAUTHORIZED_CAMERA_ACCESS')
    report['verification_path']='TAILNET_HTTPS_GET_ONLY' if remote else 'TRUSTED_LOOPBACK_IDENTITY_CONTRACT_ONLY_NOT_SERVE_PROOF'
    report['feed_mutations_sent']=False
    return report
