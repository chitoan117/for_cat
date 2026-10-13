#!/bin/sh
# Diagnostic only; no installs, GPIO access, frame capture or files written.
echo '--- OS ---'
if [ -r /etc/os-release ]; then cat /etc/os-release; else echo 'OS release unavailable'; fi
echo '--- kernel / board ---'
uname -a
uname -m
echo '--- disk/RAM/swap (diagnostic only) ---'
df -h .
if command -v free >/dev/null 2>&1; then free -h; fi
if [ -r /proc/meminfo ]; then grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree):' /proc/meminfo; fi
if [ -r /proc/device-tree/model ]; then cat /proc/device-tree/model; echo; fi
if [ -r /etc/nv_tegra_release ]; then cat /etc/nv_tegra_release; fi
if command -v nvcc >/dev/null 2>&1; then nvcc --version; else echo 'nvcc unavailable'; fi
if command -v dpkg-query >/dev/null 2>&1; then dpkg-query -W nvidia-jetpack nvidia-l4t-core 2>/dev/null || echo 'JetPack/L4T package metadata unavailable'; fi
echo '--- Python / pip / modules ---'
if command -v python3 >/dev/null 2>&1; then
  python3 --version
  python3 -m pip --version 2>&1 || echo 'pip unavailable in selected python3'
  python3 -c 'import importlib.util; print("OpenCV:","present" if importlib.util.find_spec("cv2") else "unavailable"); print("pyserial:","present" if importlib.util.find_spec("serial") else "unavailable"); print("FastAPI:","present" if importlib.util.find_spec("fastapi") else "unavailable")'
  python3 -c 'import serial; print("pyserial import OK:",serial.VERSION)' 2>&1 || echo 'pyserial import failed'
  python3 -c 'import fastapi; print("FastAPI import OK:",fastapi.__version__)' 2>&1 || echo 'FastAPI import failed'
  python3 -c 'import cv2; print("OpenCV version:",cv2.__version__)' 2>&1 || echo 'OpenCV import failed'
  python3 -c 'import cv2; print("\n".join(x.strip() for x in cv2.getBuildInformation().splitlines() if any(k in x for k in ("GStreamer", "NVIDIA CUDA", "v4l/v4l2", "Video I/O:"))))' 2>&1 || echo 'OpenCV build information unavailable'
  python3 -c 'import sqlite3; print("SQLite:",sqlite3.sqlite_version); import importlib.util; print("TensorRT module present (not loaded/validated):",importlib.util.find_spec("tensorrt") is not None)' 2>&1 || echo 'SQLite/TensorRT diagnostic unavailable'
  python3 -c 'import sys; print("Project Python supported:",sys.version_info >= (3,10))'
else
  echo 'python3 unavailable'
fi
echo '--- video devices ---'
found=0
for item in /dev/video*; do
  if [ -e "$item" ]; then ls -l "$item"; found=1; fi
done
if [ "$found" -eq 0 ]; then echo 'No /dev/video*'; fi
echo '--- USB serial devices ---'
found=0
for item in /dev/ttyUSB* /dev/ttyACM*; do
  if [ -e "$item" ]; then ls -l "$item"; found=1; fi
done
if [ "$found" -eq 0 ]; then echo 'No /dev/ttyUSB* or /dev/ttyACM*'; fi
