"""Python3.6 checked factory flash plan; --apply never uses a stub/erase-all."""
import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

REAL_ENVS=("esp32s3_16mb_no_psram_hw_safe_uart","diag_i2c","diag_rtc","diag_hx711",
           "diag_food_sensor","diag_water_sensor","diag_oled_button_buzzer")


def digest(path):
    value=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): value.update(chunk)
    return value.hexdigest()


def plan(image,expected_hash,profile,port,application_only=False):
    image=Path(image).resolve()
    if profile not in REAL_ENVS: raise ValueError("only real no-PSRAM safe/diagnostic profiles may be deployed")
    required_name="firmware.bin" if application_only else "firmware.factory.bin"
    limit=6553600 if application_only else 16*1024*1024
    if image.name!=required_name or not image.is_file() or not 0<image.stat().st_size<=limit:
        raise ValueError("explicit bounded "+required_name+" file required")
    if not re.match(r"^[a-fA-F0-9]{64}$",expected_hash) or digest(image)!=expected_hash.lower():
        raise ValueError("SHA256 mismatch/missing; use the Windows deploy manifest hash")
    with image.open("rb") as stream:
        if stream.read(1)!=b"\xe9": raise ValueError("factory image must start with an ESP bootloader image at0x0")
    if not port.startswith(("/dev/ttyACM","/dev/ttyUSB","/dev/serial/by-id/")):
        raise ValueError("explicit observed Linux serial node required")
    prefix=[sys.executable,"-m","esptool","--chip","esp32s3","--port",port,"--baud","115200","--no-stub"]
    offset="0x10000" if application_only else "0x0"
    return {"schema_version":1,"profile":profile,"image":str(image),"sha256":expected_hash.lower(),
        "image_bytes":image.stat().st_size,"port":port,"application_only":application_only,"commands":[prefix+["flash_id"],
        prefix+["write_flash",offset,str(image)],prefix+["verify_flash",offset,str(image)]],
        "erase_all":False,"range_notice":"Application-only preserves NVS but requires an already matched16MB partition/bootloader. Factory writing covers NVS/gaps; backup/review before applying."}


def redact(output):
    return re.sub(r"(?i)(MAC:\s*)[0-9a-f:]{17}",r"\1<redacted>",output)


def execute(command,timeout=600):
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=timeout)
    output=redact(result.stdout); print(output)
    if result.returncode: raise RuntimeError("esptool failed; STOP, do not switch to stub or erase-all")
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image",required=True,type=Path); parser.add_argument("--sha256",required=True)
    parser.add_argument("--profile",required=True,choices=REAL_ENVS); parser.add_argument("--port",required=True)
    parser.add_argument("--apply",action="store_true"); parser.add_argument("--verify-only",action="store_true")
    parser.add_argument("--application-only",action="store_true")
    parser.add_argument("--allow-factory-overwrite",action="store_true")
    args=parser.parse_args()
    try:
        data=plan(args.image,args.sha256,args.profile,args.port,args.application_only)
        if not args.apply:
            print(json.dumps(dict(data,result="DRY_RUN",flashed=False),indent=2)); return 0
        if not args.verify_only and not args.application_only and not args.allow_factory_overwrite:
            raise ValueError("--apply factory write also requires --allow-factory-overwrite after covered-range review")
        if not Path(args.port).exists() or not stat.S_ISCHR(os.stat(args.port).st_mode) or not os.access(args.port,os.R_OK|os.W_OK):
            raise ValueError("serial node unavailable/not a character device/not accessible; close monitors/check dialout/node")
        info=execute(data["commands"][0],60)
        if not re.search(r"Detected flash size:\s*16\s*MB",info,re.I):
            raise ValueError("ROM preflight did not report16MB flash; STOP")
        if not args.verify_only: execute(data["commands"][1])
        execute(data["commands"][2])
        print(json.dumps({"result":"VERIFY_COMMAND_PASSED","flashed":not args.verify_only,
            "profile":args.profile,"sha256":args.sha256.lower(),"stub_used":False,"hardware_milestone_awarded":False},indent=2))
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print("FLASH_ABORTED: "+str(exc),file=sys.stderr); return 2


if __name__=="__main__": sys.exit(main())
