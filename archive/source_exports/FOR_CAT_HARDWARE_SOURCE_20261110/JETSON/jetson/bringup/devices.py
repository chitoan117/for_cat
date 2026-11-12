"""Passive Python3.6 device/runtime inventory; no camera/serial/GPU starts."""
import json
import platform
import sys
from pathlib import Path


def inventory(dev_root=Path("/dev")):
    result={"python":platform.python_version(),"architecture":platform.machine(),"video_nodes":[],"serial_ports":[],"opened_devices":False}
    result["video_nodes"]=[str(path) for path in sorted(dev_root.glob("video*"))]
    try:
        from serial.tools import list_ports
        result["serial_ports"]=[{"device":port.device,"vid":port.vid,"pid":port.pid,"product":port.product}
                                for port in list_ports.comports()]
    except ImportError: result["serial_status"]="PYSERIAL_NOT_AVAILABLE"
    for name,path in (("os_release",Path("/etc/os-release")),("l4t",Path("/etc/nv_tegra_release")),("model",Path("/proc/device-tree/model"))):
        if path.is_file(): result[name]=path.read_bytes().decode("utf-8",errors="replace").replace("\x00","").strip()[:2048]
    return result


def main():
    print(json.dumps(inventory(),indent=2)); return 0


if __name__=="__main__": sys.exit(main())
