"""Future OWNER-only user-Bridge lease. PLAN by default. No flash/device-tool API.
Agent must never use --execute; isolated tests inject all service operations.
"""
from __future__ import print_function
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import time
import readiness as r

ACK='OWNER_APPROVED_READ_MAINTENANCE'
RETURN='NORMAL_APP_BOOT_AND_PORT_TOOLS_CLOSED'

def approval(path,now=None):
    v=json.loads(Path(path).read_text())
    if v.get('scope')!='READ_MAINTENANCE_ONLY_NO_FLASH' or v.get('approved') is not True or not v.get('approved_by'):
        raise ValueError('explicit reviewed read-window approval required')
    if v.get('flash_authorized') is not False:raise ValueError('this lease cannot authorize flash')
    for key in ('echo_protection_evidence_reviewed','servo_pump_buzzer_power_isolated',
                'HX711_RAM_loss_accepted','manual_normal_boot_and_handback_reviewed'):
        if v.get(key) is not True:raise ValueError('missing maintenance condition: '+key)
    for key,value in (('bridge_unit',r.UNIT),('bridge_executable',r.EXE),('by_id',r.BYID)):
        if v.get(key)!=value:raise ValueError('approval identity mismatch: '+key)
    expires=datetime.strptime(v['valid_until_utc'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    now=now or datetime.now(timezone.utc)
    if not 0<(expires-now).total_seconds()<=24*3600:raise ValueError('approval expired or exceeds24h scope')
    if set(v.get('allowed_actions',[]))-{'boot_capture','get_security_info','efuse_summary'}:
        raise ValueError('unapproved operation in read window')
    return v

def unchanged(before,after):
    return all(before.get(k)==after.get(k) for k in ('ExecStart','FragmentPath','DropInPaths','Restart','UnitFileState')) and after.get('NeedDaemonReload')=='no'

def restore(before,runner=r.command,identity=r.host_identity,hash_file=r.sha):
    """Never changes config, AI/API state, enablement or originally inactive unit."""
    result={'created_utc':r.utc(),'bridge_restored':False,'normal_app_boot_verified':False,
            'ai_api_unchanged_active':False,'manual_recovery_required':False}
    try:
        cur,raw=r.show(r.UNIT,runner)
        if raw['code'] or not unchanged(before['bridge'],cur):raise ValueError('unit configuration changed; manual review required')
        if before['bridge'].get('ActiveState')!='active':
            result['bridge_restored']=cur.get('ActiveState')==before['bridge'].get('ActiveState')
            return result
        if identity()!=r.PORT:raise ValueError('USB changed/disconnected; no auto-start')
        if cur.get('ActiveState')!='active':
            pids,_=r.holders(runner)
            if pids:raise ValueError('serial tools/other owner still hold port; no auto-start')
            if hash_file(r.EXE)!=before.get('running_executable_sha256'):raise ValueError('production executable changed; no overwrite/start')
            raw=runner(['systemctl','--user','start',r.UNIT]);result['start_result']=raw
            if raw['code']:raise ValueError('Bridge start failed')
        # Bounded wait for active and sole serial ownership; no process restart loop.
        for _ in range(10):
            cur,raw=r.show(r.UNIT,runner);pids,_=r.holders(runner)
            pid=int(cur.get('MainPID','0'))
            if not raw['code'] and cur.get('ActiveState')=='active' and cur.get('SubState')=='running' and pid>0 and pids==[pid]:
                result['bridge_restored']=True;break
            time.sleep(.3)
        peer_ok=True;result['peers']={}
        for key in ('ai','api'):
            peer,raw=r.show(before[key+'_unit'],runner);result['peers'][key]=peer
            peer_ok=peer_ok and not raw['code'] and peer.get('ActiveState')=='active' and peer.get('MainPID')==before[key].get('MainPID')
        result['ai_api_unchanged_active']=bool(peer_ok)
        if not result['bridge_restored'] or not peer_ok:raise ValueError('Bridge ownership or AI/API continuity not verified')
    except (OSError,ValueError) as e:
        result['error']=str(e);result['manual_recovery_required']=True
    return result

def lease(out,approved,runner=r.command,inspector=None,prompt=input,identity=r.host_identity,hash_file=r.sha):
    inspector=inspector or (lambda:r.snapshot(out))
    before=inspector()
    if before['preflight_issues']:raise ValueError('fresh metadata preflight NO_GO: '+str(before['preflight_issues']))
    # Recheck just before stop; PID3989 is historical, never used as a kill target.
    cur,raw=r.show(r.UNIT,runner);pids,_=r.holders(runner)
    if raw['code'] or cur.get('ActiveState')!='active' or cur.get('SubState')!='running' or cur.get('MainPID')!=before['bridge'].get('MainPID') or not unchanged(before['bridge'],cur) or pids!=[int(cur['MainPID'])] or identity()!=r.PORT:
        raise ValueError('Bridge changed since snapshot; no stop')
    attempted=False;normal=False;error=None;handback=None
    try:
        attempted=True
        stopped=runner(['systemctl','--user','stop',r.UNIT]);r.write_new(out/'stop_result.json',stopped)
        if stopped['code']:raise ValueError('stop failed; attempt original-state handback')
        cur,raw=r.show(r.UNIT,runner);pids,_=r.holders(runner)
        if raw['code'] or cur.get('ActiveState') not in ('inactive','failed') or pids or identity()!=r.PORT:
            raise ValueError('serial was not exclusively released; no device tool allowed')
        r.write_new(out/'lease_open.json',{'state':'SERIAL_RELEASED_FOR_OWNER','pid':os.getpid(),
            'approval':approved,'created_utc':r.utc(),'by_id':r.BYID,'snapshot':'snapshot.json'})
        print('READ WINDOW OPEN. No device command runs automatically. Follow MAINTENANCE_PLAN.md in another terminal.')
        print('After closing all tools and an approved normal boot, type: '+RETURN)
        normal=prompt('handback> ').strip()==RETURN
        if not normal:raise ValueError('normal boot/closed-tools acknowledgement missing')
    except BaseException as e:
        error=type(e).__name__+': '+str(e)
    finally:
        if attempted:
            try:r.write_new(out/'lease_closing.json',{'created_utc':r.utc(),'error':error})
            except OSError as e:error=(error or '')+'; closing evidence failed: '+str(e)
            handback=restore(before,runner,identity,hash_file)
            handback['normal_app_boot_owner_confirmed']=normal
            handback['application_telemetry_valid']='NOT_VERIFIED_NOT_INFERRED_FROM_ACTIVE_SERVICE'
            for name,value in (('handback.json',handback),('lease_closed.json',{'created_utc':r.utc(),'error':error,'handback':handback})):
                try:r.write_new(out/name,value)
                except OSError as e:error=(error or '')+'; evidence failed: '+str(e)
    if error or not handback or not handback['bridge_restored'] or not handback['ai_api_unchanged_active'] or not normal:
        raise ValueError('MAINTENANCE_NOT_ACCEPTED; retain evidence and follow manual handback: '+str(error or handback))
    return handback

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',choices=(ACK,));p.add_argument('--approval',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    if not a.execute:
        print(json.dumps({'mode':'PLAN_ONLY','would_stop_only_user_unit':r.UNIT,'device_commands_automatic':False,
            'requires':'separate future owner approval, physical gates, NEW evidence directory',
            'APP_FLASH':'NO_GO'},indent=2));return
    if sys.platform!='linux' or not a.approval or not a.output:raise ValueError('USER-run Linux + approval + NEW output required')
    approved=approval(a.approval)
    import fcntl
    # Single maintenance coordinator; separate from the existing Bridge DB lock.
    with (r.HERE/'.read-window.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        out=r.new_dir(a.output)
        def interrupted(signum,frame):raise KeyboardInterrupt('signal '+str(signum))
        for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):signal.signal(sig,interrupted)
        signal.signal(signal.SIGALRM,interrupted)
        expires=datetime.strptime(approved['valid_until_utc'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        signal.alarm(max(1,min(1800,int((expires-datetime.now(timezone.utc)).total_seconds()))))
        result=lease(out,approved)
        print(json.dumps(result,indent=2))

if __name__=='__main__':main()
