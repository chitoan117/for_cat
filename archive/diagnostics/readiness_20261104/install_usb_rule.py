#!/usr/bin/python3
from pathlib import Path
import os,datetime,shutil,subprocess
assert os.geteuid()==0,'Run this helper with sudo on the Jetson'
source=Path(__file__).parent/'99-forcat-esp32.rules'
target=Path('/etc/udev/rules.d/99-forcat-esp32.rules')
assert source.read_text().splitlines()[1]=='ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d3", ATTRS{serial}=="5C85066678", ENV{ID_MM_DEVICE_IGNORE}="1", ENV{ID_MM_PORT_IGNORE}="1"'
if target.exists() and target.read_bytes()!=source.read_bytes():
    backup=target.with_name(target.name+'.before-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S'))
    shutil.copy2(str(target),str(backup))
shutil.copyfile(str(source),str(target))
target.chmod(0o644)
subprocess.run(['udevadm','control','--reload-rules'],check=True)
subprocess.run(['udevadm','trigger','--action=change','--subsystem-match=tty','--sysname-match=ttyACM0'],check=True)
print('FOR_CAT ESP32-specific ModemManager ignore rule installed. Replug/re-enumeration will apply it to the USB device too.')
