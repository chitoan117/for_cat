import shutil
from pathlib import Path
O=Path(__file__).resolve().parent;S=O/'firmware/esp32';D=O/'guard_tuning/esp32'
assert S.is_dir() and not D.exists()
shutil.copytree(S,D,ignore=shutil.ignore_patterns('.pio','__pycache__'))
print('Isolated guard source prepared; production firmware/source untouched.')
