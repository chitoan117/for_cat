"""Exercise pump bench firmware against fake GPIO for inert and both polarities."""
import argparse
import json
from pathlib import Path
import subprocess

CASES=(("inert", "inert", 0, -1), ("high", "bounded", 1, 0),
       ("low", "bounded", 1, 1), ("reset", "reset", 1, 1))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("inert","high","low","reset"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if not args.output.parent.is_dir() or any(not getattr(args,name).is_file() for name,_,_,_ in CASES):
        parser.error("binary/output parent unavailable")
    args.output.mkdir()
    records=[]
    for name,test,active,off in CASES:
        path=args.output/(name+".serial.log")
        result=subprocess.run([str(getattr(args,name).resolve()),test,str(path)],
                              capture_output=True,text=True,timeout=30)
        (args.output/(name+".execution.log")).write_text(result.stdout+result.stderr,encoding="utf-8")
        if result.returncode:
            raise RuntimeError(name+": "+result.stderr)
        row=json.loads(result.stdout)
        text=path.read_text(encoding="utf-8")
        if row.get("host_active")!=active or row.get("host_off_level")!=off or \
                row.get("physical_hardware") is not False or row.get("result")!="PASS" or \
                "SERVO6 UNTOUCHED NO CAT/AUTO_WATER" not in text or \
                "physical_pump_off_verified=false" not in text:
            raise RuntimeError("invalid physical-status/polarity host receipt: "+name)
        if name=="inert" and ("mode=INERT_UNKNOWN_POLARITY" not in text or
                              "REJECTED_DISARMED" not in text):
            raise RuntimeError("inert profile was able to arm")
        if test=="bounded" and not all(x in text for x in
              ("action=ON result=ACCEPTED", "AUTO_TIMEOUT_OFF", "REJECTED_LIMIT")):
            raise RuntimeError("timeout/bounds missing in "+name)
        records.append(row)
        print("PASS",name,row["assertions"],"fakeGPIO assertions")
    summary={"scope":"HOST_ACTUAL_PUMP_LOOP_FAKE_GPIO_ONLY","named_cases":len(records),
             "cpp_assertions":sum(row["assertions"] for row in records),
             "physical_status":"NOT_TESTED","pump_off_electrical_polarity_approved":False,
             "files":records}
    (args.output/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
