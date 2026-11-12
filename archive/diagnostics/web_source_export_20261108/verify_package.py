from pathlib import Path
import ast,json,re,hashlib,shutil
r=Path('D:/Agent_Cat/FOR_CAT_WEB_SOURCE_20261108')
api=json.loads((r/'docs/openapi.json').read_text())
lines=['# API tham khảo — xuất từ Jetson ngày08/11/2026','','Hợp đồng chi tiết nằm trong `openapi.json`. Swagger ở `/docs` khi backend chạy.','','| HTTP | Endpoint | Mô tả từ source |','|---|---|---|']
for path,methods in api['paths'].items():
 for method,spec in methods.items():lines.append('| '+method.upper()+' | `'+path+'` | '+str(spec.get('summary','')).replace('|','/')+' |')
lines+=['','## Luồng trạng thái và giao diện','','- WebSocket `/api/ws/state`: truyền trạng thái hệ thống; không nằm trong OpenAPI REST.','- `/app`, `/kiosk`: giao diện Flutter cùng backend.','- `/flutter/`: tài nguyên static đã build.','','Hai nhóm endpoint `/api/v1/...` và `/api/...` cùng tồn tại. Đối chiếu `frontend/lib/real_backend.dart` và `meal_plans.dart` để biết endpoint frontend gọi thực tế. Tên `preview`/`DRY_RUN` là tên hợp đồng cũ; bridge Jetson có thể tiêu thụ yêu cầu để điều khiển phần cứng thực.']
(r/'docs/API_REFERENCE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
dest=r/'integration/esp32';dest.mkdir(parents=True,exist_ok=True)
for name in ('esp32.ino','CatNearGate.h','FallbackGate.h'):shutil.copy2(Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32')/name,dest/name)
checked=0
for p in (r/'backend').rglob('*.py'):
 ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p));checked+=1
print('Python source syntax checked:',checked)
for p in (r/'frontend').rglob('*.dart'):
 source=Path('D:/DA_KT_NC/feeder_demo')/p.relative_to(r/'frontend')
 assert p.read_bytes()==source.read_bytes(),p
print('Frontend Dart files match original byte-for-byte.')
pat=re.compile(r'''(?i)(?:password|api_key|access_token|private_key)\s*[:=]\s*["']([^"'\n]{8,})["']''')
flags=[]
for p in r.rglob('*'):
 if p.is_file() and p.suffix in ('.py','.dart','.json','.yaml','.yml','.sh') and 'web_release' not in p.parts:
  if pat.search(p.read_text(encoding='utf-8',errors='replace')):flags.append(str(p.relative_to(r)))
print('Potential credential literals (filenames only):',json.dumps(flags))
