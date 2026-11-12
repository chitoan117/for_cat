"""All backup/image/UART examples are local synthetic files, never a live backup."""
import binascii
import hashlib
import json
from pathlib import Path
import struct
import sys
import pytest
KIT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(KIT/'tools'))
import physical_acceptance as accept
import flash_prepare as flash
from image_layout import FLASH_SIZE,sha
from test_tools import synthetic_backup,synthetic_receipt,synthetic_boot_review

MAC='00:11:22:33:44:55'
LOG='esptool.py v4.8.1\nChip is ESP32-S3 (revision v0.2)\nMAC: '+MAC+'\nRead 16777216 bytes at 0x00000000\nFULL_BACKUP_READ_PASS\n'
def completed_pair(tmp_path):
    a,layout=synthetic_backup(tmp_path);b=tmp_path/'B.bin';b.write_bytes(a.read_bytes())
    ra=tmp_path/'A.json';rb=tmp_path/'B.json'
    for label,binary,record in [('A',a,ra),('B',b,rb)]:
        log=tmp_path/(label+'.log');log.write_text(LOG)
        accept.record(label,binary,log,record,0,True,MAC,'ROM')
    return a,b,ra,rb,layout
def paired(tmp_path):
    a,b,ra,rb,layout=completed_pair(tmp_path);receipt=tmp_path/'pair.json'
    accept.compare_pair(ra,rb,receipt,True)
    return a,receipt,layout
def test_active_or_unknown_exit_refused_before_any_path_access():
    class MustNotTouch:
        def __fspath__(self):raise AssertionError('touched active file')
    for finished,code in [(False,0),(True,None),(True,2),(True,True)]:
        with pytest.raises(ValueError,match='reader must'):accept.record('A',MustNotTouch(),MustNotTouch(),MustNotTouch(),code,finished,MAC)
def test_completed_partial_suffix_preserved_and_full_pair_accepted_locally(tmp_path):
    a,b,ra,rb,_=completed_pair(tmp_path);receipt=tmp_path/'pair.json'
    before=sha(a);r=accept.compare_pair(ra,rb,receipt,True)
    assert r['bytes']==FLASH_SIZE and r['two_independent_passes_match'] and not r['physical_pass']
    assert not r['flash_write_authorized'] and sha(a)==before
    from backup_recovery import validate_receipt
    assert validate_receipt(a,receipt)['sha256']==before
def test_missing_completion_marker_blocks_even_full_sized_file(tmp_path):
    a,_=synthetic_backup(tmp_path);log=tmp_path/'unfinished.log';log.write_text(LOG.replace('FULL_BACKUP_READ_PASS','').replace('Read 16777216 bytes at 0x00000000','Read progress...'))
    with pytest.raises(ValueError,match='completion'):accept.record('A',a,log,tmp_path/'A.json',0,True,MAC)
def test_truncated_read_not_padded(tmp_path):
    a=tmp_path/'A.partial';a.write_bytes(b'not full');log=tmp_path/'A.log';log.write_text(LOG)
    with pytest.raises(ValueError,match='16777216'):accept.record('A',a,log,tmp_path/'A.json',0,True,MAC)
    assert a.read_bytes()==b'not full'
def test_mismatch_keeps_both_and_no_receipt(tmp_path):
    a,b,ra,rb,_=completed_pair(tmp_path);data=bytearray(b.read_bytes());data[-1]^=1;b.write_bytes(data)
    # New completed B record reflects a genuinely different independent read.
    rb.unlink();accept.record('B',b,tmp_path/'B.log',rb,0,True,MAC)
    with pytest.raises(ValueError,match='SHA256 mismatch'):accept.compare_pair(ra,rb,tmp_path/'pair.json',True)
    assert a.exists() and b.exists() and not (tmp_path/'pair.json').exists()
def test_same_file_or_log_is_not_independent_pass(tmp_path):
    a,b,ra,rb,_=completed_pair(tmp_path);r=json.loads(rb.read_text());r['backup']=str(a);rb.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='independent'):accept.compare_pair(ra,rb,tmp_path/'pair.json',True)
def test_rom_b_plan_does_not_execute_or_overwrite_a(tmp_path):
    a,b,ra,rb,_=completed_pair(tmp_path)
    with pytest.raises(ValueError,match='NEW B'):accept.plan_b(ra,a,'python.exe')
    plan=accept.plan_b(ra,tmp_path/'B_NEW.partial','python.exe')
    assert '--no-stub' in plan['argv'] and 'read_flash' in plan['argv'] and '--flash_size' in plan['argv']
    assert plan['execution_implemented'] is False and not (tmp_path/'B_NEW.partial').exists()
def test_probe_addresses_are_explicit_and_comparison_does_not_write(tmp_path):
    a,receipt,_=paired(tmp_path);p=tmp_path/'probe.bin';p.write_bytes(a.read_bytes()[0x200000:0x210000]);manifest=tmp_path/'probes.json'
    manifest.write_text(json.dumps({'probes':[{'file':str(p),'offset':0x200000,'bytes':65536,'read_exit_code':0,'offset_source':'OWNER_REVIEWED_COMMAND_LOG'}]}))
    result=accept.compare_probes(a,receipt,manifest);assert not result['any_mismatch'] and not result['old_files_modified']
    data=json.loads(manifest.read_text());del data['probes'][0]['offset_source'];manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='filename'):accept.compare_probes(a,receipt,manifest)
def test_actual_table_and_ota_offsets_are_scanned_not_assumed(tmp_path):
    # Make a synthetic table at0x9000, otadata at0x12000, OTA apps at0x20000/0x220000.
    folder=KIT/'artifacts/diag_four_ultrasonic';data=bytearray(b'\xff'*FLASH_SIZE)
    boot=(folder/'bootloader.bin').read_bytes();data[:len(boot)]=boot
    entries=[]
    for typ,sub,start,size,name in [(1,0,0x12000,8192,b'otadata'),(0,16,0x20000,0x200000,b'ota0'),(0,17,0x220000,0x200000,b'ota1')]:
        entries.append(struct.pack('<HBBII16sI',0x50aa,typ,sub,start,size,name,0))
    table=b''.join(entries);table+=b'\xeb\xeb'+b'\xff'*14+hashlib.md5(table).digest();data[0x9000:0x9000+len(table)]=table
    image=(folder/'firmware.bin').read_bytes();data[0x20000:0x20000+len(image)]=image
    crc=0x4743989a # ESP-IDF otadata CRC of little-endian ota_seq1, seed0xffffffff.
    assert binascii.crc32(struct.pack('<I',1),0xffffffff)&0xffffffff==crc
    struct.pack_into('<I',data,0x12000,1);struct.pack_into('<II',data,0x12000+24,2,crc)
    p=tmp_path/'SYNTHETIC_alt_layout.bin';p.write_bytes(data);receipt=synthetic_receipt(p,tmp_path)
    result=accept.inspect(p,receipt)
    assert len(result['partition_candidates'])==1
    table=result['partition_candidates'][0];assert table['table_offset']==0x9000
    assert table['ota_copies'][0]['offset']==0x12000 and table['ota_copies'][0]['record_crc_valid']
    assert table['ota_copies'][0]['sequence_mapped_candidate_offset']==0x20000
    assert table['apps'][0]['image']['image_integrity']=='VALID_LOCAL_BYTES'
    assert result['active_boot_bank'].startswith('NOT_VERIFIED') and not result['flash_authorized']
def test_rom_virtual_entry_is_not_actual_boot_bank_evidence(tmp_path):
    a,receipt,layout=paired(tmp_path);log=tmp_path/'boot.log';log.write_text('entry 0x403c8708\n')
    e=tmp_path/'evidence.json';e.write_text(json.dumps({'backup_sha256':sha(a),'evidence_kind':'RUNNING_PARTITION_OBSERVATION','observer':'TEST_ONLY','log_file':str(log),'running_app_offset':layout['app_offset']}))
    with pytest.raises(ValueError,match='actual loaded'):accept.boot_gate(a,receipt,e)
def test_boot_review_binds_backup_and_running_log_but_not_physical_success(tmp_path):
    a,receipt,layout=paired(tmp_path);review=synthetic_boot_review(a,receipt,tmp_path,layout['app_offset'])
    r=accept.validate_boot_review(a,review,layout['app_offset'],layout['partition_table_offset'])
    assert r['physical_pass'] is False and not r['flash_authorized']
    Path(r['evidence_log_file']).write_text('changed')
    with pytest.raises(ValueError,match='log changed'):accept.validate_boot_review(a,review,layout['app_offset'],layout['partition_table_offset'])
def test_flash_plan_remains_blocked_without_reviewed_running_partition(tmp_path):
    a,receipt,layout=paired(tmp_path)
    r=flash.make_plan('diag_four_ultrasonic','COM_TEST',a,layout['app_offset'],True,True,backup_receipt=receipt)
    assert not r['write_plan_available'] and 'RUNNING_PARTITION' in r['blocker']
def encoded_ack():
    frame=bytearray(b'\xa5\x5a\x01'+struct.pack('<I',3)+b'\x06'+struct.pack('<H',1)+b'\x00');crc=0xffff
    for byte in frame[2:]:
        crc^=byte<<8
        for _ in range(8):crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    return bytes(frame)+struct.pack('<H',crc)
def test_capture_crc_duplicate_ack_never_infers_feed_success():
    frame=encoded_ack();bad=bytearray(frame);bad[-1]^=1
    r=accept.uart_audit(b'ASCII\n'+frame+frame+bad)
    assert len(r['valid_crc_frames'])==2 and r['duplicates']==1 and r['crc_errors']==1
    assert r['valid_crc_frames'][0]['meaning']=='ACK_RECEIPT_NOT_FEED_SUCCESS'
    assert r['transmitted_commands']==0 and r['feed_success_inferred'] is False
def test_ascii_sensor_protocol_is_not_fabricated_crc_pass():
    r=accept.uart_audit(b'{"mode":"diag_current_hardware"}\n')
    assert not r['valid_crc_frames'] and r['protocol']=='NO_VALID_BINARY_FRAME_ASCII_OR_UNKNOWN'
