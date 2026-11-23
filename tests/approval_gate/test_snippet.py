import json
import tomllib
from pathlib import Path

import pytest

from approval_gate.snippet import render_snippet

TOOLS = {"bm_project", "bm_read", "bm_search", "bm_write"}


@pytest.mark.parametrize("client", ["codex", "opencode"])
def test_snippet_renders_launcher_and_tool_permissions(client: str) -> None:
    uv = Path("/example/🛠/bin/uv")
    checkout = Path("/example/🚀 check out")
    gate = Path("/example/📁/approval gate.json")
    expected = [
        "/example/🛠/bin/uv",
        "run",
        "--directory",
        "/example/🚀 check out",
        "--locked",
        "--no-sync",
        "python",
        "-m",
        "approval_gate.proxy",
        "--config",
        "/example/📁/approval gate.json",
    ]

    output = render_snippet(client, uv, checkout, gate)

    if client == "codex":
        entry = tomllib.loads(output)["mcp_servers"]["basic_memory"]
        assert [entry["command"], *entry["args"]] == expected
        assert set(entry["enabled_tools"]) == TOOLS
    else:
        document = json.loads(output)
        entry = document["mcp"]["servers"]["basic_memory"]
        assert entry == {"type": "local", "command": expected, "codemode": False}
        deny, *allow = document["permissions"]
        assert deny == {"action": "basic_memory_*", "resource": "*", "effect": "deny"}
        assert {(rule["action"], rule["resource"], rule["effect"]) for rule in allow} == {
            (f"basic_memory_{tool}", "*", "allow") for tool in TOOLS
        }
