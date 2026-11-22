"""Launcher integration check using a client entry produced by the installer."""

import asyncio
import json
import os
import tomllib
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from approval_gate import cli, install
from approval_gate.config import Config, load_config
from approval_gate.proposals import list_proposals

DURABLE = (
    "---\ntitle: Gated decision\nkind: durable\nstatus: active\nsource: integration check\n---\n\nKeep SQLite local.\n"
)


@pytest.mark.parametrize("client", ["codex", "opencode"])
def test_installed_launcher_gates_durable_write(client: str, store, tmp_path: Path, monkeypatch) -> None:
    root, executable, environment = store
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    gate = tmp_path / "gate.json"
    config = Config(
        native_command=[str(executable), "mcp", "--transport", "stdio"],
        proposals_dir=tmp_path / "approvals",
        audit_log=tmp_path / "audit.jsonl",
        env=environment,
    )
    gate.write_text(config.model_dump_json())

    client_config = home / ("config.toml" if client == "codex" else "opencode.jsonc")
    client_config.write_text("")
    assert (
        install.main(
            [
                "--client",
                client,
                "--client-config",
                str(client_config),
                "--config",
                str(gate),
                "--apply",
            ]
        )
        == 0
    )

    if client == "codex":
        entry = tomllib.loads(client_config.read_text())["mcp_servers"]["basic_memory"]
        command = [entry["command"], *entry["args"]]
    else:
        document = json.loads(install._mask(client_config.read_text()))
        command = document["mcp"]["servers"]["basic_memory"]["command"]

    outside = tmp_path / "outside-checkout"
    outside.mkdir()
    parameters = StdioServerParameters(
        command=command[0],
        args=command[1:],
        cwd=outside,
        env=os.environ | {"HOME": str(home)},
    )
    arguments = {"content": DURABLE, "project": "personal", "identifier": "durable/from-launcher"}

    async def propose():
        async with stdio_client(parameters) as streams, ClientSession(*streams, read_timeout_seconds=30) as session:
            await session.initialize()
            return await session.call_tool("bm_write", arguments)

    result = asyncio.run(propose())
    assert not result.is_error, result.content
    proposal_id = result.structured_content["result"]["proposal_id"]
    target = root / "notes/personal/durable/from-launcher.md"
    assert not target.exists()
    loaded = load_config(gate)
    (proposal,) = list_proposals(loaded)
    assert proposal["id"] == proposal_id
    assert cli.command_approve(loaded, proposal_id, confirm=lambda _: True) == 0
    assert target.exists()
