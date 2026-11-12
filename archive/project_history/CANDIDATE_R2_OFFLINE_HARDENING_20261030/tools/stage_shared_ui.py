import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    source=Path(r'D:\DA_KT_NC\feeder_demo\lib');target=ROOT/'candidate/flutter_shared/lib'
    if target.exists():raise ValueError('shared snapshot already staged')
    target.mkdir(parents=True)
    records={}
    for name in ('ui_widgets.dart','status_model.dart','live_camera_panel.dart','live_camera_controller.dart',
                 'live_camera_image.dart','live_camera_image_stub.dart','live_camera_image_web.dart'):
        data=(source/name).read_bytes();(target/name).write_bytes(data)
        records[name]={'source':str(source/name),'sha256':hashlib.sha256(data).hexdigest()}
    (ROOT/'SHARED_UI_BASELINE.json').write_text(json.dumps(records,indent=2)+'\n');print('7 original shared UI files copied unchanged')
if __name__=='__main__':main()
