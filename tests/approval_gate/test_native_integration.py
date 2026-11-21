"""End-to-end gate check against a disposable native Basic Memory store."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

from approval_gate import cli
from approval_gate.proposals import Config, list_proposals

DURABLE = (
    "---\ntitle: Gated decision\nkind: durable\nstatus: active\nsource: integration check\n---\n\nKeep SQLite local.\n"
)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("APPROVAL_GATE_TEST_SECRET", "synthetic-credential")
    root = tmp_path / "store"
    state = root / "state"
    personal = root / "notes/personal"
    for folder in (state, personal / "durable", personal / "temporary", personal / "handovers"):
        folder.mkdir(parents=True)
    (personal / "handovers/existing-durable.md").write_text(DURABLE)
    config = {
        "projects": {"personal": {"path": str(personal), "mode": "local"}},
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


@pytest.fixture
def proxy(store, tmp_path):
    root, executable, environment = store
    config = Config(
        native_command=[str(executable), "mcp", "--transport", "stdio"],
        proposals_dir=tmp_path / "approvals",
        audit_log=tmp_path / "audit.jsonl",
        env=environment,
    )
    config_path = tmp_path / "gate.json"
    config_path.write_text(config.model_dump_json())
    assert "APPROVAL_GATE_TEST_SECRET" not in json.loads(config_path.read_text())["env"]
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "approval_gate.gate", "--config", str(config_path)],
        cwd=Path(__file__).resolve().parents[2],
        env={"PYTHONPATH": os.environ.get("PYTHONPATH", "")},
    )
    return root, config, parameters


def test_durable_write_requires_owner_approval_and_then_persists(proxy):
    root, config, parameters = proxy
    target = root / "notes/personal/durable/decision.md"
    arguments = {"content": DURABLE, "project": "personal", "identifier": "durable/decision.md"}

    async def propose():
        async with stdio_client(parameters) as streams, ClientSession(*streams, read_timeout_seconds=30) as session:
            await session.initialize()
            return await session.call_tool("bm_write", arguments)

    result = asyncio.run(propose())
    assert not result.is_error
    assert not target.exists()
    (proposal,) = list_proposals(config)
    assert result.structured_content["result"]["proposal_id"] == proposal["id"]
    assert cli.command_approve(config, proposal["id"], confirm=lambda _: True) == 0

    assert target.exists()
    assert target.read_text().startswith("---\ntitle: Gated decision")
    assert list_proposals(config)[0]["status"] == "approved"


def test_temporary_handover_lifecycle_uses_the_proxy(proxy):
    root, config, parameters = proxy
    target = root / "notes/personal/handovers/integration.md"
    arguments = {
        "content": (
            "---\ntitle: Integration handover\nkind: temporary\nstatus: active\nlast_activity: '2000-01-01T00:00:00Z'\n"
            "---\n\nResume this work.\n"
        ),
        "project": "personal",
        "identifier": "personal/handovers/integration.md",
    }

    async def wait_for_content(*lines):
        # Native file materialization can finish after the MCP response.
        async with asyncio.timeout(5):
            while True:
                content = target.read_text() if target.exists() else ""
                if all(line in content for line in lines):
                    return
                await asyncio.sleep(0.05)

    async def verify():
        async with stdio_client(parameters) as streams, ClientSession(*streams, read_timeout_seconds=30) as session:
            await session.initialize()
            created = await session.call_tool("bm_write", arguments)
            assert not created.is_error, created.content
            assert list_proposals(config) == []
            await wait_for_content("Resume this work.")

            for status in ("completed", "archived", "active"):
                read = await session.call_tool(
                    "bm_read",
                    {"identifier": arguments["identifier"], "project": "personal", "output_format": "json"},
                )
                assert not read.is_error and isinstance(read.structured_content, dict), read.content
                note = read.structured_content.get("result", read.structured_content)
                status_fields = f"status: {status}"
                if status == "archived":
                    status_fields += "\narchive_reason: completed"
                if status == "active":
                    status_fields += "\narchive_reason: null"
                content = arguments["content"].replace("status: active", status_fields)
                changed = await session.call_tool(
                    "bm_write", arguments | {"expected_checksum": note["checksum"], "content": content}
                )
                assert not changed.is_error, changed.content
                assert list_proposals(config) == []
                await wait_for_content(*status_fields.splitlines())

            proposed = await session.call_tool(
                "bm_write",
                arguments | {"identifier": "handovers/durable.md", "metadata": {"kind": "durable"}},
            )
            assert not proposed.is_error, proposed.content
            assert not target.with_name("durable.md").exists()

            existing = target.with_name("existing-durable.md")
            before = existing.read_bytes()
            read = await session.call_tool(
                "bm_read",
                {"identifier": "handovers/existing-durable.md", "project": "personal", "output_format": "json"},
            )
            assert not read.is_error and isinstance(read.structured_content, dict), read.content
            note = read.structured_content.get("result", read.structured_content)
            proposed = await session.call_tool(
                "bm_write",
                arguments | {"identifier": "handovers/existing-durable.md", "expected_checksum": note["checksum"]},
            )
            assert not proposed.is_error, proposed.content
            assert existing.read_bytes() == before
            assert len(list_proposals(config)) == 2

    asyncio.run(verify())
