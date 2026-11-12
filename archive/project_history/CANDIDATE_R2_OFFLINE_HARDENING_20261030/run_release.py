import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--native-only',action='store_true');p.add_argument('--devices-only',action='store_true');a=p.parse_args()
    out=ROOT/'evidence'/('release_tests_devices' if a.devices_only else 'release_tests_native' if a.native_only else 'release_tests')
    if out.exists():raise ValueError('preserve release tests')
    out.mkdir()
    args=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','-o','pythonpath='+str(ROOT/'tools'),str(ROOT/'tests/test_release.py')]
    if a.native_only:args+=['-k','native_']
    if a.devices_only:args+=['-k','unsafe_names or console_and_unicode']
    q=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (out/'tests.log').write_bytes(q.stdout)
    if q.returncode:raise RuntimeError('release tests failed; read '+str(out))
    result={'cases':int(re.search(rb'(\d+) passed',q.stdout).group(1)),'scope':'TEMP_FILES_ONLY','device_access':False,'APP_FLASH':'NO_GO'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
