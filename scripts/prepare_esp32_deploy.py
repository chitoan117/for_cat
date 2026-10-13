"""Copy/hash only safe real-board build products for explicit Windows→Jetson transfer."""
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"jetson"))
from bringup.flash import REAL_ENVS


def package(profile,output):
    if profile not in REAL_ENVS: raise ValueError("no SIM/legacy/surrogate/active-actuator deploy bundle")
    output=Path(output)
    if output.exists(): raise FileExistsError("bundle exists; choose a new output path")
    build=ROOT/"esp32/.pio/build"/profile
    sources={name:build/name for name in ("bootloader.bin","partitions.bin","firmware.bin","firmware.factory.bin")}
    home=Path(os.environ.get("PLATFORMIO_CORE_DIR",str(Path.home()/".platformio")))
    sources["boot_app0.bin"]=home/"packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin"
    for name,path in sources.items():
        if not path.is_file(): raise ValueError("required build product missing: "+name)
    output.mkdir(parents=True)
    try:
        records=[]
        for name,path in sources.items():
            destination=output/name; shutil.copyfile(path,destination)
            sha=hashlib.sha256(destination.read_bytes()).hexdigest()
            records.append({"file":name,"bytes":destination.stat().st_size,"sha256":sha})
        receipt={"schema_version":1,"created_at":datetime.now(timezone.utc).isoformat(),"profile":profile,
            "chip":"ESP32-S3","flash_mb":16,"psram_used":False,"actuator_outputs_enabled":0,
            "mode":"ASCII_DIAGNOSTIC" if profile.startswith("diag_") else "FROZEN_UART_V1_HW_SAFE",
            "files":records,"flash_image":"firmware.factory.bin","flash_offset":"0x0","jetson_stub_allowed":False,
            "warning":"Factory covered sectors include NVS/gaps; explicit overwrite review required. No flash performed by packaging."}
        with (output/"deploy_manifest.json").open("x",encoding="utf-8") as stream: json.dump(receipt,stream,indent=2)
        return receipt
    except BaseException:
        shutil.rmtree(output); raise  # only newly owned bundle


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--env",required=True,choices=REAL_ENVS)
    parser.add_argument("--output",type=Path); args=parser.parse_args()
    folder=args.output or ROOT/".deploy"/(args.env+"_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    try: result=package(args.env,folder)
    except (ValueError,OSError) as exc: parser.exit(2,"DEPLOY_PACKAGE_FAILED: "+str(exc)+"\n")
    print(json.dumps({"directory":str(folder),"manifest":result},indent=2))


if __name__=="__main__": main()
