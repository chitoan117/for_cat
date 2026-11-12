"""New maintenance logic ONLY: fake services/holders; no real subprocess/device."""
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import readiness as r
import serial_window as w
import security_flags as s
import app_plan as a

def props(pid,active=True):
    return {'LoadState':'loaded','ActiveState':'active' if active else 'inactive',
        'SubState':'running' if active else 'dead','MainPID':str(pid if active else 0),
        'ExecStart':r.EXE,'FragmentPath':'/TEST/bridge.service','DropInPaths':'',
        'Restart':'on-failure','UnitFileState':'enabled','NeedDaemonReload':'no','ControlGroup':'/SYNTHETIC_TEST_ONLY'}
def before():
    return {'bridge':props(7001),'ai':props(10),'api':props(11),'ai_unit':r.AI,'api_unit':r.API,
        'holders':[7001],'device':r.PORT,'executable':r.EXE,'running_executable_sha256':'TEST_DIGEST',
        'usb':{'ID_VENDOR_ID':'1a86','ID_SERIAL_SHORT':'5C85066678'},'inspection_errors':[], 'preflight_issues':[]}
class Fake:
    def __init__(self):self.active=True;self.pid=7001;self.calls=[];self.busy=False;self.fail_stop=False;self.config_change=False
    def __call__(self,argv):
        self.calls.append(argv)
        code=0;out='';err=''
        if argv[:3]==['systemctl','--user','show']:
            unit=argv[3];v=props(self.pid,self.active) if unit==r.UNIT else props(10 if unit==r.AI else 11)
            if self.config_change and unit==r.UNIT:v['ExecStart']='USER_CHANGED_EXECUTABLE'
            out='\n'.join(k+'='+v[k] for k in r.FIELDS)
        elif argv[:3]==['systemctl','--user','stop']:
            self.active=False;code=1 if self.fail_stop else 0
        elif argv[:3]==['systemctl','--user','start']:
            self.active=True;self.pid=7002
        elif argv==['fuser',r.PORT]:
            if self.busy:out='9999';err=r.PORT+':'
            elif self.active:out=str(self.pid);err=r.PORT+':'
            else:code=1
        else:raise AssertionError('Unexpected real-world operation: '+str(argv))
        return {'argv':argv,'code':code,'stdout':out,'stderr':err}

class Tests(unittest.TestCase):
    def test_assess_refreshes_historical_pid(self):self.assertEqual(r.assess(before()),[])
    def test_assess_rejects_wrong_usb_and_peer(self):
        b=before();b['usb']['ID_SERIAL_SHORT']='OTHER';b['ai']['ActiveState']='inactive'
        self.assertEqual(len(r.assess(b)),2)
    def test_assess_rejects_multiple_holders(self):
        b=before();b['holders']=[7001,7002];self.assertIn('SERIAL_OWNER_NOT_SOLE_CURRENT_MAINPID',r.assess(b))
    def test_fuser_free_is_only_clean_code1(self):
        f=Fake();f.active=False;self.assertEqual(r.holders(f)[0],[])
        with self.assertRaises(ValueError):r.holders(lambda args:dict(code=1,stdout='',stderr='Permission denied'))
    def test_fuser_unknown_diagnostic_refuses(self):
        with self.assertRaises(ValueError):r.holders(lambda args:dict(code=0,stdout='7001',stderr='unexpected warning'))
    def test_new_outputs_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=r.new_dir(Path(tmp)/'new');r.write_new(p/'data.json',{})
            with self.assertRaises(ValueError):r.new_dir(p)
            with self.assertRaises(FileExistsError):r.write_new(p/'data.json',{})
    def test_false_example_approval_cannot_execute(self):
        with self.assertRaises(ValueError):w.approval(r.HERE/'owner_read_approval.example.json')
    def test_approval_expiry_and_identity(self):
        v=json.loads((r.HERE/'owner_read_approval.example.json').read_text())
        for k in ('approved','echo_protection_evidence_reviewed','servo_pump_buzzer_power_isolated','HX711_RAM_loss_accepted','manual_normal_boot_and_handback_reviewed'):v[k]=True
        v.update(approved_by='SYNTHETIC_TEST',valid_until_utc='2026-10-29T12:00:00Z')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.json';p.write_text(json.dumps(v))
            self.assertTrue(w.approval(p,datetime(2026,10,29,11,tzinfo=timezone.utc))['approved'])
            with self.assertRaises(ValueError):w.approval(p,datetime(2026,10,29,13,tzinfo=timezone.utc))
            v['by_id']='OTHER';p.write_text(json.dumps(v))
            with self.assertRaises(ValueError):w.approval(p,datetime(2026,10,29,11,tzinfo=timezone.utc))
    def test_read_approval_cannot_authorize_flash(self):
        v=json.loads((r.HERE/'owner_read_approval.example.json').read_text());v.update(approved=True,approved_by='TEST',flash_authorized=True)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.json';p.write_text(json.dumps(v))
            with self.assertRaises(ValueError):w.approval(p)
    def test_restore_originally_inactive_never_starts(self):
        f=Fake();f.active=False;b=before();b['bridge']=props(0,False)
        result=w.restore(b,f,lambda:r.PORT,lambda _: 'TEST_DIGEST')
        self.assertTrue(result['bridge_restored']);self.assertFalse(any('start' in x for x in f.calls))
    def test_restore_refuses_busy_port(self):
        f=Fake();f.active=False;f.busy=True
        result=w.restore(before(),f,lambda:r.PORT,lambda _: 'TEST_DIGEST')
        self.assertTrue(result['manual_recovery_required']);self.assertFalse(any('start' in x for x in f.calls))
    def test_restore_refuses_changed_binary_or_config(self):
        for changed in ('binary','config'):
            f=Fake();f.active=False;f.config_change=changed=='config'
            result=w.restore(before(),f,lambda:r.PORT,lambda _: 'CHANGED')
            self.assertTrue(result['manual_recovery_required']);self.assertFalse(any('start' in x for x in f.calls))
    def test_lease_success_stops_and_restores_only_bridge(self):
        f=Fake()
        with tempfile.TemporaryDirectory() as tmp:
            result=w.lease(Path(tmp),{},f,before,lambda _:w.RETURN,lambda:r.PORT,lambda _:'TEST_DIGEST')
        self.assertTrue(result['bridge_restored']);self.assertTrue(result['ai_api_unchanged_active'])
        self.assertEqual([x for x in f.calls if 'start' in x or 'stop' in x],[['systemctl','--user','stop',r.UNIT],['systemctl','--user','start',r.UNIT]])
    def test_interrupt_attempts_handback(self):
        f=Fake()
        def interrupt(_):raise KeyboardInterrupt('SIMULATED')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):w.lease(Path(tmp),{},f,before,interrupt,lambda:r.PORT,lambda _:'TEST_DIGEST')
            self.assertTrue(json.loads((Path(tmp)/'handback.json').read_text())['bridge_restored'])
        self.assertTrue(f.active)
    def test_stop_failure_after_state_change_restores(self):
        f=Fake();f.fail_stop=True
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):w.lease(Path(tmp),{},f,before,lambda _:w.RETURN,lambda:r.PORT,lambda _:'TEST_DIGEST')
        self.assertTrue(f.active)
    def test_evidence_failure_cannot_skip_handback(self):
        f=Fake()
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'write_new',side_effect=OSError('SIMULATED_DISK_FAILURE')):
            with self.assertRaises(ValueError):w.lease(Path(tmp),{},f,before,lambda _:w.RETURN,lambda:r.PORT,lambda _:'TEST_DIGEST')
        self.assertTrue(f.active)
    def test_wrong_unit_recheck_prevents_stop(self):
        f=Fake();f.config_change=True
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):w.lease(Path(tmp),{},f,before,lambda _:w.RETURN,lambda:r.PORT,lambda _:'TEST_DIGEST')
        self.assertFalse(any('stop' in x for x in f.calls))
    def test_security_extractor_never_prints_key_blocks(self):
        raw={'BLOCK_KEY0':{'value':'SECRET_TEST_ONLY'},'SECURE_BOOT_EN':{'value':False,'readable':True}}
        result=s.extract(raw);self.assertNotIn('SECRET_TEST_ONLY',json.dumps(result));self.assertIn('SECURE_VERSION',result['missing'])
    def test_default_flash_review_withholds_argv(self):
        result=a.plan({});self.assertFalse(result['write_argv_available']);self.assertNotIn('write_argv',result)
    def test_unknown_security_and_offset_are_blockers(self):
        v=json.loads((r.HERE/'flash_review.example.json').read_text());why=a.blockers(v)
        self.assertIn('ACTUAL_BANK_NOT_CONFIRMED_APP0_NO_OFFSET_GUESS',why)
        self.assertTrue(any('UNSUPPORTED_OR_UNKNOWN_SECURITY_POLICY' in x for x in why))
    def test_all_default_entrypoints_are_side_effect_free(self):
        import contextlib,io
        import boot_capture
        for module in (r,w,s,a,boot_capture):
            with patch('sys.argv',['tool.py']),patch.object(r,'command',side_effect=AssertionError('subprocess forbidden')),contextlib.redirect_stdout(io.StringIO()) as out:
                module.main()
            self.assertIn('PLAN',out.getvalue())

if __name__=='__main__':unittest.main(verbosity=2)
