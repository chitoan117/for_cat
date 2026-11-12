"""Operator-only exclusive serial maintenance; restore original bridge state.
Importing does not call systemctl. All unit operations injectable for offline tests.
"""
import subprocess

def command(argv):
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=30)
    return {'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
class BridgeGuard:
    def __init__(self,scope='user',service='for-cat-esp32-bridge.service',runner=command):
        if scope not in ('user','system') or service!='for-cat-esp32-bridge.service':raise ValueError('explicit known bridge/scope required')
        self.prefix=['systemctl']+(['--user'] if scope=='user' else [])
        self.service=service;self.runner=runner;self.was_active=None;self.history=[];self.restored=False
    def call(self,action):
        result=self.runner(self.prefix+[action,self.service]);self.history.append({'action':action,**result});return result
    def restore(self):
        if self.was_active is True:
            result=self.call('start');state=self.call('is-active')
            self.restored=result['code']==0 and state['code']==0 and state['stdout'].strip()=='active'
        elif self.was_active is False:
            state=self.call('is-active');self.restored=state['code']==3 and state['stdout'].strip() in ('inactive','failed')
        return self.restored
    def __enter__(self):
        initial=self.call('is-active')
        if initial['code']==0 and initial['stdout'].strip()=='active':self.was_active=True
        elif initial['code']==3 and initial['stdout'].strip() in ('inactive','failed'):self.was_active=False
        else:raise RuntimeError('bridge service scope/state unknown; no serial opened')
        if self.was_active:
            try:
                if self.call('stop')['code']!=0:raise RuntimeError('bridge stop failed')
                state=self.call('is-active')
                if state['code']!=3 or state['stdout'].strip() not in ('inactive','failed'):raise RuntimeError('bridge did not stop')
            except BaseException:
                self.restore();raise
        return self
    def __exit__(self,kind,error,tb):
        if not self.restore():raise RuntimeError('bridge original state restoration NOT VERIFIED; inspect service manually') from error
        return False
