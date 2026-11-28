import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WATCHER = ROOT / "evaluation/native/mcp_watcher.py"


def test_mcp_watcher_and_restart_with_keyword_fallback():
    result = subprocess.run(
        [sys.executable, str(WATCHER)],
        cwd=ROOT,
        env=os.environ | {"WATCHFILES_FORCE_POLLING": "true"},
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stdout + result.stderr
