"""Python3.6 OpenCV V4L2 test/canonical session bridge; physical IO explicitly opt-in."""
import argparse
import hashlib
import json
import math
import multiprocessing as mp
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from ai.label_schema import IDENTITY,BEHAVIOR
from ai.sampling import SamplingPolicy


def acquire(options,folder=None,stop=None,factory=None,clock=time.monotonic):
    import cv2  # system3.6 custom bindings preserved; no GPU runtime imported
    cap=(factory or cv2.VideoCapture)(options["device"],cv2.CAP_V4L2)
    started=clock(); frames=failures=attempts=0; actual=None; rows=[]; stored=0
    stream_hash=hashlib.sha256(); policy=SamplingPolicy(options["interval"],options["minimum_spacing"])
    reason="FRAME_LIMIT"; actual_fps=None; actual_fourcc=None
    recorded_at=datetime.now(timezone.utc).isoformat()
    try:
        if not cap.isOpened(): raise ValueError("explicit camera could not open")
        cap.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*options["fourcc"]))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,options["width"]); cap.set(cv2.CAP_PROP_FRAME_HEIGHT,options["height"])
        cap.set(cv2.CAP_PROP_FPS,options["fps"]); cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
        actual_fps=float(cap.get(cv2.CAP_PROP_FPS)); actual_fourcc=int(cap.get(cv2.CAP_PROP_FOURCC))
        if not math.isfinite(actual_fps) or actual_fps<=0: actual_fps=None
        if folder is not None: (folder/"processed").mkdir()
        for _ in range(100000):
            if stop is not None and stop.is_set(): reason="USER_STOP"; break
            if clock()-started>=options["seconds"]: reason="DURATION_LIMIT"; break
            ok,frame=cap.read(); attempts+=1
            if not ok or frame is None:
                failures+=1
                if failures>=3: reason="CAMERA_READ_FAILURE"; break
                continue
            frames+=1; height,width=frame.shape[:2]; actual=[width,height]
            if actual!=[options["width"],options["height"]]: raise ValueError("actual resolution differs from requested reviewed mode")
            elapsed=clock()-started
            if folder is not None and policy.due(elapsed):
                ok,encoded=cv2.imencode(".jpg",frame)
                if not ok: raise ValueError("frame encode failed")
                data=encoded.tobytes()
                if len(data)>8000000 or stored+len(data)>100000000: reason="STORAGE_BUDGET"; break
                sha=policy.select(elapsed,data)
                if sha is not None:
                    identifier="s-"+sha[:24]; relative="processed/"+identifier+".jpg"
                    with (folder/relative).open("xb") as output: output.write(data)
                    stream_hash.update(data); stored+=len(data)
                    row={"sample_id":identifier,"session_id":options["session_id"],"source_video":"","timestamp":None,
                        "source_offset_seconds":elapsed,"identity_label":None,"behavior_label":None,"usable":False,
                        "hash":sha,"source_hash":None,"path":relative}
                    row.update(dict((key,options.get(key)) for key in ("food_type","lighting","distance","view_angle","occlusion")))
                    rows.append(row)
            if (len(rows) if folder is not None else frames)>=options["frames"]: reason="FRAME_LIMIT"; break
    finally: cap.release()
    elapsed=max(clock()-started,1e-9)
    result={"result":"FRAMES_OBSERVED" if frames and not failures else "FAIL","frames_received":frames,"read_failures":failures,
        "seconds":elapsed,"measured_fps":frames/elapsed,"actual_resolution":actual,"reported_fps":actual_fps,
        "actual_fourcc_code":actual_fourcc,"requested_fourcc":options["fourcc"],"backend":"V4L2","stop_reason":reason,
        "actual_io_requires_operator_evidence":True,"milestone_automatically_awarded":False}
    if folder is not None:
        sha=stream_hash.hexdigest() if rows else None
        manifest={"schema_version":1,"session_id":options["session_id"],"recorded_at":recorded_at,
            "camera_source":"CAMERA","camera_device":options["device"],"resolution":actual,"fps":actual_fps,
            "identity_target":options["identity"],"behavior_target":options["behavior"],"usable":False,
            "source_hash":sha,"source_hash_kind":"SAMPLED_FRAME_STREAM_SHA256","duration_seconds":options["seconds"],
            "sampling_interval_seconds":options["interval"],"minimum_spacing_seconds":options["minimum_spacing"],
            "max_frames":options["frames"],"sample_count":len(rows),"stop_reason":reason,"capture_backend":"V4L2",
            "capture_fourcc":options["fourcc"],"requested_resolution":[options["width"],options["height"]],"requested_fps":options["fps"]}
        manifest.update(dict((key,options.get(key)) for key in ("food_type","lighting","distance","view_angle","occlusion","environment","notes")))
        for row in rows: row["source_hash"]=sha
        (folder/"session.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        (folder/"manifest.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows),encoding="utf-8")
        result["samples"]=len(rows)
    return result


def worker(options,folder,stop,connection):
    try: connection.send(acquire(options,Path(folder) if folder else None,stop))
    except Exception as exc: connection.send({"result":"FAIL","error":str(exc)[:256]})
    finally: connection.close()


def run(options,output=None,apply=False):
    capturing=bool(options.get("session_id")); stage=None; destination=None
    if capturing:
        if not re.match(r"^[a-z0-9_-]{1,64}$",options["session_id"]): raise ValueError("invalid explicit session ID")
        destination=Path(output)/options["session_id"]
        if destination.exists(): raise FileExistsError("session exists, no overwrite")
        if not apply: return {"result":"DRY_RUN","camera_opened":False,"session_id":options["session_id"]}
        Path(output).mkdir(parents=True,exist_ok=True); stage=Path(tempfile.mkdtemp(prefix=".capture-",dir=str(output)))
    elif not apply: return {"result":"DRY_RUN","camera_opened":False,"device":options["device"]}
    context=mp.get_context("spawn"); stop=context.Event(); receiver,sender=context.Pipe(False)
    process=context.Process(target=worker,args=(options,str(stage) if stage else None,stop,sender)); result=None
    try:
        process.start(); sender.close(); deadline=time.monotonic()+options["seconds"]+10
        try:
            while time.monotonic()<deadline:
                if receiver.poll(0.1): result=receiver.recv(); break
                if not process.is_alive(): break
        except KeyboardInterrupt:
            stop.set()
            if receiver.poll(3): result=receiver.recv()
        if result is None: raise TimeoutError("camera worker deadline exceeded; terminated without a PASS")
        process.join(2)
        if process.is_alive(): raise TimeoutError("camera worker did not stop")
        if stage is not None and result.get("result")!="FAIL" and result.get("samples",0)>0:
            if destination.exists(): raise FileExistsError("session exists")
            stage.rename(destination); result["session_path"]=str(destination)
        return result
    finally:
        if process.pid is not None and process.is_alive(): process.terminate(); process.join(3)
        receiver.close(); sender.close()
        if stage is not None and stage.exists(): shutil.rmtree(stage)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--device",required=True)
    parser.add_argument("--width",type=int,default=1280); parser.add_argument("--height",type=int,default=720)
    parser.add_argument("--fps",type=float,default=30); parser.add_argument("--fourcc",default="MJPG")
    parser.add_argument("--frames",type=int,default=300); parser.add_argument("--seconds",type=float,default=15)
    parser.add_argument("--interval",type=float,default=1); parser.add_argument("--minimum-spacing",type=float,default=0.5)
    parser.add_argument("--session-id"); parser.add_argument("--identity",choices=IDENTITY,default="UNKNOWN")
    parser.add_argument("--behavior",choices=BEHAVIOR,default="UNSURE")
    parser.add_argument("--output",type=Path,default=ROOT/"ai/datasets/capture"); parser.add_argument("--apply",action="store_true")
    parser.add_argument("--save",type=Path)
    for key in ("food_type","lighting","distance","view_angle","occlusion","environment","notes"): parser.add_argument("--"+key.replace("_","-"))
    args=parser.parse_args(); options=vars(args).copy()
    if not 1<=args.frames<=1000 or not 0<args.seconds<=3600 or not 1<=args.width<=3840 or not 1<=args.height<=2160 or not 0<args.fps<=60:
        parser.error("invalid finite duration/frame/resolution/FPS bounds")
    if not re.match(r"^[A-Za-z0-9]{4}$",args.fourcc) or not 0<args.interval<=3600 or not 0<=args.minimum_spacing<=3600:
        parser.error("invalid sampling/FourCC")
    for key in ("food_type","lighting","distance","view_angle","occlusion","environment","notes"):
        value=options.get(key); limit=512 if key=="notes" else 256 if key=="environment" else 64
        if value is not None and len(value)>limit: parser.error("context metadata oversized")
    if args.save and args.save.exists(): parser.error("save path exists")
    options.pop("output"); options.pop("save"); options.pop("apply")
    try: result=run(options,args.output,args.apply)
    except (OSError,ValueError,EOFError) as exc: result={"result":"FAIL","error":str(exc)[:256]}
    if args.save:
        args.save.parent.mkdir(parents=True,exist_ok=True)
        with args.save.open("x",encoding="utf-8") as stream: json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2)); return 2 if result.get("result")=="FAIL" else 0


if __name__=="__main__": sys.exit(main())
