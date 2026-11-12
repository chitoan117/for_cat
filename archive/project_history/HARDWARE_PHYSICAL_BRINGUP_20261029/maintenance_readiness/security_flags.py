"""Extract named ESP32-S3 flags from an EXISTING espefuse JSON file.
No esptool/serial imports. Never turns flags into flash authorization.
"""
from __future__ import print_function
import argparse
import json
from pathlib import Path
import readiness as r

NAMES=('MAC','SECURE_BOOT_EN','SPI_BOOT_CRYPT_CNT','SECURE_VERSION',
       'DIS_DOWNLOAD_MODE','ENABLE_SECURITY_DOWNLOAD','DIS_DOWNLOAD_MANUAL_ENCRYPT',
       'DIS_USB_SERIAL_JTAG_DOWNLOAD_MODE','DIS_USB_DOWNLOAD_MODE',
       'SECURE_BOOT_KEY_REVOKE0','SECURE_BOOT_KEY_REVOKE1','SECURE_BOOT_KEY_REVOKE2')

def extract(value):
    selected={}
    def walk(node):
        if isinstance(node,dict):
            for key,v in node.items():
                if key in NAMES:
                    if isinstance(v,dict):selected[key]={k:v[k] for k in ('value','readable','description') if k in v}
                    else:selected[key]={'value':v,'readable':'NOT_RECORDED'}
                else:walk(v)
        elif isinstance(node,list):
            for v in node:walk(v)
    walk(value)
    return {'kind':'EXISTING_EFUSE_FLAGS_NOT_POLICY_APPROVAL','flags':selected,
            'missing':[k for k in NAMES[:8] if k not in selected],
            'antirollback_counter_interpretation':'REVIEW_WITH_IDF_POLICY_NOT_RAW_IMAGE_INFERENCE',
            'APP_FLASH':'NO_GO_PENDING_REVIEW','physical_pass':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    if not a.source:
        print(json.dumps({'mode':'PLAN_ONLY','serial_opened':False,'next':'--source EXISTING_JSON [--output NEW_JSON]'}));return
    if not r.regular(a.source) or a.source.stat().st_size>2*1024*1024:raise ValueError('regular existing JSON <=2MiB required')
    result=extract(json.loads(a.source.read_text()));result['source_sha256']=r.sha(a.source)
    if a.output:r.write_new(a.output,result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
