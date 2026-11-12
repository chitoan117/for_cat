"""Preserve the staged user's current-state document before a small latest banner."""
from pathlib import Path
import shutil
ROOT=Path('/home/toan/for_cat')
source=ROOT/'docs/CURRENT_PROJECT_STATE.md'
backup=ROOT/'evidence/overnight_integration_20261023/originals/docs/CURRENT_PROJECT_STATE.md'
assert not backup.exists()
backup.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(source,backup)
print('CURRENT DOCUMENT ORIGINAL CHECKPOINTED; USER STAGED INDEX NOT TOUCHED')
