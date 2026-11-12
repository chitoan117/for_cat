import hashlib
import json
from pathlib import Path
import queue
import struct
import sys
import types
import pytest
KIT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(KIT/'tools'))
from bridge_guard import BridgeGuard
import serial_evidence as serial
import flash_prepare as flash
from image_layout import partitions,FLASH_SIZE,app_partition
from image_layout import sha
from analyze_hx_log import analyze
from build_windows import pump_variant

class Service:
    def __init__(self,active=True):self.active=active;self.calls=[];self.fail_restore=False
    def __call__(self,argv):
        action=argv[-2];self.calls.append(action)
        if action=='stop':self.active=False
        if action=='start' and not self.fail_restore:self.active=True
        if action=='is-active':return {'code':0 if self.active else 3,'stdout':'active' if self.active else 'inactive','stderr':''}
        return {'code':0,'stdout':'','stderr':''}
def test_bridge_restores_after_capture_error():
    service=Service();guard=BridgeGuard(runner=service)
    with pytest.raises(OSError):
        with guard:
            assert not service.active
            raise OSError('fake serial read failure')
    assert service.active and guard.restored and service.calls[-2:]==['start','is-active']
def test_inactive_bridge_stays_inactive():
    service=Service(False);guard=BridgeGuard(runner=service)
    with guard:pass
    assert guard.restored and not service.active and 'start' not in service.calls
def test_restore_failure_is_not_success():
    service=Service();guard=BridgeGuard(runner=service)
    with pytest.raises(RuntimeError,match='restoration'):
        with guard:service.fail_restore=True
    assert not guard.restored
def test_unknown_scope_never_stops_or_opens_serial():
    guard=BridgeGuard(runner=lambda a:{'code':4,'stdout':'unknown','stderr':''})
    with pytest.raises(RuntimeError,match='unknown'):
        with guard:pytest.fail('entered unknown state')
    assert len(guard.history)==1

class FakeSerial:
    in_waiting=1
    def __init__(self,clock,lines=None):self.clock=clock;self.tx=[];self.opens=0;self.closes=0;self.is_open=False;self.lines=list(lines or [])
    def open(self):self.opens+=1;self.is_open=True
    def close(self):self.closes+=1;self.is_open=False
    def write(self,data):self.tx.append(data)
    def read(self,n):
        self.clock[0]+=.3
        return self.lines.pop(0) if self.lines else b'ASCII_DIAGNOSTIC_NOT_PHYSICAL_PASS\n'
def test_default_capture_sends_status_only_and_never_claims_pass(tmp_path):
    clock=[0.];io=FakeSerial(clock)
    result=serial.capture(io,tmp_path,'servo',5,lambda:clock[0])
    assert io.tx and set(io.tx)=={b'servo status\n'}
    assert result['physical_result']=='NOT_VERIFIED' and result['ack_receipt_is_physical_success'] is False
    assert (tmp_path/'serial_raw.bin').read_bytes()
@pytest.mark.parametrize('command',['servo arm YES','servo open','pump on 100','test CONFIRM','tare 15','save YES','reference CONFIRM','buzzer-driver ACTIVE_HIGH CONFIRM'])
def test_unattended_commands_cannot_trigger_or_calibrate(command):
    for profile in serial.PROFILES:assert serial.manual_command(profile,command) is None
def test_manual_electrical_ack_is_not_sensor_voltage_proof():
    assert serial.manual_command('sensors','ultra-select hc1 CONFIRM') is None
    assert serial.manual_command('sensors','ultra-select hc1 CONFIRM',electrical=True)=='ultra-select hc1 CONFIRM'
    assert serial.manual_command('buzzer','test CONFIRM',actuator=True)=='test CONFIRM'
    assert serial.manual_command('pump_inert','pump on 100',actuator=True) is None
    assert serial.manual_command('pump_active','pump on 501',actuator=True) is None
    assert serial.manual_command('servo','STOP')=='servo stop'
def test_user_observation_separate_from_physical_acceptance(tmp_path):
    clock=[0.];io=FakeSerial(clock);commands=queue.Queue()
    commands.put('OBSERVE audible two tones by owner');commands.put('SEND test CONFIRM')
    result=serial.capture(io,tmp_path,'buzzer',5,lambda:clock[0],commands)
    assert set(io.tx)=={b'status\n'} and result['physical_result']=='NOT_VERIFIED'
    records=[json.loads(s) for s in (tmp_path/'records.jsonl').read_text().splitlines()]
    assert any(r['kind']=='USER_OBSERVED' for r in records) and any(r['kind']=='USER_COMMAND_REJECTED' for r in records)
@pytest.mark.parametrize('fail',[False,True])
def test_real_capture_entry_one_open_and_finally_restore_with_fake_io(tmp_path,monkeypatch,fail):
    service=Service();clock=[0.];io=FakeSerial(clock)
    if fail:
        def bad_read(n):raise OSError('injected failure')
        io.read=bad_read
    monkeypatch.setattr(serial,'operator_host',lambda:True)
    monkeypatch.setattr(serial,'BridgeGuard',lambda **kw:BridgeGuard(runner=service))
    monkeypatch.setattr(serial,'command',lambda argv:{'code':1,'stdout':'','stderr':''})
    monkeypatch.setitem(sys.modules,'serial',types.SimpleNamespace(Serial=lambda **kw:io))
    original=serial.capture
    def fake_clock_capture(port,folder,profile,seconds,*args):return original(port,folder,profile,seconds,lambda:clock[0])
    monkeypatch.setattr(serial,'capture',fake_clock_capture)
    output=tmp_path/'new_evidence'
    monkeypatch.setattr(sys,'argv',['serial_evidence.py','--profile','sensors','--output',str(output),'--seconds','5','--execute','--confirm','OWNER_SUPERVISED_SERIAL'])
    if fail:
        with pytest.raises(SystemExit):serial.main()
    else:serial.main()
    data=json.loads((output/'session.json').read_text())
    assert io.opens==io.closes==1 and service.active and data['bridge_original_state_restored']
    assert data['physical_result']=='NOT_VERIFIED'

def test_all_measurements_not_just_endpoints_and_not_display_deadband():
    values=[-.131398,.7,-.122004]
    lines=[json.dumps({'mode':'HX711_REFERENCE','valid':True,'measurement_grams':v,'display_grams':0,'monotonic_ms':1000+i*300}) for i,v in enumerate(values)]
    lines.append(json.dumps({'mode':'HX711_REFERENCE','valid':False,'measurement_grams':None}))
    result=analyze(lines)
    assert result['sample_count']==3 and result['max']==.7 and result['min']==-.131398 and result['invalid_count']==1
    assert result['physical_pass'] is False and not result['display_deadband_used_for_acceptance']
def test_full_status_is_not_an_extra_independent_hx_sample(tmp_path):
    clock=[0.];lines=[json.dumps({'mode':'HX711_REFERENCE','valid':True,'measurement_grams':.1,'calibration_source':'RAM_ONLY'}).encode()+b'\n',
        json.dumps({'mode':'HX711_REFERENCE','valid':True,'measurement_grams':.2,'monotonic_ms':100}).encode()+b'\n']
    result=serial.capture(FakeSerial(clock,lines),tmp_path,'hx_reference_legacy',5,lambda:clock[0])
    assert result['measurement_grams_all_samples']['count']==1

def test_flash_plan_missing_backup_never_contains_write(tmp_path):
    plan=flash.make_plan('diag_four_ultrasonic','COM_TEST',tmp_path/'missing.bin')
    assert not plan['write_plan_available'] and 'application_write_command' not in plan
    assert 'read-flash' in plan['full_backup_command'] and 'erase_flash' not in json.dumps(plan['full_backup_command'])
def synthetic_backup(tmp_path,profile='diag_four_ultrasonic'):
    folder,layout=flash.artifact(profile);data=bytearray(b'\xff'*FLASH_SIZE)
    # Synthetic full image populated from known offline artifacts, NOT a device read.
    boot=(folder/'bootloader.bin').read_bytes();data[:len(boot)]=boot;table=(folder/'partitions.bin').read_bytes()
    at=layout['partition_table_offset'];data[at:at+len(table)]=table
    app=layout['app_offset'];image=(folder/'firmware.bin').read_bytes();data[app:app+len(image)]=image
    p=tmp_path/'SYNTHETIC_FULL_FLASH_NOT_HARDWARE.bin';p.write_bytes(data)
    return p,layout
def synthetic_receipt(backup,tmp_path):
    # Local test fixture only, never evidence of a real device read.
    digest=sha(backup);p=tmp_path/'SYNTHETIC_RECEIPT.json'
    p.write_text(json.dumps({'kind':'FORCAT_VERIFIED_FLASH_BACKUP_V1','bytes':FLASH_SIZE,'coverage_bytes':FLASH_SIZE,
        'contiguous_from_zero':True,'two_independent_passes_match':True,'rom_continuity':'OWNER_REVIEWED',
        'device_id':'00:11:22:33:44:55','sha256':digest,'physical_pass':False,
        'ranges':[{'offset':0,'size':FLASH_SIZE,'sha256':digest,'pass_a':'SYNTHETIC_a.bin','pass_b':'SYNTHETIC_b.bin'}]}))
    return p
def synthetic_boot_review(backup,receipt,tmp_path,offset):
    from physical_acceptance import boot_gate
    log=tmp_path/'SYNTHETIC_running_partition.log';log.write_text('RUNNING_PARTITION_OFFSET='+hex(offset))
    evidence=tmp_path/'SYNTHETIC_boot_evidence.json'
    evidence.write_text(json.dumps({'backup_sha256':sha(backup),'evidence_kind':'RUNNING_PARTITION_OBSERVATION',
        'observer':'SYNTHETIC_TEST_ONLY','log_file':str(log),'running_app_offset':offset}))
    review=tmp_path/'SYNTHETIC_boot_review.json';review.write_text(json.dumps(boot_gate(backup,receipt,evidence)))
    return review
def test_flash_offsets_from_real_artifacts_and_matching_backup_no_nvs_write(tmp_path):
    backup,layout=synthetic_backup(tmp_path);rollback=tmp_path/'rollback.bin'
    receipt=synthetic_receipt(backup,tmp_path)
    review=synthetic_boot_review(backup,receipt,tmp_path,layout['app_offset'])
    plan=flash.make_plan('diag_four_ultrasonic','COM_TEST',backup,layout['app_offset'],True,True,rollback,backup_receipt=receipt,running_partition_review=review)
    assert plan['write_plan_available'] and not plan['nvs_or_partition_write_planned']
    assert plan['application_write_command'][-2]==hex(layout['app_offset'])
    assert rollback.stat().st_size==layout['application_partition']['size']
    assert not plan['physical_pass']
    with pytest.raises(FileExistsError):flash.make_plan('diag_four_ultrasonic','COM_TEST',backup,layout['app_offset'],True,True,rollback,backup_receipt=receipt,running_partition_review=review)
def test_unknown_boot_bank_and_ram_power_ack_block_write(tmp_path):
    backup,layout=synthetic_backup(tmp_path)
    receipt=synthetic_receipt(backup,tmp_path)
    bank=flash.make_plan('diag_four_ultrasonic','COM_TEST',backup,backup_receipt=receipt)
    assert not bank['write_plan_available'] and 'BOOT_BANK' in bank['blocker']
    ack=flash.make_plan('diag_four_ultrasonic','COM_TEST',backup,layout['app_offset'],backup_receipt=receipt)
    assert not ack['write_plan_available'] and 'RAM_LOSS' in ack['blocker']
def test_backup_md5_corruption_never_generates_write(tmp_path):
    backup,layout=synthetic_backup(tmp_path);data=bytearray(backup.read_bytes());data[layout['partition_table_offset']+20]^=1;backup.write_bytes(data)
    receipt=synthetic_receipt(backup,tmp_path)
    with pytest.raises(ValueError,match='MD5'):flash.make_plan('diag_four_ultrasonic','COM_TEST',backup,layout['app_offset'],True,True,backup_receipt=receipt)
def test_pump_never_selects_unknown_polarity(tmp_path):
    with pytest.raises(ValueError):pump_variant(0,None)
    observation=tmp_path/'USER_OBSERVED.json';observation.write_text('{"USER_OBSERVED":{"f5305s_off_level":null}}')
    with pytest.raises(ValueError):pump_variant(1,observation)
    observation.write_text('{"USER_OBSERVED":{"f5305s_off_level":0,"boot_off_verified":true,"observer":"SYNTHETIC_TEST_ONLY"}}')
    assert pump_variant(0,observation)=='diag_pump_bench_active_high'
    with pytest.raises(ValueError):pump_variant(1,observation)
@pytest.mark.parametrize('reported_off',[0,1])
def test_active_pump_tx_requires_status_polarity_matching_owner_observation(tmp_path,reported_off):
    clock=[0.];io=FakeSerial(clock,[('PUMP_BENCH_STATUS GPIO7_off_level='+str(reported_off)+' state=DISARMED\n').encode()])
    commands=queue.Queue();commands.put('OBSERVE SYNTHETIC_TEST_ONLY primed')
    commands.put('SEND pump arm YES');commands.put('SEND pump on 20')
    result=serial.capture(io,tmp_path,'pump_active',5,lambda:clock[0],commands,False,True,expected_pump_off=1)
    assert (b'pump on 20\n' in io.tx)==(reported_off==1)
    assert result['physical_result']=='NOT_VERIFIED'
