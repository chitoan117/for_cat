"""Windows-only ROI checks. No SSH, camera/serial APIs, network or old test runner."""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import argparse

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
HOST=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device'
FW=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(command,log):
    process=subprocess.run([str(x) for x in command],cwd=OUT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/log).write_bytes(process.stdout)
    text=process.stdout.decode('utf-8','replace')
    if process.returncode:raise RuntimeError(text)
    return text
def illustration(cases):
    pieces=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="1020" viewBox="0 0 1280 1020">',
            '<rect width="1280" height="1020" fill="#14202b"/>',
            '<text x="25" y="35" fill="white" font-size="23">SYNTHETIC ROI SIMULATION — NOT A JETSON CAMERA RESULT</text>']
    for i,case in enumerate(cases):
        x=25+(i%2)*625;y=65+(i//2)*235
        pieces.append(f'<g transform="translate({x},{y})"><rect width="600" height="220" rx="8" fill="#243746"/>')
        title=html.escape(case['label']+' | '+case['mode'])
        subtitle=html.escape(case['relation']+' | classification='+case['classification'])
        pieces.append(f'<text x="12" y="24" fill="white" font-size="16">{title}</text><text x="12" y="46" fill="#cde2f5" font-size="14">{subtitle}</text>')
        pieces.append('<g transform="translate(20,60)"><rect width="560" height="145" fill="#15242e" stroke="#708da0"/>')
        if case['mode']=='ROI_ENABLED' and case['label']!='UNCONFIGURED_ENABLED':
            pieces.append('<rect x="140" y="36.25" width="280" height="72.5" fill="#b89a1b" fill-opacity=".13" stroke="#ffce38" stroke-width="2"/>')
        if case['label']!='UNCONFIGURED_ENABLED':
            a,b,c,d=case['bbox'];color='#ff7474' if case['label'].startswith('DOG') else '#6ee790'
            pieces.append(f'<rect x="{a*560}" y="{b*145}" width="{(c-a)*560}" height="{(d-b)*145}" fill="none" stroke="{color}" stroke-width="3"/>')
            if case['label']=='MIXED':pieces.append(f'<rect x="{a*560+5}" y="{b*145+5}" width="{(c-a)*560-10}" height="{(d-b)*145-10}" fill="none" stroke="#ff7474" stroke-width="3"/>')
        pieces.append('</g></g>')
    pieces.append('<text x="25" y="1010" fill="#cde2f5" font-size="15">Yellow: reviewed test ROI. Green: CAT bbox. Red: DOG bbox. All coordinates/detections are synthetic fixtures.</text></svg>')
    (OUT/'roi_synthetic_preview.svg').write_text('\n'.join(pieces),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cpp-only',action='store_true');args=parser.parse_args()
    (OUT/'native').mkdir(exist_ok=True)
    protected=[FW/'include/m4/hx711.h',FW/'include/m4/hx711_reference.h',FW/'include/m4/calibration.h',FW/'include/m4/calibration_record.h',
               FW/'include/m4/approach_dog_warning.h',FW/'include/dog_warning_protocol.h',FW/'include/m4/quad_level_sampler.h',
               HOST/'feed_policy.h',HOST/'decision_logic.h',ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/app/scheduled_worker.py']
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    result={'kind':'ROI_WINDOWS_OFFLINE_ONLY','generated_utc':datetime.now(timezone.utc).isoformat(),
            'default_mode':'FULL_FRAME','camera_opened':False,'serial_opened':False,'ssh_used':False,'network_used':False,
            'firmware_flashed':False,'model_trained':False,'physical_pass_claimed':False,'old_tests_rerun':False}
    exported=None
    node=shutil.which('node')
    if node or args.cpp_only:
        if args.cpp_only:
            log=OUT/'roi_calibration_test.log'
            assert log.stat().st_mtime>=max((OUT/'test_roi_calibration.js').stat().st_mtime,(OUT/'roi_calibration_math.js').stat().st_mtime)
            output=log.read_text(encoding='utf-8');result['calibration_tool_result_reused_unchanged']=True
        else:output=run([node,OUT/'test_roi_calibration.js'],'roi_calibration_test.log')
        assert 'ROI_IMAGE_CALIBRATION_MATH_PASS' in output
        exported=next(line.split('=',1)[1] for line in output.splitlines() if line.startswith('EXPORTED_SYNTHETIC_CONFIG='))
        result['calibration_tool_test']='PASS';result['calibration_tool_stdout']=output
    else:result['calibration_tool_test']='NOT_RUN_NODE_UNAVAILABLE'
    exe=OUT/'native/test_roi_offline.exe'
    run([ZIG,'c++','-std=c++14','-O1','-g','-Wall','-Wextra','-Wpedantic','-Werror','-I'+str(HOST),'-I'+str(FW/'include'),OUT/'test_roi_offline.cpp','-o',exe],'roi_offline_compile.log')
    args=[exe,OUT/'roi_synthetic_cases.jsonl',ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/config/food_roi.example.json']
    if exported:args.append(exported)
    output=run(args,'roi_offline_test.log');assert 'ROI_OFFLINE_PASS' in output
    result['cpp14_build']='PASS';result['cpp14_tests']='PASS';result['cpp14_stdout']=output
    cases=[json.loads(line) for line in (OUT/'roi_synthetic_cases.jsonl').read_text(encoding='utf-8').splitlines()]
    illustration(cases)
    after={str(p.relative_to(ROOT)):sha(p) for p in protected};assert before==after
    prior=json.loads((ROOT/'HX711_REFERENCE_PORT_20261028/result.json').read_text(encoding='utf-8'))
    for name in ('hx711.h','hx711_reference.h','calibration.h','calibration_record.h'):
        assert sha(FW/'include/m4'/name)==prior['source_sha256']['include/m4/'+name]
    result['untouched_dependencies_sha256']=after
    result['changed_roi_sources_sha256']={name:sha(HOST/name) for name in ('food_roi.h','roi_species.h','approach_fusion.h','esp32_bridge.cpp','roi_ai_source.cpp','roi_review.cpp')}
    result['visualization']='roi_synthetic_preview.svg — SYNTHETIC ONLY'
    result['jetson_cuda_opencv_build']='NOT_RUN_OFFLINE_WINDOWS_NO_SDK'
    result['old_arm_binaries']='HISTORICAL_PRE_OPTIONAL_ROI_DO_NOT_TREAT_AS_UPDATED_BUILD'
    result['ROI_OFFLINE_SOFTWARE_READY']=True
    (OUT/'roi_offline_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(output)
    print(json.dumps({'cpp14':'PASS','image_tool_math':result['calibration_tool_test'],'synthetic_scenes':len(cases),'ROI_OFFLINE_SOFTWARE_READY':True}))

if __name__=='__main__':main()
