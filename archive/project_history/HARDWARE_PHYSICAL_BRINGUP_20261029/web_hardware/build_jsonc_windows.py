"""Build real json-c locally for Windows parser tests, never system/production."""
import json
import re
import os
from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
TOOLS=HERE/'native_tooling/Scripts';SOURCE=HERE/'json_c_source'
BUILD=HERE/'native_jsonc_build';INSTALL=HERE/'native_jsonc_install'
def run(argv,name):
    p=subprocess.run([str(x) for x in argv],cwd=HERE,capture_output=True,timeout=600,
        env={**os.environ,'PATH':str(TOOLS)+os.pathsep+os.environ.get('PATH',''),'PYTHONIOENCODING':'utf-8'})
    (HERE/(name+'.log')).write_bytes(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError(name+' failed; see log')
    print(name+': PASS',flush=True)
    return p.stdout.decode('utf-8','replace')
def main():
    commit=run(['git','-C',SOURCE,'rev-parse','HEAD'],'jsonc_source_commit').strip()
    if commit!='b4c371fa0cbc4dcbaccc359ce9e957a22988fb34':raise ValueError('wrong pinned json-c source')
    run([TOOLS/'cmake.exe','-S',SOURCE,'-B',BUILD,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+str(TOOLS/'ninja.exe'),
        '-DCMAKE_C_COMPILER='+str(ZIG),'-DCMAKE_C_COMPILER_ARG1=cc','-DCMAKE_AR='+str(HERE/'native_wrappers/zig-ar.cmd'),
        '-DCMAKE_C_ARCHIVE_CREATE=<CMAKE_AR> ar qc <TARGET> <LINK_FLAGS> <OBJECTS>',
        '-DCMAKE_C_ARCHIVE_FINISH=<CMAKE_AR> ar s <TARGET>',
        '-DCMAKE_BUILD_TYPE=Release','-DBUILD_SHARED_LIBS=OFF','-DBUILD_STATIC_LIBS=ON','-DBUILD_TESTING=OFF',
        '-DBUILD_APPS=OFF','-DDISABLE_WERROR=ON','-DENABLE_THREADING=OFF','-DCMAKE_INSTALL_PREFIX='+str(INSTALL)],'jsonc_configure')
    # Clang-on-Windows CMake auto-detection treats zig.exe as bare llvm-ar.
    # Compile real CMake/Ninja object targets, then invoke the actual zig ar
    # subcommand explicitly. No vendor source/toolchain-global patch required.
    targets=re.findall(r'^build (CMakeFiles/json-c\.dir/[^:]+\.obj):',(BUILD/'build.ninja').read_text(),re.M)
    if len(targets)<10:raise ValueError('unexpected json-c object target set')
    run([TOOLS/'cmake.exe','--build',BUILD,'--parallel','2','--target',*targets],'jsonc_build_objects')
    run([ZIG,'ar','rcs',BUILD/'libjson-c.a',*[BUILD/t for t in targets]],'jsonc_archive')
    run([TOOLS/'cmake.exe','--install',BUILD],'jsonc_install')
    (HERE/'jsonc_dependency.json').write_text(json.dumps({'version':'0.17','tag':'json-c-0.17-20230812','commit':commit,
        'scope':'WINDOWS_OFFLINE_PARSER_TEST_DEPENDENCY_ONLY','global_or_production_install':False},indent=2)+'\n')
if __name__=='__main__':main()
