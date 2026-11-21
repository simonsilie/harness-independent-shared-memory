import os
import subprocess
import sys
from pathlib import Path

from build.semantic_runtime import WATCHER

ROOT = Path(__file__).resolve().parents[3]


def test_model_free_mcp_watcher_and_restart():
    result = subprocess.run(
        [sys.executable, str(WATCHER), "--semantic-disabled"],
        cwd=ROOT,
        env=os.environ | {"WATCHFILES_FORCE_POLLING": "true"},
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stdout + result.stderr
