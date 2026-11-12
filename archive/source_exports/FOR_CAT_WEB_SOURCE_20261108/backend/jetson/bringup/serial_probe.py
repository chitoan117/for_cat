"""Explicit Python3.6 pyserial PING/GET_STATUS only; saves actual raw RX when requested."""
import argparse
import json
import math
import time
from datetime import datetime,timezone
from pathlib import Path

from . import protocol


def read_frame(port,deadline,clock=time.monotonic):
    prefix=b""; reads=0
    def exact(count):
        nonlocal reads
        output=bytearray()
        while len(output)<count:
            reads+=1
            if reads>8192 or clock()>=deadline: raise TimeoutError("bounded UART read timed out")
            part=port.read(count-len(output))
            if len(part)>count-len(output): raise ValueError("serial backend exceeded read request")
            output.extend(part)
        return bytes(output)
    for _ in range(4096):
        prefix=(prefix+exact(1))[-2:]
        if prefix==protocol.START: break
    else: raise ValueError("startup/noise budget exhausted")
    header=exact(8); length=int.from_bytes(header[6:8],"little")
    if length>256: raise ValueError("oversized UART payload")
    return prefix+header+exact(length+2)


def probe(port,count=3,timeout=2,base_id=100,clock=time.monotonic,sleep=time.sleep):
    if not 1<=count<=10 or not math.isfinite(timeout) or not 0<timeout<=10 or not 0<=base_id<=0xffffffff-2*count:
        raise ValueError("invalid bounded probe arguments")
    records=[]
    for index in range(count):
        for command in (protocol.PING,protocol.GET_STATUS):
            identifier=base_id+index*2+(command==protocol.GET_STATUS)
            raw=protocol.encode(identifier,command); began=clock()
            row={"command":"PING" if command==1 else "GET_STATUS","request_id":identifier,"tx_hex":raw.hex(),
                 "request_command":command,"rx_hex":None,"result":"FAIL","feed_requests_sent":0,"request_correlated":False}
            try:
                if port.write(raw)!=len(raw): raise TimeoutError("partial serial write")
                deadline=clock()+timeout
                for _ in range(32):
                    received=read_frame(port,deadline,clock); row["rx_hex"]=received.hex(); decoded=protocol.decode(received)
                    if decoded["request_id"]==identifier: break
                else: raise ValueError("stale reply budget exhausted")
                row.update(decoded); row["request_correlated"]=True
                expected=protocol.ACK if command==protocol.PING else protocol.SYSTEM_STATUS
                row["result"]="PASS" if decoded["command"]==expected and decoded["payload_hex"]=="01" else "FAIL"
            except (OSError,ValueError,TimeoutError) as exc: row["error"]=str(exc)[:256]
            row["elapsed_ms"]=(clock()-began)*1000; records.append(row)
        if index+1<count: sleep(1)
    return {"schema_version":1,"started_at_utc":datetime.now(timezone.utc).isoformat(),"records":records,
            "result":"PASS" if all(row["result"]=="PASS" for row in records) else "FAIL","feed_requests_sent":0,
            "milestone_automatically_awarded":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device",required=True); parser.add_argument("--count",type=int,default=3)
    parser.add_argument("--timeout",type=float,default=2); parser.add_argument("--startup-delay",type=float,default=2)
    parser.add_argument("--save",type=Path); args=parser.parse_args()
    if not 1<=args.count<=10 or not 0<args.timeout<=10 or not 0<=args.startup_delay<=5: parser.error("invalid bounds")
    if args.save and args.save.exists(): parser.error("save path exists; no overwrite")
    try:
        import serial
        with serial.Serial(args.device,115200,timeout=min(args.timeout,0.1),write_timeout=args.timeout) as port:
            time.sleep(args.startup_delay); port.reset_input_buffer()
            result=probe(port,args.count,args.timeout)
    except (OSError,ValueError) as exc:
        result={"result":"FAIL","error":str(exc)[:256],"device":args.device,"feed_requests_sent":0}
    result["device"]=args.device
    if args.save:
        args.save.parent.mkdir(parents=True,exist_ok=True)
        with args.save.open("x",encoding="utf-8") as stream: json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2)); return 0 if result["result"]=="PASS" else 2


if __name__=="__main__": raise SystemExit(main())
