"""Plan by default; explicit offline ARM64 compile in an exclusive staging dir.
No camera/serial/process launch of compiled binaries; no engine deserialization.
"""
import argparse
import json
from pathlib import Path
import subprocess
from jetson_preflight import inspect
from release_bundle import verify,digest

def build_plan(bundle,output):
    bundle=Path(bundle).resolve();output=Path(output).resolve()
    verify(bundle)
    # Build outputs must remain under the selected release's build directory.
    if output.parent!=bundle.parent.parent/'build'/bundle.name or output.exists():raise ValueError('use NEW staging/build/RELEASE/NAME outside immutable release')
    device=bundle/'payload/jetson/device'
    common=['g++','-std=c++14','-O2','-pthread','-I'+str(bundle/'firmware_include')]
    return output,common,device
def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--output',required=True)
    p.add_argument('--production-root',required=True);p.add_argument('--execute-build',action='store_true');args=p.parse_args()
    output,common,device=build_plan(args.bundle,args.output)
    if not args.execute_build:
        print(json.dumps({'plan_only':True,'standard':'C++14','binaries':['roi_ai_source','esp32_bridge','ai_state_tap'],
                          'output':str(output),'camera_opened':False}));return
    evidence=inspect(args.production_root)
    if not evidence['build_preconditions']:raise SystemExit('BLOCKED: dependencies/ARM64/engine preflight; no build performed')
    bundle=Path(args.bundle).resolve()
    output.mkdir(parents=True,exist_ok=False)
    (output/'preflight.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    def pkg(args):return subprocess.check_output(['pkg-config',*args],text=True).split()
    result={'arm64_build':'PASS','runtime':'NOT_VERIFIED','physical_pass':False,'binaries':{}}
    for name in ('roi_ai_source','esp32_bridge','ai_state_tap'):
        modules=['json-c','sqlite3']+(['opencv4'] if name=='roi_ai_source' else [])
        command=common+pkg(['--cflags',*modules])
        if name=='roi_ai_source':command+=['-I'+str(bundle/'ai_reference'),'-I/usr/local/cuda-10.2/include','-Wno-deprecated-declarations']
        command += [str(device/(name+'.cpp')),'-o',str(output/name)]+pkg(['--libs',*modules])
        if name=='roi_ai_source':command+=['-L/usr/local/cuda-10.2/lib64','-lnvinfer','-lcudart']
        p=subprocess.run(command,capture_output=True,timeout=900)
        (output/(name+'.build.log')).write_bytes(p.stdout+p.stderr)
        if p.returncode:raise SystemExit('BUILD FAIL '+name+'; keep logs; no runtime cutover')
        result['binaries'][name]={'sha256':digest(output/name),'bytes':(output/name).stat().st_size}
    (output/'build_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
