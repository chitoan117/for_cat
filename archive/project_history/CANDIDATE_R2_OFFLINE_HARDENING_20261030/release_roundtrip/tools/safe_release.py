"""Python3.6+ bounded source-archive validation and NEW-directory extraction.
Default CLI PLAN_ONLY. No imports/execution from the archive, no device/service API.
"""
from __future__ import print_function
import argparse,hashlib,io,json,os,re,stat,unicodedata,zipfile
from pathlib import Path
KIND='FORCAT_R2_OFFLINE_HARDENING'
MANIFEST='SOURCE_MANIFEST.json';DIGEST='SOURCE_MANIFEST.sha256'
MAX_ZIP=8*1024*1024;MAX_FILE=1024*1024;MAX_TOTAL=16*1024*1024;MAX_FILES=256
REQUIRED=('tools/native_hardening.py','tools/safe_release.py','tests/safety_audit.cpp','tests/mass_policy.cpp',
    'tests/session_audit.cpp','tests/stream_bridge.cpp','tests/behavior_hardening.cpp',
    'candidate/bridge/esp32_bridge.cpp','candidate/bridge/telemetry.h','candidate/bridge/ultrasonic_telemetry.h',
    'candidate/bridge/diagnostic_session.h','candidate/bridge/food_roi.h','candidate/bridge/feed_policy.h',
    'candidate/bridge/decision_logic.h','candidate/bridge/approach_fusion.h','candidate/bridge/owner_behavior.h',
    'candidate/protocol/dog_warning_protocol.h','candidate/firmware/include/m4/dispense_bench.h',
    'candidate/firmware/include/m4/servo_bench.h','fixtures/feeding_policy.json','fixtures/transport_script.json')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON key')
        result[key]=value
    return result
def safe_name(name):
    if not isinstance(name,str) or not name or len(name)>240 or len(name.split('/'))>16 or name.startswith('/') or '\\' in name or ':' in name:raise ValueError('unsafe source path')
    for part in name.split('/'):
        if part in ('','.','..') or part.endswith(('.',' ')) or any(ord(c)<32 or c in '*?"<>|' for c in part):raise ValueError('unsafe path component')
        stem=unicodedata.normalize('NFKC',part.split('.')[0]).upper()
        if stem in ('CON','NUL','AUX','PRN','CONIN$','CONOUT$','CLOCK$') or re.match(r'^(COM|LPT)[1-9]$',stem):raise ValueError('reserved Windows device name')
    if Path(name).suffix.lower() in ('.exe','.dll','.o','.obj','.a','.lib','.pdb','.pyc','.bin'):raise ValueError('binary/object/firmware forbidden in source release')
    return unicodedata.normalize('NFC',name).casefold()
def decode_manifest(raw,recorded,expected,required=REQUIRED):
    actual=digest(raw)
    if not re.match(r'^[0-9a-f]{64}$',recorded) or actual!=recorded:raise ValueError('manifest checksum mismatch')
    if expected is not None and (not re.match(r'^[0-9a-f]{64}$',expected) or actual!=expected):raise ValueError('external trusted manifest mismatch')
    def bad(_):raise ValueError('non-finite JSON constant')
    m=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=bad)
    if m.get('kind')!=KIND or m.get('base_revision')!='GCC75_R2':raise ValueError('wrong candidate kind/base')
    files=m.get('files')
    if not isinstance(files,dict) or not 1<=len(files)<=MAX_FILES or not set(required)<=set(files):raise ValueError('missing required source inputs')
    names=set();total=0
    for name,meta in files.items():
        key=safe_name(name)
        if key in names or name in (MANIFEST,DIGEST):raise ValueError('path alias or recursive manifest')
        names.add(key)
        if not isinstance(meta,dict) or type(meta.get('bytes')) is not int or not 0<=meta['bytes']<=MAX_FILE or not re.match(r'^[0-9a-f]{64}$',str(meta.get('sha256',''))):raise ValueError('invalid file metadata')
        total+=meta['bytes']
    if total>MAX_TOTAL:raise ValueError('expanded release budget exceeded')
    return m,actual
def regular(path):
    try:return stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink()
    except OSError:return False
def directory(root,expected=None,allow_generated=False,required=REQUIRED):
    root=Path(root)
    if root.is_symlink() or getattr(root,'is_junction',lambda:False)():raise ValueError('symlink/junction root')
    for name in (MANIFEST,DIGEST):
        if not regular(root/name):raise ValueError('regular manifest required')
    if (root/MANIFEST).stat().st_size>MAX_FILE or (root/DIGEST).stat().st_size>128:raise ValueError('manifest budget exceeded')
    raw=(root/MANIFEST).read_bytes()
    if len(raw)>MAX_FILE:raise ValueError('manifest budget exceeded')
    m,actual=decode_manifest(raw,(root/DIGEST).read_text(encoding='ascii').strip(),expected,required)
    found=set()
    for parent,dirs,files in os.walk(str(root),followlinks=False):
        parent=Path(parent)
        for name in list(dirs):
            p=parent/name
            if p.is_symlink() or getattr(p,'is_junction',lambda:False)():raise ValueError('symlink/junction directory')
            if allow_generated and parent==root and name.startswith('hardening_arm64_'):dirs.remove(name)
        for name in files:
            p=parent/name;rel=p.relative_to(root).as_posix()
            if not regular(p):raise ValueError('non-regular source file')
            if rel not in m['files'] and rel not in (MANIFEST,DIGEST):raise ValueError('unexpected file: '+rel)
            found.add(rel)
            if rel in m['files']:
                meta=m['files'][rel]
                if p.stat().st_size!=meta['bytes'] or digest(p.read_bytes())!=meta['sha256']:raise ValueError('source mismatch: '+rel)
    if found!=set(m['files'])|{MANIFEST,DIGEST}:raise ValueError('missing source files')
    return {'source_integrity':'PASS','files_checked':len(m['files']),'manifest_sha256':actual,
        'base_revision':'GCC75_R2','revision':KIND,'ARM64':'NOT_RUN_BY_VERIFIER','APP_FLASH':'NO_GO'}
def inspect_bytes(data,expected,required=REQUIRED):
    if len(data)>MAX_ZIP:raise ValueError('compressed archive budget exceeded')
    if expected is None:raise ValueError('external manifest digest required for untrusted archive')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos=z.infolist();aliases=set();payload={};expanded=0
            if len(infos)>MAX_FILES+2:raise ValueError('archive member budget exceeded')
            for info in infos:
                key=safe_name(info.filename)
                mode=info.external_attr>>16
                if key in aliases or info.is_dir() or (stat.S_IFMT(mode) not in (0,stat.S_IFREG)) or info.flag_bits&1:raise ValueError('duplicate/alias/nonregular/encrypted member')
                aliases.add(key);expanded+=info.file_size
                if not 0<=info.file_size<=MAX_FILE or expanded>MAX_TOTAL+2*MAX_FILE:raise ValueError('archive expanded budget exceeded')
                with z.open(info) as f:raw=f.read(MAX_FILE+1)
                if len(raw)!=info.file_size:raise ValueError('archive length mismatch')
                payload[info.filename]=raw
            if MANIFEST not in payload or DIGEST not in payload:raise ValueError('archive has no manifest')
            m,actual=decode_manifest(payload[MANIFEST],payload[DIGEST].decode('ascii').strip(),expected,required)
            if set(payload)!=set(m['files'])|{MANIFEST,DIGEST}:raise ValueError('unexpected/missing archive member')
            for name,meta in m['files'].items():
                if len(payload[name])!=meta['bytes'] or digest(payload[name])!=meta['sha256']:raise ValueError('archive source mismatch: '+name)
            return payload,{'archive_integrity':'PASS','files_checked':len(m['files']),'manifest_sha256':actual,'APP_FLASH':'NO_GO'}
    except (zipfile.BadZipFile,RuntimeError,EOFError,UnicodeError) as e:raise ValueError('invalid/corrupt archive: '+str(e))
def archive(path,expected,required=REQUIRED):
    p=Path(path)
    if not regular(p) or p.stat().st_size>MAX_ZIP:raise ValueError('regular bounded ZIP required')
    return inspect_bytes(p.read_bytes(),expected,required)[1]
def extract(path,destination,expected,required=REQUIRED):
    p=Path(path);destination=Path(destination).absolute()
    if destination.exists() or destination.is_symlink() or not destination.parent.is_dir():raise ValueError('NEW destination with existing parent required')
    for parent in destination.parents:
        if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)():raise ValueError('symlink/junction extraction parent')
    if not regular(p) or p.stat().st_size>MAX_ZIP:raise ValueError('regular bounded ZIP required')
    payload,result=inspect_bytes(p.read_bytes(),expected,required) # validate immutable bytes BEFORE any output
    destination.mkdir(mode=0o700)
    for name,data in payload.items():
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data)
    directory(destination,expected,required=required)
    return {**result,'extracted_to':str(destination),'serial_opened':False,'services_changed':False}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path);p.add_argument('--archive',type=Path)
    p.add_argument('--extract-to',type=Path);p.add_argument('--expected-sha256');p.add_argument('--allow-generated',action='store_true');a=p.parse_args()
    if not a.directory and not a.archive:
        print(json.dumps({'mode':'PLAN_ONLY','APP_FLASH':'NO_GO','extracts_or_builds':False}));return
    if a.directory and (a.archive or a.extract_to):raise ValueError('choose one check')
    if a.extract_to and not a.archive:raise ValueError('archive required')
    result=directory(a.directory,a.expected_sha256,a.allow_generated) if a.directory else extract(a.archive,a.extract_to,a.expected_sha256) if a.extract_to else archive(a.archive,a.expected_sha256)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
