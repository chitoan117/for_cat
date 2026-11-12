"""Offline candidate-specific check only. Does not access the attached image bytes,
camera, serial, SSH or network; photo coordinates were visually estimated."""
import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
HOST=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device'
CONFIG=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/config/food_roi.fixed_camera.candidate.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(command,log):
    p=subprocess.run([str(x) for x in command],cwd=OUT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/log).write_bytes(p.stdout)
    if p.returncode:raise RuntimeError(p.stdout.decode('utf-8','replace'))
    return p.stdout.decode('utf-8','replace')
prior=json.loads((OUT/'roi_offline_result.json').read_text(encoding='utf-8'))
for name,digest in prior['changed_roi_sources_sha256'].items():assert sha(HOST/name)==digest, 'existing ROI code changed unexpectedly'
exe=OUT/'native/test_fixed_camera_roi.exe';assert exe.parent.is_dir()
run([ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++14','-O1','-Wall','-Wextra','-Wpedantic','-Werror','-I'+str(HOST),OUT/'test_fixed_camera_roi.cpp','-o',exe],'fixed_camera_roi_compile.log')
text=run([exe,CONFIG],'fixed_camera_roi_test.log')
assert 'FIXED_CAMERA_ROI_CANDIDATE_PASS' in text
result={'result':'PASS','scope':'FIXED_CAMERA_CANDIDATE_SYNTHETIC_GEOMETRY_ONLY',
        'reference_image':'User-supplied conversation attachment, displayed1920x1080; original bytes not archived or hashed',
        'coordinate_provenance':'VISUAL_ESTIMATE_NOT_PIXEL_SEGMENTATION',
        'config_sha256':sha(CONFIG),'candidate_normalized':[.02,.40,.75,1.0],
        'candidate_pixels_1920x1080':[38.4,432,1440,1080],
        'camera_fixed':'OWNER_DECLARATION','calibrated':False,'default_mode':'FULL_FRAME',
        'original_roi_sources_unchanged':True,'old_tests_rerun':False,'hardware_used':False,
        'real_animal_bbox_validation':False,'stdout':text}
(OUT/'fixed_camera_roi_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(text)
