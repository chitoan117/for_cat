from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as E,json,hashlib,re
p=Path('C:/Users/chito/Downloads/Bao_cao_YCS_He_thong_cho_thu_cung_an_uong_tu_dong_tich_hop_AI.docx')
with ZipFile(p) as z:
 s=z.read('word/document.xml').decode()
 print(json.dumps({'drawings':s.count('<w:drawing>'),'pict':s.count('<w:pict>'),'shape_textboxes':s.count('<w:txbxContent>'),'comments':'word/comments.xml' in z.namelist(),'insertions':len(re.findall(r'<w:ins\b',s)),'deletions':len(re.findall(r'<w:del\b',s)),'has_DS3231': 'DS3231' in s}))
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 root=E.fromstring(s)
 for j,tbl in enumerate(root.findall('.//w:tbl',ns),1):
  print('TABLE',j)
  for row in tbl.findall('w:tr',ns):
   print(json.dumps([''.join(c.itertext()) if False else ''.join(x.text or '' for x in c.findall('.//w:t',ns)) for c in row.findall('w:tc',ns)],ensure_ascii=True))
pcb=Path('C:/Users/chito/Downloads/pet_feeder.pdsprj')
if pcb.exists():
 with ZipFile(pcb) as z:
  name=next(x for x in z.namelist() if x.endswith('ROOT.LYT'))
  data=z.read(name)
  print('PCB_LAYOUT_SHA256',hashlib.sha256(data).hexdigest())
  for key in (b'IRF4905',b'PC817',b'F5305S'):print(key.decode(),any(key in z.read(n) for n in z.namelist()))
