import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("opt_in", ["default", "environment", "config"])
def test_mcp_project_creation_requires_opt_in(tmp_path, opt_in):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import asyncio
import json
import os
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.exceptions import ToolError

from basic_memory.config import ConfigManager
from basic_memory.mcp.server import mcp
import basic_memory.mcp.tools.projects

opt_in = sys.argv[1]
state = Path(os.environ["BASIC_MEMORY_CONFIG_DIR"])
state.mkdir()
root = state.parent / "main"
root.mkdir()
target = state.parent / "new-project"
(state / "config.json").write_text(json.dumps({
    "projects": {"main": {"path": str(root), "mode": "local"}},
    "default_project": "main",
    **({"enable_mcp_project_create": True} if opt_in == "config" else {}),
}))

async def check():
    args = {"command": "create", "name": "new-project", "path": str(target), "set_default": True}
    async with Client(mcp) as client:
        await client.call_tool("bm_project", {"command": "list"})
        await client.call_tool("bm_project", {"command": "recent", "project": "main"})
        if opt_in == "default":
            try:
                await client.call_tool("bm_project", args)
            except ToolError:
                pass
            else:
                raise AssertionError("MCP project creation should require an opt-in")
            assert not target.exists()
            config = ConfigManager().config
            assert set(config.projects) == {"main"}
            assert config.default_project == "main"
        else:
            await client.call_tool("bm_project", args)
            assert target.is_dir()
            assert "new-project" in ConfigManager().config.projects
            assert ConfigManager().config.default_project == "new-project"

asyncio.run(check())
""",
            opt_in,
        ],
        cwd=tmp_path,
        env={key: value for key, value in os.environ.items() if not key.startswith("BASIC_MEMORY_")}
        | {
            "BASIC_MEMORY_CONFIG_DIR": str(tmp_path / "state"),
            "BASIC_MEMORY_HOME": str(tmp_path / "main"),
            "BASIC_MEMORY_FORCE_LOCAL": "true",
            "FASTMCP_CHECK_FOR_UPDATES": "off",
            "HF_HUB_OFFLINE": "1",
        }
        | ({"BASIC_MEMORY_ENABLE_MCP_PROJECT_CREATE": "true"} if opt_in == "environment" else {}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
