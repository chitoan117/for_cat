"""Safe top-level fast/full software validation. Never opens a physical device."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    if sys.version_info < (3, 10):
        raise SystemExit("Real Jetson app stack requires Python>=3.10. Use the existing HOST venv; do not upgrade Nano system Python.")
    from scripts.check_release import main
    raise SystemExit(main())
