"""Offline ESP32 partition/image checks. No guessed flash offsets or serial IO."""
import hashlib
import struct
from pathlib import Path

FLASH_SIZE=16*1024*1024
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()
def partitions(blob):
    out=[];saw_md5=False
    for offset in range(0,min(len(blob),4096),32):
        entry=blob[offset:offset+32]
        if len(entry)<32:raise ValueError('short partition record')
        magic=struct.unpack_from('<H',entry)[0]
        if magic==0xffff:break
        if magic==0xebeb:
            if entry[16:]!=hashlib.md5(blob[:offset]).digest():raise ValueError('partition MD5 mismatch')
            saw_md5=True;break
        if magic!=0x50aa:raise ValueError('partition magic')
        _,kind,subtype,start,size,label,flags=struct.unpack('<HBBII16sI',entry)
        if size==0 or start+size>FLASH_SIZE or start%4096:raise ValueError('partition range')
        out.append({'type':kind,'subtype':subtype,'offset':start,'size':size,'label':label.split(b'\0')[0].decode('ascii'),'flags':flags})
    if not out or not saw_md5:raise ValueError('MD5-protected partition table required')
    ordered=sorted(out,key=lambda p:p['offset'])
    if any(a['offset']+a['size']>b['offset'] for a,b in zip(ordered,ordered[1:])):raise ValueError('partition overlap')
    return out
def image_header(blob):
    if len(blob)<24 or blob[0]!=0xe9:raise ValueError('ESP image magic/header')
    chip=struct.unpack_from('<H',blob,12)[0]
    if chip!=9:raise ValueError('not ESP32-S3 image')
    return {'chip_id':chip,'segments':blob[1],'flash_mode_code':blob[2],'flash_size_code':blob[3]>>4}
def app_partition(layout,offset):
    items=[p for p in layout if p['type']==0 and p['offset']==offset]
    if len(items)!=1:raise ValueError('application address not in partition table')
    return items[0]
def load_full_backup(path,partition_offset):
    path=Path(path)
    if not path.is_file() or path.stat().st_size!=FLASH_SIZE:raise ValueError('complete16MB backup required')
    data=path.read_bytes()
    # Old bootloader/table must be verified, not assumed compatible with new image.
    image_header(data[:24])
    table=partitions(data[partition_offset:partition_offset+4096])
    return data,table
