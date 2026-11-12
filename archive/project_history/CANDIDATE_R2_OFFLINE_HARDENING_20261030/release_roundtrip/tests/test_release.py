import hashlib,io,json,os,stat,subprocess,sys,zipfile,warnings
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import safe_release as s
def fixture(files=None):
    files=files or {'source.py':b'SYNTHETIC_SOURCE_NOT_EXECUTED'}
    value={'kind':s.KIND,'base_revision':'GCC75_R2','files':{name:{'bytes':len(data),'sha256':s.digest(data)} for name,data in files.items()}}
    raw=json.dumps(value).encode();expected=s.digest(raw)
    return {**files,s.MANIFEST:raw,s.DIGEST:(expected+'\n').encode()},expected
def zipped(payload,extra=None):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as z:
        for name,data in payload.items():z.writestr(name,data)
        if extra:extra(z)
    return out.getvalue()
def test_valid_roundtrip_and_no_existing_overwrite(tmp_path):
    payload,digest=fixture();archive=tmp_path/'source.zip';archive.write_bytes(zipped(payload));dest=tmp_path/'new'
    assert s.archive(archive,digest,required=('source.py',))['archive_integrity']=='PASS'
    assert s.extract(archive,dest,digest,required=('source.py',))['archive_integrity']=='PASS'
    before=(dest/'source.py').stat().st_mtime_ns
    with pytest.raises(ValueError):s.extract(archive,dest,digest,required=('source.py',))
    assert before==(dest/'source.py').stat().st_mtime_ns
@pytest.mark.parametrize('name',['../escape.py','/absolute.py','C:/Windows/file.py','..\\escape.py','a//b.py','a/./b.py','a/../b.py','NUL.py','a/CON.txt','a/file.','a/file ','a/COM1.py','a/LPT9.py','bad:stream','bad?.py','bad\x00.py'])
def test_unsafe_names_rejected(name):
    with pytest.raises(ValueError):s.safe_name(name)
@pytest.mark.parametrize('fault',['extra','missing','tamper','bad_manifest_digest','external_digest','wrong_kind','invalid_json','duplicate_member','case_alias','symlink','directory','encrypted','crc_corrupt','truncated'])
def test_archive_fail_closed_before_any_output(tmp_path,fault):
    payload,expected=fixture();extra=None
    if fault=='extra':payload['unexpected.py']=b'NOT_EXECUTED'
    if fault=='missing':del payload['source.py']
    if fault=='tamper':payload['source.py']=b'TAMPERED'
    if fault=='bad_manifest_digest':payload[s.DIGEST]=b'0'*64
    if fault=='external_digest':expected='0'*64
    if fault=='wrong_kind':
        value=json.loads(payload[s.MANIFEST]);value['kind']='OTHER';payload[s.MANIFEST]=json.dumps(value).encode();expected=s.digest(payload[s.MANIFEST]);payload[s.DIGEST]=expected.encode()
    if fault=='invalid_json':payload[s.MANIFEST]=b'{';expected=s.digest(b'{');payload[s.DIGEST]=expected.encode()
    if fault=='duplicate_member':extra=lambda z:z.writestr('source.py',b'SECOND_COPY')
    if fault=='case_alias':extra=lambda z:z.writestr('SOURCE.PY',b'ALIAS')
    if fault=='symlink':
        def extra(z):
            info=zipfile.ZipInfo('link.py');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'/outside')
    if fault=='directory':extra=lambda z:z.writestr('empty/',b'')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',UserWarning);data=zipped(payload,extra)
    if fault=='encrypted':
        data=bytearray(data);pos=data.index(b'PK\x01\x02');data[pos+8]|=1;data=bytes(data)
    if fault=='crc_corrupt':
        data=bytearray(data);pos=data.index(b'SYNTHETIC_SOURCE_NOT_EXECUTED');data[pos]^=1;data=bytes(data)
    if fault=='truncated':data=data[:25]
    archive=tmp_path/'bad.zip';archive.write_bytes(data);dest=tmp_path/'not_created'
    with pytest.raises((ValueError,zipfile.BadZipFile)):s.extract(archive,dest,expected,required=('source.py',))
    assert not dest.exists()
def test_manifest_duplicate_keys_and_resource_budget():
    raw=b'{"kind":"x","kind":"x"}'
    with pytest.raises(ValueError):s.decode_manifest(raw,s.digest(raw),s.digest(raw),())
    payload,expected=fixture({'big.py':b'x'*(s.MAX_FILE+1)})
    with pytest.raises(ValueError):s.inspect_bytes(zipped(payload),expected,())
def test_directory_extra_tamper_missing_and_symlink(tmp_path):
    payload,digest=fixture()
    for name,data in payload.items():(tmp_path/name).write_bytes(data)
    assert s.directory(tmp_path,digest,required=('source.py',))['source_integrity']=='PASS'
    (tmp_path/'unexpected.py').write_text('NOT_EXECUTED')
    with pytest.raises(ValueError):s.directory(tmp_path,digest,required=('source.py',))
    (tmp_path/'unexpected.py').unlink();(tmp_path/'source.py').write_bytes(b'tampered')
    with pytest.raises(ValueError):s.directory(tmp_path,digest,required=('source.py',))
    (tmp_path/'source.py').unlink()
    with pytest.raises(ValueError):s.directory(tmp_path,digest,required=('source.py',))
def test_binary_objects_and_wrong_input_shape_rejected():
    for name in ('win.exe','x.obj','x.o','firmware.bin','cache.pyc'):
        with pytest.raises(ValueError):s.safe_name(name)
    payload,digest=fixture()
    value=json.loads(payload[s.MANIFEST]);value['files']['source.py']['bytes']=True
    raw=json.dumps(value).encode()
    with pytest.raises(ValueError):s.decode_manifest(raw,s.digest(raw),s.digest(raw),('source.py',))
def test_externally_untrusted_archive_never_extracts(tmp_path):
    payload,_=fixture();archive=tmp_path/'x.zip';archive.write_bytes(zipped(payload))
    with pytest.raises(ValueError):s.extract(archive,tmp_path/'new',None,required=('source.py',))
    assert not (tmp_path/'new').exists()
def test_native_default_plan_and_no_windows_promotion(tmp_path):
    target=tmp_path/'hardening_arm64_NOT_CREATED'
    command=[sys.executable,'-B',str(ROOT/'tools/native_hardening.py'),'--out',str(target)]
    p=subprocess.run(command,capture_output=True,text=True,timeout=15)
    assert p.returncode==0,p.stderr
    value=json.loads(p.stdout);assert value['mode']=='PLAN_ONLY' and value['mass_policy']['tolerance_grams']==5 and not target.exists()
    if sys.platform=='win32':
        p=subprocess.run(command+['--execute','BUILD_AND_FILE_REPLAY_ONLY'],capture_output=True,text=True,timeout=15)
        assert p.returncode!=0 and 'actual Linux ARM64 required' in p.stderr and not target.exists()
def test_native_output_never_overwrites_R1_R2_or_existing(tmp_path):
    import native_hardening as native
    for p in (ROOT.parent/'CANDIDATE_GCC75_R2_20261029',ROOT/'evidence',ROOT/'native_arm64_r2_first_run'):
        with pytest.raises(ValueError):native.new_output(p)
@pytest.mark.parametrize('name',['CONIN$','CONOUT$.txt','COM¹.py','LPT².txt'])
def test_console_and_unicode_DOS_devices_never_become_files(name):
    with pytest.raises(ValueError):s.safe_name(name)
