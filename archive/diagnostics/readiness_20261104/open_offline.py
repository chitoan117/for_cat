from pathlib import Path
import os,subprocess
import shutil
target=Path('/home/toan/Desktop/cat/for-cat-offline.desktop')
installed=Path('/home/toan/.local/share/applications/for-cat-offline.desktop')
if not target.exists():
    assert 'X-ForCat-Launcher=true' in installed.read_text()
    shutil.copyfile(str(installed),str(target))
    target.chmod(0o755)
pid=subprocess.check_output(['pgrep','-u',str(os.getuid()),'-x','lxsession'],universal_newlines=True).split()[0]
for item in Path('/proc',pid,'environ').read_bytes().split(b'\0'):
    k,sep,v=item.partition(b'=')
    if sep and k.decode() in ['DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS']: os.environ[k.decode()]=v.decode()
import gi
gi.require_version('Gio','2.0')
from gi.repository import Gio
app=Gio.DesktopAppInfo.new_from_filename(str(target))
assert app is not None and app.launch([],None)
print('Actual FOR_CAT Offline launcher opened on the Jetson touch display')
