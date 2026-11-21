"""Portable OKF export of every configured project in a local store."""

import json
import os
import subprocess
import sys
from pathlib import Path


def export(source: Path, destination: Path) -> Path:
    """Export all configured projects into separate bundles and return the export root."""
    source, destination = source.resolve(), destination.resolve()
    config = json.loads((source / "state/config.json").read_text())
    names = sorted(config["projects"])
    default = config.get("default_project", "personal")
    home = (source / Path(config["projects"][default]["path"])).resolve()
    env = os.environ | {
        "BASIC_MEMORY_CONFIG_DIR": str(source / "state"),
        "BASIC_MEMORY_HOME": str(home),
        "BASIC_MEMORY_FORCE_LOCAL": "true",
        "BASIC_MEMORY_AUTO_UPDATE": "false",
        "HF_HUB_OFFLINE": "1",
    }
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    executable = Path(sys.executable).with_name("basic-memory")
    for name in names:
        subprocess.run(
            [str(executable), "okf", "export", str(destination / "bundles" / name), "--project", name, "--json"],
            env=env,
            check=True,
        )
    return destination
