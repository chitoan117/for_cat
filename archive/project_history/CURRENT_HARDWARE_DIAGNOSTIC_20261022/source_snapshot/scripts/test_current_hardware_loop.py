"""Actual sensor-only setup/loop + Jetson parser, fake IO, no physical board."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"jetson"))
from bringup.sensor_monitor import parse_report

CASES=("missing","functional","faults")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if not args.binary.is_file() or not args.output.parent.is_dir():
        parser.error("binary or output parent missing")
    args.output.mkdir()
    records=[]
    for name in CASES:
        serial=args.output/(name+".serial.log")
        result=subprocess.run([str(args.binary.resolve()),name,str(serial)],capture_output=True,text=True,timeout=30)
        (args.output/(name+".execution.log")).write_text(result.stdout+result.stderr,encoding="utf-8")
        if result.returncode:
            raise RuntimeError(name+": "+result.stderr)
        receipt=json.loads(result.stdout)
        if receipt.get("case")!=name or receipt.get("result")!="PASS" or receipt.get("physical_hardware") is not False:
            raise RuntimeError("invalid software receipt")
        rows=[parse_report(line) for line in serial.read_bytes().splitlines() if line.startswith(b"{")]
        if not rows or any(row["mode"]!="diag_current_hardware" for row in rows):
            raise RuntimeError("current sensor reports missing")
        if name=="missing" and not all(row["grams"] is None and row["current_hardware"]["rtc_detected"] is False for row in rows):
            raise RuntimeError("missing sensors produced fake readiness")
        if name=="functional" and not any(row["current_hardware"]["pir_transition_count"]>0 and
                                       row["approach_distance_cm"] is not None and row["water_distance_cm"] is not None and
                                       row["current_hardware"]["weight_stable"] is True for row in rows):
            raise RuntimeError("normal synthetic roles not decoded")
        if name=="faults" and not any(row["current_hardware"]["operational_water_timeout_count"]>0 and
                                    row["current_hardware"]["weight_stable"] is False for row in rows):
            raise RuntimeError("fault/unstable evidence not decoded")
        receipt["parsed_reports"]=len(rows)
        records.append(receipt)
        print("PASS",name,receipt["assertions"],"assertions",len(rows),"Jetson-parsed reports")
    summary={"scope":"SOFTWARE_ONLY_REAL_SENSOR_LOOP_FAKE_IO","named_cases":len(CASES),
             "cpp_assertions":sum(row["assertions"] for row in records),
             "decoded_reports":sum(row["parsed_reports"] for row in records),
             "physical_status":"NOT_TESTED","actuator_gpio_touches":0,"cases":records}
    (args.output/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
