"""Backup-recovery fakes; no real port, reset, service action or installer."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest
KIT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(KIT/'tools'))
import backup_recovery as recovery
import flash_prepare as flash
from image_layout import FLASH_SIZE,sha
from test_tools import synthetic_backup,synthetic_receipt,synthetic_boot_review

def plan(tmp_path,chunk=1048576):
    folder=tmp_path/'NEW_SESSION'
    recovery.create_plan(folder,'00:11:22:33:44:55','COM99',sys.executable,chunk)
    return folder
def fake_reader(argv):
    if '-c' in argv:return 0,b'4.8.1\n'
    size=int(argv[-2],0);offset=int(argv[-3],0)
    Path(argv[-1]).write_bytes(bytes([(offset//1048576)%256])*size)
    return 0,b'esptool.py v4.8.1\nChip is ESP32-S3 (revision v0.2)\nMAC: 00:11:22:33:44:55\nRead complete\n'
def read_pair(folder,index,runner=fake_reader):
    for name in ('a','b'):
        result=recovery.take_read(folder,index,name,execute=True,confirm='OWNER_READ_ONLY_BACKUP',rom_ready=True,runner=runner)
        assert result['complete']
def complete(tmp_path,monkeypatch):
    folder=plan(tmp_path);monkeypatch.setattr(recovery,'windows_host',lambda:True)
    for index in range(16):read_pair(folder,index)
    return folder

def test_64k_plan_covers_boundary_and_known_probe_addresses(tmp_path):
    folder=plan(tmp_path,65536);p=recovery.load_plan(folder)
    assert len(p['chunks'])==256
    assert p['chunks'][32]['offset']==0x200000 and p['chunks'][-1]['offset']==0xff0000
    assert p['chunks'][-1]['offset']+p['chunks'][-1]['size']==FLASH_SIZE
    assert p['transport']=='STUB' and p['before']==p['after']=='no_reset'
def test_plan_does_not_overwrite_existing_evidence(tmp_path):
    folder=tmp_path/'existing';folder.mkdir();(folder/'part_00.bin').write_bytes(b'owner probe')
    with pytest.raises(ValueError):recovery.create_plan(folder,'00:11:22:33:44:55','COM99',sys.executable)
    assert (folder/'part_00.bin').read_bytes()==b'owner probe'
def test_default_read_only_produces_argv_no_process_or_files(tmp_path):
    folder=plan(tmp_path)
    def forbidden(*a):pytest.fail('default plan executed process')
    result=recovery.take_read(folder,2,'a',runner=forbidden)
    assert result['mode']=='PLAN_ONLY' and not result['device_opened']
    assert 'read_flash' in result['argv'] and '--flash_size' in result['argv']
    assert not (folder/'reads').exists() and not any(x in result['argv'] for x in ('write_flash','erase_flash','--no-stub'))
def test_execute_requires_explicit_owner_rom_confirmation(tmp_path):
    folder=plan(tmp_path)
    with pytest.raises(ValueError):recovery.take_read(folder,0,'a',execute=True,runner=lambda a:pytest.fail('called'))
def test_failed_read_preserved_and_never_overwritten(tmp_path,monkeypatch):
    folder=plan(tmp_path);monkeypatch.setattr(recovery,'windows_host',lambda:True)
    def bad(argv):
        if '-c' in argv:return 0,b'4.8.1\n'
        Path(argv[-1]).write_bytes(b'truncated');return 2,b'Invalid head of packet (0x6F)'
    result=recovery.take_read(folder,2,'a',execute=True,confirm='OWNER_READ_ONLY_BACKUP',rom_ready=True,runner=bad)
    assert not result['complete'] and result['returncode']==2
    path=folder/result['binary'];assert path.read_bytes()==b'truncated'
    with pytest.raises(ValueError,match='exists'):recovery.take_read(folder,2,'a',execute=True,confirm='OWNER_READ_ONLY_BACKUP',rom_ready=True,runner=bad)
    assert path.read_bytes()==b'truncated'
def test_tool_version_and_mac_are_pinned(tmp_path,monkeypatch):
    folder=plan(tmp_path);monkeypatch.setattr(recovery,'windows_host',lambda:True)
    with pytest.raises(ValueError,match='4.8.1'):recovery.take_read(folder,0,'a',execute=True,confirm='OWNER_READ_ONLY_BACKUP',rom_ready=True,runner=lambda a:(0,b'3.3.3\n'))
    def other(argv):
        code,text=fake_reader(argv)
        return code,text.replace(b'00:11:22:33:44:55',b'00:11:22:33:44:66')
    assert not recovery.take_read(folder,0,'a',execute=True,confirm='OWNER_READ_ONLY_BACKUP',rom_ready=True,runner=other)['complete']
def test_full_two_pass_assembly_and_receipt_no_physical_acceptance(tmp_path,monkeypatch):
    folder=complete(tmp_path,monkeypatch);out=tmp_path/'full.bin';receipt=tmp_path/'verified.json'
    result=recovery.assemble(folder,out,receipt,True)
    assert out.stat().st_size==FLASH_SIZE and result['coverage_bytes']==FLASH_SIZE
    assert result['two_independent_passes_match'] and not result['physical_pass'] and not result['flash_write_authorized']
    assert recovery.validate_receipt(out,receipt)['sha256']==sha(out)
    with pytest.raises(ValueError,match='NEW'):recovery.assemble(folder,out,receipt,True)
def test_gap_cannot_be_padded_with_ff(tmp_path,monkeypatch):
    folder=plan(tmp_path);monkeypatch.setattr(recovery,'windows_host',lambda:True);read_pair(folder,0)
    out=tmp_path/'full.bin'
    with pytest.raises(ValueError,match='coverage'):recovery.assemble(folder,out,tmp_path/'r.json',True)
    assert not out.exists()
def test_changed_independent_pass_rejected(tmp_path,monkeypatch):
    folder=complete(tmp_path,monkeypatch)
    receipt=folder/'reads/pass_b/offset_00200000_try_1.json';r=recovery.read_json(receipt)
    data=folder/r['binary'];data.write_bytes(b'Q'*r['size']);r['binary_sha256']=sha(data);receipt.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='pass mismatch'):recovery.assemble(folder,tmp_path/'full.bin',tmp_path/'r.json',True)
def test_tampered_evidence_hash_rejected(tmp_path,monkeypatch):
    folder=complete(tmp_path,monkeypatch);p=folder/'reads/pass_a/offset_00000000_try_1.bin';p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='integrity'):recovery.assemble(folder,tmp_path/'full.bin',tmp_path/'r.json',True)
def test_owner_rom_continuity_review_not_inferred(tmp_path):
    folder=plan(tmp_path)
    with pytest.raises(ValueError,match='continuity'):recovery.assemble(folder,tmp_path/'full.bin',tmp_path/'r.json')
def test_plan_tampering_cannot_execute_non_read_operation(tmp_path):
    folder=plan(tmp_path);p=recovery.read_json(folder/'plan.json');p['argv']=['erase_flash']
    (folder/'plan.json').write_text(json.dumps(p))
    argv=recovery.take_read(folder,0,'a')['argv']
    assert 'read_flash' in argv and 'erase_flash' not in argv
def test_full_sized_unreceipted_file_is_not_accepted_for_flash(tmp_path):
    backup,layout=synthetic_backup(tmp_path)
    result=flash.make_plan('diag_four_ultrasonic','COM_TEST',backup,layout['app_offset'],True,True)
    assert not result['write_plan_available'] and 'RECEIPT' in result['blocker']
@pytest.mark.parametrize('style,write,option',[('v4','write_flash','--flash_mode'),('v5','write-flash','--flash-mode')])
def test_flash_options_follow_esptool_major_cli(tmp_path,style,write,option):
    backup,layout=synthetic_backup(tmp_path);receipt=synthetic_receipt(backup,tmp_path)
    review=synthetic_boot_review(backup,receipt,tmp_path,layout['app_offset'])
    result=flash.make_plan('diag_four_ultrasonic','COM_TEST',backup,layout['app_offset'],True,True,style=style,backup_receipt=receipt,running_partition_review=review)
    argv=result['application_write_command']
    assert write in argv and option in argv
    assert ('--flash-mode' if style=='v4' else '--flash_mode') not in argv
def test_inventory_is_readonly_no_implicit_address_inference(tmp_path):
    p=tmp_path/'part_00.bin';p.write_bytes(b'owner bytes');before=p.stat().st_mtime_ns
    result=recovery.inventory(tmp_path)
    assert len(result['files'])==1 and p.stat().st_mtime_ns==before
    assert result['full_backup_verified'] is False and result['old_files_modified'] is False
