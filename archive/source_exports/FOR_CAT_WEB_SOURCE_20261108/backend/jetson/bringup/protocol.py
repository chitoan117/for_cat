"""Frozen UART v1 bytes, portable to system Python3.6; NOT a new protocol."""
import struct

START=b"\xa5\x5a"
VERSION=1
MAX_PAYLOAD=256
PING=1
GET_STATUS=2
ACK=6
SYSTEM_STATUS=5


def crc16(data):
    crc=0xffff
    for byte in data:
        crc ^= byte<<8
        for _ in range(8):
            crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    return crc


def encode(request_id,command,payload=b""):
    if not isinstance(request_id,int) or not 0<=request_id<=0xffffffff or not isinstance(command,int) or not 1<=command<=7 or len(payload)>MAX_PAYLOAD:
        raise ValueError("invalid v1 ID/command/payload")
    body=struct.pack("<BIBH",VERSION,request_id,command,len(payload))+payload
    return START+body+struct.pack("<H",crc16(body))


def decode(raw):
    if len(raw)<12 or raw[:2]!=START: raise ValueError("truncated/start mismatch")
    version,identifier,command,length=struct.unpack_from("<BIBH",raw,2)
    if version!=1 or not 1<=command<=7 or length>256 or len(raw)!=12+length: raise ValueError("version/command/length mismatch")
    received=struct.unpack_from("<H",raw,len(raw)-2)[0]; calculated=crc16(raw[2:-2])
    if received!=calculated: raise ValueError("CRC mismatch")
    return {"request_id":identifier,"command":command,"payload_hex":raw[10:-2].hex(),
            "crc_received":received,"crc_calculated":calculated,"crc_match":True}
