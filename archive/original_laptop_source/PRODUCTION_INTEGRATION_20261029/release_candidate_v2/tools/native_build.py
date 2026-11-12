"""Native ARM64 compile only, no cutover or execution after build."""
import json
from pathlib import Path
import subprocess
import sys
from integrity import sha,verify,write_new
from preflight import inventory

def commands(release,output,flags,cuda_home='/usr/local/cuda-10.2'):
    release=Path(release);output=Path(output);device=release/'payload/jetson/device'
    result={}
    common=['g++','-std=c++14','-O2','-pthread','-I'+(release/'firmware_include').as_posix()]
    for name in ('roi_ai_source','esp32_bridge','ai_state_tap','engine_probe'):
        modules=['json-c','sqlite3'] if name!='engine_probe' else []
        if name=='roi_ai_source':modules+=['opencv4']
        source=device/(name+'.cpp') if name!='engine_probe' else release/'tools/engine_probe.cpp'
        cmd=common+flags('cflags',modules)
        if name in ('roi_ai_source','engine_probe'):
            cmd+=['-I'+(release/'ai_reference').as_posix(),'-I'+cuda_home+'/include','-Wno-deprecated-declarations']
        cmd+=[source.as_posix(),'-o',(output/name).as_posix()]+flags('libs',modules)
        if name in ('roi_ai_source','engine_probe'):cmd+=['-L'+cuda_home+'/lib64','-lnvinfer','-lcudart']
        result[name]=cmd
    return result
def build(release,output,production):
    release=Path(release).resolve();output=Path(output).resolve();production=Path(production).resolve()
    verify(release)
    if output.exists() or production==output or production in output.parents or release==output or release in output.parents:
        raise ValueError('NEW build directory disjoint from release/production required')
    preflight=inventory(release,production)
    if not preflight['build_preconditions']:raise ValueError('ARM64/compiler/OpenCV/CUDA/TensorRT/Python preconditions not met')
    if not preflight['engine_matches_expected']:raise ValueError('engine hash must be reviewed before build')
    def flags(mode,modules):return subprocess.check_output(['pkg-config','--'+mode,*modules],text=True).split() if modules else []
    output.mkdir(parents=True,exist_ok=False)
    write_new(output/'preflight.json',preflight)
    result={'arm64_build':'PASS','release_manifest_sha256':sha(release/'manifest.json'),'binaries':{},'engine_contract':'NOT_VERIFIED'}
    for name,argv in commands(release,output,flags,preflight['cuda_home']).items():
        p=subprocess.run(argv,capture_output=True,timeout=1200)
        (output/(name+'.build.log')).write_bytes(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError('BUILD FAIL '+name+'; logs retained, no deploy')
        result['binaries'][name]=sha(output/name)
    write_new(output/'build.json',result)
    return result
