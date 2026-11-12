from pathlib import Path
import json,runpy

root=Path(__file__).resolve().parent
oldroot=root.parent/'web_cleanup_20261106'
web=root/'web_real'
(web/'forcat_build.json').write_text(json.dumps({'mode':'REAL','base_href':'/flutter/','target_grams':35,'source':'REMOVE_CAMERA_20261108'}),encoding='utf-8')
package=(oldroot/'package_web.py').read_text(encoding='utf-8').replace('web_cleanup_20261106','web_remove_camera_20261108')
package=package.replace("sha(ROOT / 'before/main.dart.js')", "'a7c6f3902bc30016068d1dabe90b87027208ab27d73369e23974e386351f9f5a'")
(root/'package_web.py').write_text(package,encoding='utf-8')
deploy=(oldroot/'deploy_web.py').read_text(encoding='utf-8').replace('cleanup_20261106','remove_camera_20261108')
(root/'deploy_web.py').write_text(deploy,encoding='utf-8')
runpy.run_path(str(root/'package_web.py'),run_name='__main__')
