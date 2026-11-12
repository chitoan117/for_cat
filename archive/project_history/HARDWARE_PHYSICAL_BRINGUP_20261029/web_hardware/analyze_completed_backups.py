"""READ-ONLY actual A/B analysis, writes derived evidence only inside this folder."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;KIT=HERE.parent
sys.path.insert(0,str(KIT/'tools'))
from completed_backup_pair import validate_pair
from backup_recovery import new_json
from physical_acceptance import inspect_contents
from image_layout import sha

A=KIT.parent/'ESP32_FULL_BACKUP_20261029/esp32s3_flash_16mb.bin'
B=KIT.parent/'ESP32_FULL_BACKUP_20261029/esp32s3_flash_16mb_B.bin'
EXPECTED='56a04d58bd8063e64f6b043a6b91d2d412c64d75e563ee58d81a83666d9a8e16'
def main():
    receipt=validate_pair(A,B,EXPECTED)
    new_json(HERE/'accepted_backup_pair.json',receipt)
    data=A.read_bytes();analysis=inspect_contents(data,EXPECTED)
    for table in analysis['partition_candidates']:
        for app in table['apps']:
            offset=app['offset'];size=app['image'].get('image_bytes')
            if size:
                app['application_used_bytes_sha256']=__import__('hashlib').sha256(data[offset:offset+size]).hexdigest()
                app['contains_HX711_REFERENCE_literal']=b'HX711_REFERENCE' in data[offset:offset+size]
    new_json(HERE/'actual_backup_layout.json',analysis)
    print(json.dumps({'backup_AB':'PASS','bytes_each':receipt['bytes'],'sha256':EXPECTED,
        'bootloader':analysis['bootloader_at_rom_s3_offset0'],'tables':analysis['partition_candidates'],
        'active_boot_bank':analysis['active_boot_bank'],'flash_authorized':False},indent=2))
if __name__=='__main__':main()
