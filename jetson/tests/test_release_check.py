"""Check-runner contracts; never compile/upload firmware from a pytest test."""
import sys
from pathlib import Path
import pytest
from scripts.check_release import CheckFailure,execute,pytest_counts,PROFILES


def test_release_summary_retains_skips_and_rejects_failed_or_absent_suite():
    assert pytest_counts("211 passed, 2 skipped in 3s")=={"passed":211,"failed":0,"skipped":2,"errors":0}
    for text in ("no tests ran","1 failed, 10 passed","2 errors, 10 passed"):
        with pytest.raises(CheckFailure): pytest_counts(text)
    assert len(PROFILES)==11 and len(set(PROFILES))==11


def test_check_subprocess_failure_is_not_suppressed(tmp_path,capsys):
    with pytest.raises(CheckFailure,match="exit 3"):
        execute("failure",[sys.executable,"-c","print('GENUINE_FAILURE'); raise SystemExit(3)"],Path.cwd(),tmp_path)
    assert "GENUINE_FAILURE" in capsys.readouterr().out
    assert "GENUINE_FAILURE" in (tmp_path/"failure.log").read_text()
