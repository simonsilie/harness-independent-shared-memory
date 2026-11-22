"""Disposable Basic Memory stores shared by approval-gate integration tests."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from mcp.client.stdio import get_default_environment

DURABLE = (
    "---\ntitle: Gated decision\nkind: durable\nstatus: active\nsource: integration check\n---\n\nKeep SQLite local.\n"
)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("APPROVAL_GATE_TEST_SECRET", "synthetic-credential")
    root = tmp_path / "store"
    state = root / "state"
    personal = root / "notes/personal"
    alpha = root / "notes/alpha"
    for folder in (state, personal / "durable", personal / "temporary", personal / "handovers", alpha):
        folder.mkdir(parents=True)
    (personal / "handovers/existing-durable.md").write_text(DURABLE)
    config = {
        "projects": {
            "personal": {"path": str(personal), "mode": "local"},
            "alpha": {"path": str(alpha), "mode": "local"},
        },
        "default_project": "personal",
        "database_backend": "sqlite",
        "database_url": None,
        "default_search_type": "text",
        "semantic_search_enabled": False,
        "auto_update": False,
        "logfire_enabled": False,
    }
    (state / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    env = {
        "BASIC_MEMORY_CONFIG_DIR": str(state),
        "BASIC_MEMORY_HOME": str(personal),
        "BASIC_MEMORY_FORCE_LOCAL": "true",
        "BASIC_MEMORY_SEMANTIC_SEARCH_ENABLED": "false",
        "BASIC_MEMORY_AUTO_UPDATE": "false",
        "FASTMCP_CHECK_FOR_UPDATES": "off",
        "HF_HUB_OFFLINE": "1",
    }
    executable = Path(sys.executable).with_name("basic-memory")
    subprocess.run(
        [str(executable), "reindex", "--full", "--search"],
        env=get_default_environment() | env,
        check=True,
        capture_output=True,
        timeout=180,
    )
    return root, executable, env
