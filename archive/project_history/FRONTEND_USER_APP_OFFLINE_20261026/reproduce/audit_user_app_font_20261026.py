from pathlib import Path
import struct
ROOT=Path(r'D:\DA_KT_NC\feeder_demo');b=(ROOT/'assets/fonts/Roboto-Regular.ttf').read_bytes()
u16=lambda o:struct.unpack_from('>H',b,o)[0];u32=lambda o:struct.unpack_from('>I',b,o)[0]
tables={b[o:o+4].decode('ascii'):u32(o+8) for o in range(12,12+u16(4)*16,16)};c=tables['cmap'];chars=set()
for i in range(u16(c+2)):
 o=c+u32(c+4+i*8+4);f=u16(o)
 if f==4:
  n=u16(o+6)//2;ends=o+14;starts=ends+2*n+2
  for j in range(n):chars.update(range(u16(starts+2*j),u16(ends+2*j)+1))
 if f==12:
  for j in range(u32(o+12)):
   start,end,_=struct.unpack_from('>III',b,o+16+12*j);chars.update(range(start,end+1))
used=set(''.join(p.read_text(encoding='utf-8') for p in (ROOT/'lib').glob('*.dart')))
for c in sorted(used,key=ord):
 if ord(c)>127 and ord(c) not in chars:print(f'U+{ord(c):04X} {c.encode("unicode_escape").decode()}')
